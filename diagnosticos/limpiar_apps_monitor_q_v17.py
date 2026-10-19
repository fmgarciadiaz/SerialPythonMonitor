"""Archive and remove explicitly inventoried old monitor apps; keep V16/V17."""
import sys,json,base64,zipfile,subprocess,shlex
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from unoq import Board,config_path


def main():
    folder=ROOT/'diagnosticos/resultados_v17'
    if not json.loads((folder/'radio_test_installed.json').read_text())['ok']:
        raise RuntimeError('V17 installation must be verified first')
    inventory=json.loads((folder/'cleanup_inventory.json').read_text())
    b=Board(json.loads(config_path('v17').read_text()))
    archive=ROOT/'respaldos/unoq/apps_antiguas_antes_v17_20261013.zip'
    report={'keep':['scope-v16','scope-v17'],'archive':str(archive.relative_to(ROOT)),
            'apps':[],'networks':[],'ok':False}
    output=folder/'cleanup_old_apps.json'
    def save():output.write_text(json.dumps(report,indent=2)+'\n')
    names={app['folder'] for app in inventory['remove']}
    with zipfile.ZipFile(archive,'a',zipfile.ZIP_DEFLATED) as bundle:
        for app in inventory['remove']:
            name=app['folder']
            if name in report['keep']:raise RuntimeError('Protected app in removal list')
            current=json.loads(b.cli('app','list','--format','json',capture=True).stdout)['apps']
            matches=[x for x in current if base64.b64decode(x['id']+'='*(-len(x['id'])%4)).decode()=='user:'+name]
            if not matches:continue
            if matches[0]['status']=='running':raise RuntimeError('Unexpected running old app')
            remote='/home/arduino/ArduinoApps/'+name
            temporary='/tmp/v17-cleanup-'+name+'.zip'
            local=folder/('cleanup-'+name+'.zip')
            b.cli('app','export',remote,temporary,capture=True)
            b.run('pull',temporary,str(local),capture=True)
            bundle.write(local,name+'.zip');bundle.fp.flush()
            local.unlink()
            b.shell('python3','-c','import pathlib,sys; pathlib.Path(sys.argv[1]).unlink()',temporary)
            result=subprocess.run([b.adb,'-s',b.serial,'shell',shlex.join(['arduino-app-cli','app','destroy',remote])],
                                  input='y\n',capture_output=True,text=True,timeout=60)
            row={'folder':name,'removed':result.returncode==0,'log':result.stdout+result.stderr}
            report['apps'].append(row);save();print(name,row['removed'],flush=True)
            if not row['removed']:raise RuntimeError(row['log'])
    # App CLI destroys runtime resources but retains source folders.
    # Remove sources only after the archive has been fully closed.
    completed=[x['folder'] for x in report['apps'] if x['removed']]
    code="""import pathlib,json,sys,shutil
base=pathlib.Path('/home/arduino/ArduinoApps')
names=json.loads(sys.argv[1])
for name in names:
 if name in ('scope-v16','scope-v17') or '/' in name or name.startswith('.'):raise RuntimeError('Protected target')
 path=base/name
 if path.is_symlink() or path.resolve().parent!=base.resolve():raise RuntimeError('Unexpected source path')
for name in names:
 path=base/name
 if path.exists():shutil.rmtree(path)
"""
    b.shell('python3','-c',code,json.dumps(completed))
    report['source_folders_removed']=completed;save()
    all_names=b.shell('docker','network','ls','--format','{{.Name}}',capture=True).stdout.splitlines()
    for name in all_names:
        if name not in {x+'_default' for x in names}:continue
        network=json.loads(b.shell('docker','network','inspect',name,capture=True).stdout)[0]
        if network.get('Containers'):continue
        report['networks'].append(network);save()
        b.shell('docker','network','rm',name)
    final=json.loads(b.cli('app','list','--format','json',capture=True).stdout)['apps']
    remaining=[base64.b64decode(x['id']+'='*(-len(x['id'])%4)).decode()[5:] for x in final]
    report['ok']=not(set(remaining)&names) and set(report['keep']).issubset(remaining)
    save();print('CLEANUP',report['ok'],'apps',len(report['apps']),'networks',len(report['networks']),flush=True)


if __name__=='__main__':main()
