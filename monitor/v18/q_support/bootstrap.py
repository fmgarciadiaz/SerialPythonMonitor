"""Initial Scope V18 installation, exclusively on an unoccupied target.

Uses accepted sources/binaries and the existing bounded backend. Never removes
an existing app or substitutes a private firmware/cache for the accepted pair.
"""
import json

from monitor.v18.q_support.backend import APP, APP_CONTAINER, CONTAINER, HELPER, _verified_file
from monitor.v18.q_support.prepare import Journal, sha256


def inventory(backend):
    apps=backend._json('arduino-app-cli','app','list','--format','json')
    if not isinstance(apps,dict) or not isinstance(apps.get('apps'),list):
        raise RuntimeError('No se pudo verificar el inventario de apps del Q')
    names=backend._output('docker','ps','-a','--format','{{.Names}}').splitlines()
    running=backend._output('docker','ps','--format','{{.Names}}').splitlines()
    exists=backend._json('python3','-c',
        'import os,json,sys;print(json.dumps(os.path.lexists(sys.argv[1])))',APP)
    if not isinstance(exists,bool):raise RuntimeError('Estado de carpeta Scope V18 inválido')
    return dict(apps=apps['apps'],containers=names,running=running,path_exists=exists)


def require_empty(state):
    if (state['path_exists'] or APP_CONTAINER in state['containers'] or
            CONTAINER in state['containers'] or
            any(app.get('name')=='Scope V18' for app in state['apps'])):
        raise RuntimeError('Scope V18 existe o está incompleta; no se sobrescribe como instalación inicial')
    if (any(app.get('status')=='running' for app in state['apps']) or
            any(name.startswith('scope-') and name.endswith('-main-1') for name in state['running'])):
        raise RuntimeError('Hay otra app activa en el Q; detenerla antes de la instalación inicial')
    # A relay from an older version may own SPI without an App Lab app running.
    if any(name.startswith('serialmonitor-usb-stream') for name in state['running']):
        raise RuntimeError('Hay otro relay activo; no se interrumpe ni modifica')


def preflight(backend,acceptance):
    backend._no_reader()
    state=inventory(backend);require_empty(state)
    proof=json.loads(_verified_file(acceptance,'prebuild_proof').read_text())
    launcher=proof.get('launcher',{})
    if (launcher.get('path')!='/usr/bin/arduino-app-cli' or
            backend._output('arduino-app-cli','version')!=launcher.get('version','').strip() or
            backend._hash(launcher['path'])!=launcher.get('sha256')):
        raise RuntimeError('App CLI del Q no coincide con el entorno validado; revisar su versión antes de instalar')
    board=backend._board();board.run('get-state')
    board.run('push',str(HELPER),backend.helper)
    if backend._hash(backend.helper)!=sha256(HELPER):
        raise RuntimeError('El verificador transferido al Q no coincide')
    return state


def cleanup(backend,created):
    """Stop only new V18 resources; retain failed sources for diagnosis."""
    errors=[]
    def attempt(label,operation):
        try:return operation()
        except BaseException as exc:errors.append(label+': '+str(exc))
    board=backend._board()
    if created:
        names=attempt('inventario',lambda:backend._output('docker','ps','-a','--format','{{.Names}}').splitlines())
        relay_id=getattr(backend,'new_relay_id',None)
        relay=attempt('identidad relay',lambda:backend._inspect(CONTAINER)) if names is not None and CONTAINER in names else None
        owned_relay=relay is not None and relay_id is not None and relay.get('Id')==relay_id
        if relay is not None and not owned_relay:
            errors.append('Relay con identidad no atribuible a este intento; no se modifica')
        if owned_relay:
            attempt('detener relay nuevo',lambda:board.shell('docker','stop','--time','3',relay_id))
        sources=attempt('comprobar fuentes nuevas',backend._sources)
        owned_app=sources==backend.acceptance['sources']['app']
        if owned_app and names is not None and APP_CONTAINER in names:
            attempt('detener app nueva',board.stop)
        # Keep failed installation material; no unknown firmware is restarted.
        # Do not move a partial import whose exact ownership cannot be proven.
        if owned_app and not errors:
            if owned_relay:
                attempt('retirar relay nuevo detenido',lambda:board.shell('docker','rm',relay_id))
            if names is not None and APP_CONTAINER in names:
                attempt('retirar app nueva detenida',lambda:board.shell('docker','rm',APP_CONTAINER))
            if not errors:
                attempt('guardar instalación fallida',lambda:board.shell('mv',APP,backend.remote_folder+'/failed_initial_app'))
    return dict(errors=errors,previous_scope_pair_existed=False,
                previous_firmware_restored=False,failed_material=backend.remote_folder,
                note='No se restaura firmware previo desconocido; revisar informe antes de reintentar')


def install_empty(backend,acceptance,report,save):
    journal=Journal(report,save);created=False;prepared=None
    report['action']='install_initial';save()
    try:
        journal.step('initial_preflight',lambda:preflight(backend,acceptance))
        print('Primera instalación: preparando la pareja Scope V18 aceptada…',flush=True)
        prepared=journal.step('initial_stage',lambda:backend.prepare(acceptance,{}))
        # Compile and hash-gate before creating/starting any app on the Q.
        if not all(prepared.get(key) is True for key in
                   ('source_hashes_equal','compiled_firmware_hash_equal','precompiled_relay_hash_equal')):
            raise RuntimeError('La pareja preparada no pasó la verificación de binarios')
        journal.step('initial_recheck',lambda:require_empty(inventory(backend)))
        backend._board().shell('mkdir','-p',backend.remote_folder)
        created=True  # Import may fail after creating its target; preserve intent.
        journal.step('initial_import',backend._board().create)
        if backend._sources()!=acceptance['sources']['app']:
            raise RuntimeError('Las fuentes importadas no coinciden con Scope V18 aceptada')
        print('Instalando firmware y relay V18…',flush=True)
        journal.step('initial_start_app',lambda:backend.start_new_app(prepared))
        journal.step('initial_start_relay',lambda:backend.start_new_relay({},prepared))
        journal.step('initial_verify_environment',lambda:backend.preflight(acceptance))
        identity=backend._identity()
        if any(identity.get(key)!=value for key,value in acceptance['candidate_identity'].items()):
            raise RuntimeError('Identidad de primera instalación distinta de la aceptada')
        baseline=journal.step('initial_capture',backend.capture)
        if baseline['app_sources']!=acceptance['sources']['app']:
            raise RuntimeError('Fuentes de primera instalación distintas de la pareja aceptada')
        print('Verificando diez segundos de adquisición y salida apagada…',flush=True)
        recovery=journal.step('initial_acquisition',lambda:backend._recover(identity,10))
        if not all(recovery.get(key) is True for key in ('snapshot_equal','continuous','integrity_ok')):
            raise RuntimeError('Primera instalación sin adquisición continua verificada')
        report.update(ok=True,action='installed_initial',identity=identity,recovery=recovery)
        save()
    except BaseException:
        report['initial_cleanup']=cleanup(backend,created)
        save()
        raise
