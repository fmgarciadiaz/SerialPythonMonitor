"""Ensayo sostenido de tasa WAV negociada, con restauración ADC/DAC."""
import argparse,json,time
from collections import deque
from dataclasses import asdict
from pathlib import Path
import numpy as np
from monitor.v13.receiver.unoq_usb import Connection
from monitor.v13.receiver.unoq_config_receiver import OutputReceiver
from monitor.v13.receiver.unoq_acquisition import Configuration
from monitor.v13.receiver.unoq_switch import Mode
from monitor.v13.receiver.unoq_wav import State


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--rate',type=int,choices=(20000,40000,50000),required=True)
    parser.add_argument('--seconds',type=int,default=120)
    parser.add_argument('--adc-rate',type=int,default=40000)
    args=parser.parse_args()
    t=np.arange(args.rate*args.seconds)/args.rate
    volts=(np.sin(2*np.pi*997*t)+np.sin(2*np.pi*12003*t))*.6+1.65
    codes=np.rint(volts*4095/3.3).astype('<u2')
    del t,volts
    rows=deque(maxlen=args.adc_rate*2); count=0
    result={'wav_rate':args.rate,'seconds':args.seconds,'adc_rate':args.adc_rate,'ok':False}
    last_print=0; min_free=16;min_reserve=999;started=None;done=None
    def collect(batch):
        nonlocal count
        count+=len(batch);rows.extend(batch)
    def status(reply):
        nonlocal started,done,min_free,min_reserve,last_print
        now=time.monotonic()
        if reply.reason: raise RuntimeError('WAV rechazado: '+str(reply))
        if reply.state==State.PLAYING:
            if started is None: started=now
            min_free=min(min_free,reply.free_blocks)
            if reply.accepted<reply.total: min_reserve=min(min_reserve,(reply.accepted-reply.played)/reply.rate)
        if reply.state==State.DONE: done=now
        if reply.state in (State.UNDERRUN,State.FAULT): raise RuntimeError('WAV interrumpido: '+str(reply))
        if now-last_print>20:
            print(f'{reply.state.name}: {reply.played/reply.rate:.1f}/{reply.total/reply.rate:.1f}s; ADC {count}',flush=True)
            last_print=now
    with Connection('1060031107') as connection:
        receiver=OutputReceiver(connection,collect,print)
        receiver.select(Mode.SPI)
        prior_adc=receiver.config
        prior_gen=receiver.generator()
        result['adc_previo']=asdict(prior_adc);result['generador_previo']=asdict(prior_gen.active)
        try:
            receiver.configure(Configuration(14,args.adc_rate))
            receiver.on_wav=status
            receiver.wav_request()
            deadline=time.monotonic()+3
            while receiver.wav_pending and time.monotonic()<deadline:receiver.pump()
            if receiver.wav_status is None:raise RuntimeError('Sin capacidad WAV')
            count=0;rows.clear()
            receiver.wav_request(1,codes,args.rate)
            deadline=time.monotonic()+args.seconds+10
            while done is None and time.monotonic()<deadline:receiver.pump()
            final=receiver.wav_status
            result['final']=asdict(final);result['pares_adc']=count
            if final.state!=State.DONE or final.played!=len(codes) or done is None:raise RuntimeError('No finalizó completo')
            result['duracion_observada_s']=done-started
            result['reserva_min_s']=min_reserve
            data=np.asarray(rows,dtype=np.float64)[-args.adc_rate:,1:3]
            spectra=[]
            for trace in data.T:
                spectrum=np.abs(np.fft.rfft((trace-trace.mean())*np.hanning(len(trace))))
                freq=np.fft.rfftfreq(len(trace),1/args.adc_rate)
                spectra.append({str(f):float(spectrum[np.argmin(abs(freq-f))]/max(spectrum[1:])) for f in (997,12003)})
            result['tonos_relativos']=spectra
            if any(d[str(f)]<.3 for d in spectra for f in (997,12003)):raise RuntimeError('Tonos incorrectos')
            if abs(result['duracion_observada_s']-args.seconds)>.3:raise RuntimeError('Duración fuera de tolerancia')
            # Confirm STOP during another session.
            receiver.wav_request(1,codes[:args.rate*2],args.rate)
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                receiver.pump()
                if receiver.wav_status and receiver.wav_status.state==State.PLAYING:break
            receiver.wav_request(3)
            deadline=time.monotonic()+3
            while receiver.wav_pending and time.monotonic()<deadline:receiver.pump()
            result['stop']=receiver.wav_status.state.name
            if receiver.wav_status.state!=State.IDLE:raise RuntimeError('Stop no confirmado')
            result['ok']=True
        except Exception as exc:
            result['error']=str(exc)
            raise
        finally:
            try:
                if receiver.wav_codes is not None or receiver.wav_status and receiver.wav_status.state in (State.BUFFERING,State.PLAYING,State.UNDERRUN,State.FAULT):
                    receiver.wav_request(3)
                    deadline=time.monotonic()+3
                    while receiver.wav_pending and time.monotonic()<deadline:receiver.pump()
                receiver.configure(prior_adc)
                restored=receiver.generator()
                result['restaurado']=receiver.config==prior_adc and restored.active==prior_gen.active and restored.running==prior_gen.running
                result['ok']=result['ok'] and result['restaurado']
            except Exception as exc:
                result['restaurado']=False
                result['restoration_error']=str(exc)
                result['ok']=False
            finally:
                receiver.close()
                folder=Path('diagnosticos/resultados_wav');folder.mkdir(exist_ok=True)
                (folder/f'20261005_{args.rate}_{args.seconds}s_adc{args.adc_rate}.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
