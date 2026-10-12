"""Isolated WAV240 trial; restore installed V16 app and exact control profile."""
import json,sys,subprocess,time,argparse
from pathlib import Path
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from unoq import Board
import usb_stream
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor,require_available_wav
from monitor.v16.receiver.unoq_usb import Connection
from monitor.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.v16.receiver.unoq_switch import Mode
from monitor.v16.receiver.unoq_acquisition import Configuration
from monitor.v16.receiver.unoq_generator import GeneratorConfig

EXPERIMENT=ROOT/'experimentos/synth_wav240/unoq.json'
STABLE=ROOT/'arduino/v16/unoq.json'
def profile(restore=None):
    with Connection('1060031107') as c:
        r=OutputReceiver(c,lambda _:None);r.select(Mode.SPI)
        gen=r.generator().active;r.wav_request()
        deadline=time.monotonic()+5
        while r.wav_pending and time.monotonic()<deadline:r.pump()
        if r.wav_pending:raise TimeoutError('Sin confirmación WAV')
        if restore is not None and gen.enabled:
            r.generator(GeneratorConfig(enabled=0,low=0,high=0));gen=r.generator().active
        require_available_wav(r,gen)
        if restore is not None:
            r.configure(Configuration(**restore['adc']))
            r.generator(GeneratorConfig(**restore['generator']))
        return dict(adc=asdict(r.config),generator=asdict(r.generator().active),wav=r.wav_status.state.name)

def start(config):
    saved_args=sys.argv;saved_path=usb_stream.config_path;saved_binary=usb_stream.binary
    try:
        usb_stream.config_path=lambda _:config
        stable_relay_board=Board(json.loads(STABLE.read_text()))
        usb_stream.binary=lambda board,*args,**kwargs:saved_binary(stable_relay_board,*args,**kwargs)
        sys.argv=['usb_stream.py','start','--firmware','v16']
        usb_stream.main()
    finally:sys.argv=saved_args;usb_stream.config_path=saved_path;usb_stream.binary=saved_binary

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=float,default=60)
    parser.add_argument('--credits',type=int,choices=(2,3,4),default=2)
    parser.add_argument('--targets',type=int,nargs='+',choices=range(4,17),default=[8,6])
    parser.add_argument('--presets',nargs='+',default=['Guitarra','Brass','Piano Virtual'])
    args=parser.parse_args()
    if args.seconds<=0:parser.error('Duración debe ser positiva')
    require_exclusive_monitor()
    stable=Board(json.loads(STABLE.read_text()));experiment=Board(json.loads(EXPERIMENT.read_text()))
    apps=json.loads(stable.cli('app','list','--format','json',capture=True).stdout).get('apps',[])
    if any(a.get('status')=='running' and a.get('name')!=stable.config['name'] for a in apps):
        raise RuntimeError('Otra aplicación activa; ensayo cancelado antes de cambiar firmware')
    report=dict(prior=profile(),restored=False)
    folder=ROOT/'diagnosticos/resultados_piano/eficiencia_v16';folder.mkdir(parents=True,exist_ok=True)
    path=folder/(time.strftime('%Y%m%d_%H%M%S')+'_wav240_restoration.json')
    report['backup']=str(stable.backup());path.write_text(json.dumps(report,indent=2)+'\n')
    changed=False
    try:
        if any(a.get('name')==experiment.config['name'] for a in apps):
            experiment.push_sources(experiment.check_sources(),experiment.remote)
        else:experiment.create()
        changed=True
        usb_stream.stop(stable);stable.stop();start(EXPERIMENT)
        profile(report['prior'])
        trial_log=path.with_name(path.stem+'_trial.log');report['trial_log']=str(trial_log)
        with trial_log.open('w') as out:
            result=subprocess.run([sys.executable,str(ROOT/'diagnosticos/probar_audio_owner_v16.py'),
                '--seconds',str(args.seconds),'--targets',*[str(t) for t in args.targets],'--shared-adc','--adc-rate','40000',
                '--amplitude','2.5','--voices','11','--scheduler','--worker-wakeup',
                '--chunk-size','240','--credits',str(args.credits),'--presets',*args.presets],stdout=out,stderr=subprocess.STDOUT)
        report['trial_exit_code']=result.returncode
    except Exception as exc:report['error']=str(exc)
    finally:
        if changed:
            try:
                usb_stream.stop(experiment);experiment.stop();start(STABLE)
                report['final']=profile(report['prior']);report['restored']=report['final']==report['prior']
                if not report['restored']:report['restore_error']='Perfil final distinto del inicial'
            except Exception as exc:report['restore_error']=str(exc)
        path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
    if not report['restored'] or report.get('error') or report.get('trial_exit_code')!=0:
        raise RuntimeError('Ensayo incompleto; revisar reporte '+str(path))
if __name__=='__main__':main()
