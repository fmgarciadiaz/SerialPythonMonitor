"""Passive CH1 antenna captures; no generated RF, exact ADC/generator restoration."""
import sys,json,time
from pathlib import Path
from dataclasses import asdict
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_switch import Mode
from monitor.v17.bode_calibration import instrument_identity
from monitor.v17.radio_scan import scan_carriers,SCAN_SIZE,SCAN_BLOCKS
from monitor.v17.radio_am import AMDemodulator,RadioConfig

def main():
    require_exclusive_monitor()
    folder=ROOT/'diagnosticos/resultados_v17/antena_am'/time.strftime('%Y%m%d_%H%M%S')
    folder.mkdir(parents=True)
    report=dict(cases=[],restored=False,scope='Passive antenna CH1; RF candidates, not identified stations or listening acceptance')
    def persist():(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    report['identity']=instrument_identity('1060031107');persist()
    if report['identity'] is None:raise RuntimeError('No se pudo verificar firmware')
    try:
        with Connection('1060031107') as connection:
            r=OutputReceiver(connection,lambda _:None);r.decoder.numeric=True
            r.select(Mode.SPI);gen=r.generator().active
            prior=r.config
            r.wav_request();deadline=time.monotonic()+3
            while r.wav_pending and time.monotonic()<deadline:r.pump()
            if gen.enabled or r.wav_status is None or r.wav_status.state.value not in (0,3):raise RuntimeError('Salida ocupada; no se modificó')
            report['prior']=dict(adc=asdict(prior),generator=asdict(gen));persist()
            try:
                for bits,rate in ((8,1600000),(10,1250000),(14,851063)):
                    r.configure(Configuration(bits,rate));chunks=[];count=0
                    def collect(records):
                        nonlocal count
                        if count<SCAN_SIZE*SCAN_BLOCKS*4:
                            data=np.asarray(list(records),dtype=np.uint32)
                            chunks.append(data);count+=len(data)
                    r.on_samples=collect
                    before=r.decoder.pairs;started=time.monotonic()
                    while time.monotonic()-started<5:r.pump()
                    r.on_samples=lambda _:None
                    data=np.concatenate(chunks)
                    path=folder/f'adc{bits}_{rate}.npz'
                    np.savez_compressed(path,records=data,rate=r.config.actual_rate,bits=bits)
                    case=dict(bits=bits,rate=r.config.actual_rate,recording=path.name,captured=len(data),samples=r.decoder.pairs-before,status=dict(r.decoder.status))
                    report['cases'].append(case);persist()
                    print(f'Captured ADC{bits}/{rate}: {len(data)}',flush=True)
            finally:
                r.on_samples=lambda _:None;r.configure(prior);reply=r.generator(gen)
                started=time.monotonic();before=r.decoder.pairs
                while time.monotonic()-started<10:r.pump()
                report['recovery']=dict(samples=r.decoder.pairs-before,status=dict(r.decoder.status))
                report['restored']=r.config==prior and reply.active==gen
                persist()
        report['final_identity']=instrument_identity('1060031107')
        report['identity_unchanged']=report['identity']==report['final_identity']
        persist()
        for case in report['cases']:
            data=np.load(folder/case['recording'])['records'];rf=data[:,1]*3.3/((1<<case['bits'])-1)
            case['levels']=dict(min_v=float(rf.min()),max_v=float(rf.max()),rms_ac_v=float(np.std(rf)),clipped=int(np.count_nonzero((data[:,1]==0)|(data[:,1]==(1<<case['bits'])-1))))
            scans=[]
            for j in range(3):
                block=rf[j*SCAN_SIZE*SCAN_BLOCKS:(j+1)*SCAN_SIZE*SCAN_BLOCKS]
                if len(block)!=SCAN_SIZE*SCAN_BLOCKS:break
                scans.append(scan_carriers(block,case['rate'],10,2,10000))
            case['scans']=scans;persist()
        report['ok']=report['restored'] and report['identity_unchanged'] and all(not c['status'].get('dropped',0) and not c['status'].get('fatal',0) for c in report['cases'])
    except Exception as exc:report['error']=str(exc)
    persist();print(folder,flush=True);print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
