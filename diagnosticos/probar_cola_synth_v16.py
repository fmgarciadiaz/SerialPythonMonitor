"""Physical Synth queue trial. Requires an idle Q and no other relay client."""
import sys,json,time,argparse,gc
from pathlib import Path
from dataclasses import asdict,replace
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from monitor.historico.v16.receiver.unoq_usb import Connection
from monitor.historico.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.historico.v16.receiver.unoq_switch import Mode
from monitor.historico.v16.receiver.unoq_acquisition import Configuration
from monitor.historico.v16.receiver.unoq_wav import State
from monitor.historico.v16.fm_source import FMSource,FMParameters
from monitor.historico.v16.virtual_instruments import warmup

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=float,default=30)
    parser.add_argument('--timings',action='store_true',help='Record host interval trace to separate ACK delay contributors')
    parser.add_argument('--freeze-startup',action='store_true',help='Experimental scoped freeze of initialized objects; new objects retain normal GC')
    parser.add_argument('--process',action='store_true',help='Experimental separate generation process; receiver remains here')
    args=parser.parse_args();warmup()
    from monitor.historico.v16.fm_feedback import warmup as warmup_feedback
    warmup_feedback()
    folder=ROOT/'diagnosticos/resultados_piano/eficiencia_v16';folder.mkdir(exist_ok=True)
    path=folder/(datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')+'_cola_fisica.json')
    report=dict(scope='Headless physical digital continuity; simulated chords/pedal, no Qt/MIDI or acoustic latency',cases=[],restored=False)
    def save():path.write_text(json.dumps(report,indent=2)+'\n')
    def wait(r):
        deadline=time.monotonic()+5
        while r.wav_pending and time.monotonic()<deadline:r.pump()
        if r.wav_pending:raise TimeoutError('WAV no confirmó comando')
    with Connection('1060031107') as connection:
        r=OutputReceiver(connection,lambda batch:None,lambda message:print(message,flush=True))
        r.select(Mode.SPI);prior=r.config;gen=r.generator().active
        r.wav_request();wait(r)
        if r.wav_status.state!=State.IDLE or gen.enabled:
            raise RuntimeError('Salida Q ocupada; no se modifica')
        report['prior']=dict(adc=asdict(prior),generator=asdict(gen));save()
        gc_started={}
        def observe_gc(phase,info):
            generation=info['generation']
            if phase=='start':gc_started[generation]=time.monotonic()
            elif generation in gc_started:r._trace_transport('gc',gc_started.pop(generation),time.monotonic(),generation)
        if args.timings:gc.callbacks.append(observe_gc)
        frozen=False
        try:
            if args.freeze_startup:
                if gc.get_freeze_count():raise RuntimeError('Hay objetos congelados previos; ensayo no los modifica')
                gc.collect();gc.freeze();frozen=True
                report['gc_frozen_objects']=gc.get_freeze_count()
            r.configure(Configuration(14,100000))
            for target in (5,4,3):
                params=FMParameters(preset='Piano Virtual',waveform='virtual',virtual_model='piano',
                    string_decay=4.,string_position=.12,string_brightness=.78,
                    oscillator_levels=(1.,0.,0.),notes=())
                if args.process:
                    from monitor.historico.v16.synth_process import SynthProcess
                    source=SynthProcess(20000,params,wait_ready=False)
                    deadline=time.monotonic()+30
                    while not source.is_ready():
                        if time.monotonic()>deadline:raise TimeoutError('Worker no inició')
                        r.pump()
                else:source=FMSource(20000,params)
                source.target_blocks=target
                case=dict(target=target,rate=20000,adc_rate=100000,queue_ms=target*24,statuses=0,min_blocks=16,max_target=target,ok=False)
                report['cases'].append(case)
                def status(s):
                    source.observe_status(s);case['statuses']+=1
                    case['max_target']=max(case['max_target'],source.target_blocks)
                    if s.state==State.PLAYING:case['min_blocks']=min(case['min_blocks'],16-s.free_blocks)
                r.on_wav=status;r.wav_request(1,source,20000)
                if args.timings:r.transport_trace=[]
                began=time.monotonic();step=-1
                while time.monotonic()-began<args.seconds:
                    current=int((time.monotonic()-began)/.35)
                    if current!=step:
                        step=current;base=36+(step%4)*7
                        notes=tuple((base+i,70+(i*5)%55) for i in range(11)) if step%4!=3 else ()
                        source.update(replace(params,notes=notes,note_id=step+1,virtual_sustain=step%4!=3))
                    r.pump()
                    if r.wav_status and r.wav_status.state in (State.UNDERRUN,State.FAULT,State.DONE):break
                s=r.wav_status
                if args.timings:
                    trace_path=path.with_name(path.stem+f'_target{target}_trace.json')
                    trace_path.write_text(json.dumps(r.transport_trace)+'\n')
                    case['host_trace']=str(trace_path.relative_to(ROOT))
                    r.transport_trace=None
                case.update(seconds=time.monotonic()-began,state=s.state.name,reason=int(s.reason),played=s.played,
                    max_render_ms=source.max_render_ms,max_ack_gap_ms=source._max_ack_gap*1000,
                    transport=source.transport_metrics,adc_status=r.decoder.status)
                case['ok']=s.state==State.PLAYING and not s.reason and case['max_target']==target
                if args.process:case['max_worker_render_ms']=source.max_worker_render_ms
                r.wav_request(3);wait(r);save();print(json.dumps(case),flush=True)
                if args.process:source.close()
                if not case['ok']:break
        except Exception as exc:
            report['error']=str(exc);raise
        finally:
            if args.process and 'source' in locals():source.close()
            if frozen:gc.unfreeze()
            if args.timings:gc.callbacks.remove(observe_gc)
            try:
                r.wav_request(3);wait(r);r.configure(prior);r.generator(gen)
                report['final']=dict(adc=asdict(r.config),generator=asdict(r.generator().active),wav=r.wav_status.state.name)
                report['restored']=report['final']['adc']==asdict(prior) and report['final']['generator']==asdict(gen) and r.wav_status.state==State.IDLE
            except Exception as exc:report['restore_error']=str(exc)
            save();print(path,flush=True)

if __name__=='__main__':main()
