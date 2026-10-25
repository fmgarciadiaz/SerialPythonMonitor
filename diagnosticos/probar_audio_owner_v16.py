"""Experimental child owns Synth+Q; parent validates bounded ADC IPC and forces GC.

No GUI integration. No dropped ADC allowed: a full IPC queue fails the trial.
The child snapshots/restores the Q. Optional startup freeze belongs only to
the disposable child; normal GC of newly allocated objects remains enabled.
"""
import sys,time,json,argparse,gc,queue,multiprocessing as mp
import os,re,subprocess
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from dataclasses import asdict,replace
from monitor.historico.v16.fm_source import FMSource,FMParameters

def monitor_processes(process_text, own_pid=None):
    """Conservative preflight: an open monitor may own the Q."""
    found=[]
    for line in process_text.splitlines():
        fields=line.strip().split(None,1)
        if len(fields)!=2 or not fields[0].isdigit():continue
        pid,command=int(fields[0]),fields[1]
        if pid==own_pid:continue
        if ('iniciar_monitor.py' in command or
                re.search(r'monitor/(?:historico/)?v\d+/app\.py(?:\s|$)',command)):
            found.append(pid)
    return found


def require_exclusive_monitor():
    processes=subprocess.run(['ps','-axo','pid=,command='],check=True,capture_output=True,text=True)
    owners=monitor_processes(processes.stdout,os.getpid())
    if owners:raise RuntimeError(f'Monitor abierto (PID {owners}); ensayo cancelado antes de conectar al Q')


def require_available_wav(receiver,generator):
    from monitor.historico.v16.receiver.unoq_wav import State
    status=receiver.wav_status
    # Firmware BEGIN accepts completed playback; no STOP of another session.
    available=status.state==State.IDLE or (status.state==State.DONE and not status.reason)
    if not available or generator.enabled:raise RuntimeError('Q ocupado')


def validate_adc_batch(data,last_index=None,last_timestamp=None,period_us=10):
    if data.ndim!=2 or data.shape[1]!=4 or not len(data):raise ValueError('Lote ADC IPC inválido')
    timestamp=data[:,0].astype(np.uint64);indices=data[:,3].astype(np.uint64)
    if np.any(data[:,1:3]>16383):raise ValueError('ADC IPC fuera de rango')
    if np.any((np.diff(indices)&0xffffffff)!=1) or np.any((np.diff(timestamp)&0xffffffff)!=period_us):raise ValueError('ADC IPC discontinuo dentro de lote')
    if last_index is not None and ((int(indices[0])-last_index)&0xffffffff)!=1:raise ValueError('ADC IPC perdió muestras entre lotes')
    if last_timestamp is not None and ((int(timestamp[0])-last_timestamp)&0xffffffff)!=period_us:raise ValueError('ADC IPC perdió timestamps entre lotes')
    return int(indices[-1]),int(timestamp[-1]),len(data)

def owner(control,adc,target,seconds,freeze,trace_path=None,adc_rate=100000,qos=False,socket_probe=False,amplitude=1.0,parameters=None,scheduler=False,read_timeout_ms=100,probe_process=False,credits=2,async_synth=False,worker_wakeup=False,chunk_size=480):
    from monitor.historico.v16.receiver.unoq_usb import Connection
    from monitor.historico.v16.receiver.unoq_config_receiver import OutputReceiver
    from monitor.historico.v16.receiver.unoq_switch import Mode
    from monitor.historico.v16.receiver.unoq_acquisition import Configuration
    from monitor.historico.v16.receiver.unoq_generator import GeneratorConfig
    from monitor.historico.v16.receiver.unoq_wav import State
    from monitor.historico.v16.virtual_instruments import warmup
    from monitor.historico.v16.fm_feedback import warmup as feedback_warmup
    report=dict(dac_levels=dict(amplitude=amplitude,offset=1.65),queue_growth=[],target=target,adc_rate=adc_rate,freeze_worker=freeze,restored=False,sent_samples=0,max_target=target,min_blocks=16)
    if scheduler:
        import resource
        report["slow_pumps"]=[];report["slow_pumps_omitted"]=0;report["slow_reads"]=[];report["slow_reads_omitted"]=0
    pending=[];frozen=False;source=None;receiver=None;gc_started={};probe=None;qos_context=None
    def gc_trace(phase,info):
        generation=info["generation"]
        if phase=="start":gc_started[generation]=time.monotonic()
        elif receiver is not None and generation in gc_started:
            receiver._trace_transport("gc",gc_started.pop(generation),time.monotonic(),generation)
    def send_batch():
        if not pending:return
        began=time.monotonic();cpu=time.thread_time() if trace_path else None
        data=np.asarray(pending,dtype=np.uint32)
        try:adc.put_nowait(data)
        except queue.Full:raise RuntimeError('ADC IPC lleno; ensayo rechazado sin descartar muestras silenciosamente')
        report['sent_samples']+=len(data);pending.clear()
        if receiver is not None and cpu is not None:receiver._trace_transport('adc_ipc',began,time.monotonic(),cpu_seconds=time.thread_time()-cpu)
    def collect(records):
        pending.extend(records)
        if len(pending)>=2048:send_batch()
    def wait(r):
        deadline=time.monotonic()+5
        while r.wav_pending and time.monotonic()<deadline:r.pump()
        if r.wav_pending:raise TimeoutError('Sin confirmación WAV')
    try:
        if qos:
            from monitor.historico.v16.audio_qos import audio_qos
            qos_context=audio_qos("user_interactive")
            report["qos"]=qos_context.__enter__()
        warmup();feedback_warmup()
        p=parameters or FMParameters(preset='Piano Virtual',waveform='virtual',virtual_model='piano',
            string_decay=4.,string_position=.12,string_brightness=.78,oscillator_levels=(1.,0.,0.),notes=())
        report["read_timeout_ms"]=read_timeout_ms
        report["credits"]=credits
        report["chunk_size"]=chunk_size
        report["initial_queue_ms"]=target*chunk_size/20
        report["preset"]=p.preset
        report['async_synth']=async_synth
        report['worker_wakeup']=worker_wakeup
        if async_synth:
            from monitor.historico.v16.synth_process import SynthProcess
            source=SynthProcess(20000,p)
        else:source=FMSource(20000,p)
        source.prepare_audio();source.target_blocks=target
        if freeze:gc.collect();gc.freeze();frozen=True
        with Connection('1060031107') as c:
            original_timeout=c.socket.gettimeout()
            c.socket.settimeout(read_timeout_ms/1000)
            if worker_wakeup:
                from monitor.historico.v16.synth_process import read_with_audio_wakeup
                from types import SimpleNamespace
                raw_connection=SimpleNamespace(socket=c.socket,read=c.read)
                c.read=lambda:read_with_audio_wakeup(raw_connection,source)
            if scheduler:
                original_read=c.read
                def observed_read():
                    began=time.monotonic();cpu=time.process_time();data=original_read();elapsed=time.monotonic()-began
                    if elapsed>=.020:
                        item=dict(start=began,wall_ms=elapsed*1000,cpu_ms=(time.process_time()-cpu)*1000)
                        if len(report['slow_reads'])<256:report['slow_reads'].append(item)
                        else:report['slow_reads_omitted']+=1
                    return data
                c.read=observed_read
            r=OutputReceiver(c,lambda records:None);r.wav_live_credits=credits;r.wav_chunk_points=chunk_size;receiver=r
            if trace_path:
                from monitor.historico.v16.transport_trace import NumericTransportTrace
                r.transport_trace=NumericTransportTrace();gc.callbacks.append(gc_trace)
                source.audio_trace=r._trace_transport
            r.select(Mode.SPI);prior=r.config;gen=r.generator().active
            r.wav_request();wait(r)
            report['initial_wav']=r.wav_status.state.name
            require_available_wav(r,gen)
            report['prior']=dict(adc=asdict(prior),generator=asdict(gen))
            try:
                r.configure(Configuration(14,adc_rate));r.on_samples=collect
                if socket_probe:
                    from monitor.historico.v16.socket_probe import SocketProbe,ProcessSocketProbe
                    probe=(ProcessSocketProbe if probe_process else SocketProbe)(c.socket);probe.start()
                def status(s):
                    source.observe_status(s)
                    if source.target_blocks>report['max_target']:
                        now=time.monotonic();r._trace_transport('queue_growth',now,now,source.target_blocks)
                        report['queue_growth'].append(dict(time=now,target=source.target_blocks,actual_blocks=16-s.free_blocks))
                    report['max_target']=max(report['max_target'],source.target_blocks)
                    if s.state==State.PLAYING:report['min_blocks']=min(report['min_blocks'],16-s.free_blocks)
                r.on_wav=status;r.set_wav_levels(amplitude,1.65);r.wav_request(1,source,20000)
                control.send(('ready',))
                began=time.monotonic()
                while time.monotonic()-began<seconds:
                    control_start=time.monotonic();control_cpu=time.thread_time() if trace_path else None
                    while control.poll():
                        message=control.recv()
                        if message[0]=='stop':raise InterruptedError('Ensayo cancelado')
                        _,notes,note_id,pedal=message
                        source.update(replace(p,notes=notes,note_id=note_id,virtual_sustain=pedal))
                    if control_cpu is not None:r._trace_transport('controls',control_start,time.monotonic(),cpu_seconds=time.thread_time()-control_cpu)
                    pump_start=time.monotonic();pump_cpu=time.thread_time() if trace_path else None
                    if scheduler:usage_before=resource.getrusage(resource.RUSAGE_SELF)
                    r.pump()
                    if scheduler:
                        elapsed=time.monotonic()-pump_start
                        usage_after=resource.getrusage(resource.RUSAGE_SELF)
                        if elapsed>=.020:
                            item=dict(start=pump_start,wall_ms=elapsed*1000,cpu_ms=((usage_after.ru_utime+usage_after.ru_stime)-(usage_before.ru_utime+usage_before.ru_stime))*1000,
                                minor_faults=usage_after.ru_minflt-usage_before.ru_minflt,major_faults=usage_after.ru_majflt-usage_before.ru_majflt,
                                voluntary_switches=usage_after.ru_nvcsw-usage_before.ru_nvcsw,involuntary_switches=usage_after.ru_nivcsw-usage_before.ru_nivcsw)
                            if len(report['slow_pumps'])<256:report['slow_pumps'].append(item)
                            else:report['slow_pumps_omitted']+=1
                    if pump_cpu is not None:r._trace_transport('pump',pump_start,time.monotonic(),cpu_seconds=time.thread_time()-pump_cpu)
                    if r.wav_status and r.wav_status.state in (State.UNDERRUN,State.FAULT,State.DONE):break
                s=r.wav_status
                report.update(seconds=time.monotonic()-began,state=s.state.name,reason=int(s.reason),
                    played=s.played,max_ack_gap_ms=source._max_ack_gap*1000,transport=source.transport_metrics,adc_status=r.decoder.status)
                report['ok']=s.state==State.PLAYING and not s.reason and report['max_target']==target
                r.wav_request(3);wait(r)
            finally:
                c.socket.settimeout(original_timeout)
                if probe is not None:
                    try:probe.close()
                    except Exception as exc:report['probe_close_error']=str(exc)
                r.on_samples=lambda records:None
                try:
                    r.wav_request(3);wait(r);r.configure(prior);r.generator(GeneratorConfig(**asdict(gen)))
                    report['final']=dict(adc=asdict(r.config),generator=asdict(r.generator().active),wav=r.wav_status.state.name)
                    report['restored']=report['final']['adc']==asdict(prior) and report['final']['generator']==asdict(gen) and report['final']['wav']=='IDLE'
                except Exception as exc:report['restore_error']=str(exc)
                send_batch()
    except Exception as exc:report['error']=str(exc);report['ok']=False
    finally:
        if async_synth and source is not None:
            report['max_worker_render_ms']=source.max_worker_render_ms
            source.close()
        if gc_trace in gc.callbacks:gc.callbacks.remove(gc_trace)
        if trace_path and receiver is not None:
            trace=receiver.transport_trace.export() if receiver.transport_trace is not None else dict(events=[],metadata={})
            Path(trace_path).write_text(json.dumps(trace)+"\n")
            report["trace_path"]=str(trace_path)
            if probe is not None:
                probe_path=Path(trace_path).with_suffix(".socket.npz")
                report["socket_probe"]=probe.save(probe_path)
                report["socket_probe_path"]=str(probe_path)
            report["trace_limit_reached"]=trace["metadata"].get("overwritten",0)>0
        if frozen:gc.unfreeze()
        if qos_context is not None:
            try:qos_context.__exit__(None,None,None)
            except Exception as exc:report['qos_error']=str(exc);report['ok']=False
        control.send(('done',report));control.close()

def run_case(target,seconds,freeze,pause_ms=75,trace_path=None,shared_adc=False,adc_rate=100000,qos=False,socket_probe=False,amplitude=1.0,parameters=None,scheduler=False,read_timeout_ms=100,probe_process=False,credits=2,voices=11,async_synth=False,worker_wakeup=False,chunk_size=480):
    context=mp.get_context('spawn');parent,child=context.Pipe()
    from monitor.historico.v16.adc_ipc import SharedAdcRing
    adc=SharedAdcRing(context) if shared_adc else context.Queue(maxsize=32)
    process=context.Process(target=owner,args=(child,adc,target,seconds,freeze,trace_path,adc_rate,qos,socket_probe,amplitude,parameters,scheduler,read_timeout_ms,probe_process,credits,async_synth,worker_wakeup,chunk_size))
    process.start();child.close()
    result=None;ready=False;step=-1;last_index=last_timestamp=None;count=0;gc_ms=[];pauses=[];pause_events=[]
    started=time.monotonic();deadline=started+seconds+60;next_gc=started+1
    def consume(data):
        nonlocal last_index,last_timestamp,count
        last_index,last_timestamp,length=validate_adc_batch(data,last_index,last_timestamp,1000000//adc_rate);count+=length
    try:
        while result is None or process.is_alive():
            while result is None and parent.poll():
                message=parent.recv()
                if message[0]=='ready':ready=True;started=time.monotonic()
                else:result=message[1]
            while True:
                try:consume(adc.get_nowait())
                except queue.Empty:break
            now=time.monotonic()
            if ready and result is None:
                current=int((now-started)/.35)
                if current!=step:
                    step=current;base=36+(step%4)*7
                    notes=tuple((base+i,70+i*5%55) for i in range(voices)) if step%4!=3 else ()
                    parent.send(('update',notes,step+1,step%4!=3))
                if now>=next_gc:
                    before=time.monotonic();gc.collect();gc_ms.append((time.monotonic()-before)*1000)
                    time.sleep(pause_ms/1000);after=time.monotonic();pauses.append((after-before)*1000);pause_events.append(dict(start=before,end=after,gc_ms=gc_ms[-1]));next_gc=now+1
            if now>deadline:raise TimeoutError('Audio owner no terminó')
            if not process.is_alive() and result is None:raise RuntimeError('Audio owner se cerró sin reporte')
            time.sleep(.001)
        process.join()
        while True:
            try:consume(adc.get(timeout=.1))
            except queue.Empty:break
        result['voices']=voices
        result['adc_ipc']='shared_ring' if shared_adc else 'queue';result['ipc_samples']=count;result['ipc_ok']=count==result['sent_samples']
        result['parent_pause_events']=pause_events
        result['parent_gc_max_ms']=max(gc_ms,default=0)
        result['parent_pause_max_ms']=max(pauses,default=0)
        result['ok']=result.get('ok',False) and result['ipc_ok'] and result['restored']
        return result
    finally:
        if process.is_alive():
            try:parent.send(('stop',))
            except (BrokenPipeError,EOFError):pass
            process.join(10)
        if process.is_alive():process.terminate();process.join();print('ERROR: owner terminado forzosamente; verificar restauración Q',flush=True)
        parent.close();adc.close();adc.join_thread()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--seconds',type=float,default=30);p.add_argument('--freeze-worker',action='store_true');p.add_argument('--parent-pause-ms',type=float,default=75);p.add_argument('--targets',type=int,nargs='+',choices=range(2,17),default=[5,4,3]);p.add_argument('--timings',action='store_true');p.add_argument('--shared-adc',action='store_true');p.add_argument('--adc-rate',type=int,choices=(40000,100000),default=100000);p.add_argument("--qos",action="store_true");p.add_argument("--socket-probe",action="store_true");p.add_argument("--amplitude",type=float,choices=(1.0,2.5),default=1.0);p.add_argument("--presets",nargs="+");p.add_argument("--scheduler",action="store_true");p.add_argument("--read-timeout-ms",type=int,choices=(5,20,100),default=100);p.add_argument("--probe-process",action="store_true");p.add_argument("--credits",type=int,choices=(1,2,3,4),default=2);p.add_argument("--voices",type=int,choices=range(12),default=11);p.add_argument("--async-synth",action="store_true");p.add_argument("--worker-wakeup",action="store_true");p.add_argument("--chunk-size",type=int,choices=(240,480),default=480);args=p.parse_args()
    if args.probe_process:args.socket_probe=True;args.timings=True
    if args.worker_wakeup:args.async_synth=True
    try:require_exclusive_monitor()
    except RuntimeError as exc:p.error(str(exc))
    report=dict(scope='Dedicated audio/Q owner, bounded lossless ADC IPC, simulated controls and forced parent GC; no GUI/acoustic acceptance',cases=[])
    folder=ROOT/'diagnosticos/resultados_piano/eficiencia_v16'
    path=folder/(datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')+'_audio_owner.json')
    presets=[(None,None)]
    if args.presets:
        from monitor.historico.v16.fm_source import PRESETS
        if any(name not in PRESETS for name in args.presets):p.error('Preset desconocido')
        from diagnosticos.synth_presets_v16 import panel_presets
        snapshots=panel_presets(args.presets)
        # Preserve repeated presets and their order for alternating trials.
        presets=[(name,snapshots[name]) for name in args.presets]
    for index,(name,parameters) in enumerate(presets):
        for target in args.targets:
            trace_path=path.with_name(path.stem+f'_preset{index}_target{target}_trace.json') if args.timings else None
            case=run_case(target,args.seconds,args.freeze_worker,args.parent_pause_ms,trace_path,args.shared_adc,args.adc_rate,args.qos,args.socket_probe,args.amplitude,parameters,args.scheduler,args.read_timeout_ms,args.probe_process,args.credits,args.voices,args.async_synth,args.worker_wakeup,args.chunk_size);report['cases'].append(case)
            path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(case),flush=True)
            if not case['restored']:raise RuntimeError('Q no restaurado: no continuar ensayos')
            if not case['ok']:break
    print(path,flush=True)

if __name__=='__main__':main()
