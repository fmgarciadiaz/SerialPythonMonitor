"""Trial the cached candidate relay, retain old container, and restore it."""
import sys,json,time,subprocess,argparse
from pathlib import Path
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from unoq import Board,config_path
from usb_stream import CONTAINER,stop
from monitor.historico.v16.receiver.unoq_usb import Connection
from monitor.historico.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.historico.v16.receiver.unoq_switch import Mode
from monitor.historico.v16.receiver.unoq_acquisition import Configuration
from monitor.historico.v16.receiver.unoq_generator import GeneratorConfig

def state(restore=None):
    with Connection('1060031107') as c:
        r=OutputReceiver(c,lambda batch:None);r.select(Mode.SPI)
        if restore:
            r.configure(Configuration(**restore['adc']))
            r.generator(GeneratorConfig(**restore['generator']))
        r.wav_request();deadline=time.monotonic()+5
        while r.wav_pending and time.monotonic()<deadline:r.pump()
        if r.wav_pending or int(r.wav_status.state)!=0:raise RuntimeError('WAV no está IDLE')
        result=dict(adc=asdict(r.config),generator=asdict(r.generator().active))
        if not restore and result['generator']['enabled']:raise RuntimeError('Generador ocupado')
        return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-binary',required=True,help='Already compiled absolute Q path; stable relay is restored afterwards')
    args=parser.parse_args()
    b=Board(json.loads(config_path('v16').read_text()))
    sockets=b.shell('ss','-tnp',capture=True).stdout
    if ':8766' in sockets:raise RuntimeError('Relay ocupado por otro cliente')
    previous=state();old=json.loads(b.shell('docker','inspect',CONTAINER,capture=True).stdout)[0]
    backup=CONTAINER+'-before-synth-trial'
    report=dict(prior=previous,old_mounts=old['Mounts'],restored=False)
    path=ROOT/'diagnosticos/resultados_piano/eficiencia_v16/relay_trial_restoration.json'
    path.write_text(json.dumps(report,indent=2)+'\n')
    b.shell('docker','stop','--time','3',CONTAINER)
    b.shell('docker','rename',CONTAINER,backup)
    try:
        import usb_stream
        original_binary=usb_stream.binary;original_argv=sys.argv
        try:
            usb_stream.binary=lambda *a,**k:args.candidate_binary
            sys.argv=['usb_stream.py','start','--firmware','v16'];usb_stream.main()
        finally:
            usb_stream.binary=original_binary;sys.argv=original_argv
        state(previous) # App restart may enable its default generator.
        subprocess.run([sys.executable,str(ROOT/'diagnosticos/probar_cola_synth_v16.py'),'--seconds','30'],check=True)
        report['candidate_logs']=b.shell('docker','logs','--tail','20',CONTAINER,capture=True).stdout
    except Exception as exc:
        report['error']=str(exc);raise
    finally:
        try:
            stop(b);b.shell('docker','rename',backup,CONTAINER)
            b.start();b.shell('docker','start',CONTAINER)
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                try:
                    report['final']=state(previous);break
                except Exception:time.sleep(.2)
            report['restored']=report.get('final')==previous
            if not report['restored']:raise RuntimeError('Restauración no confirmada')
        except Exception as exc:report['restore_error']=str(exc)
        path.write_text(json.dumps(report,indent=2)+'\n');print(path,flush=True)

if __name__=='__main__':main()
