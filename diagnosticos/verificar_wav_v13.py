"""Ensayo físico acotado WAV/ADC; no cambia el firmware instalado."""
import json,time,tempfile
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from monitor.historico.v13.wav_source import prepare_wav
from monitor.historico.v13.receiver.unoq_usb import Connection
from monitor.historico.v13.receiver.unoq_config_receiver import OutputReceiver
from monitor.historico.v13.receiver.unoq_switch import Mode
from monitor.historico.v13.receiver.unoq_wav import State


def main():
    result={'pruebas':[]}
    rows=[]; states=[]
    with Connection('1060031107') as connection:
        receiver=OutputReceiver(connection,rows.extend,print)
        receiver.on_wav=states.append
        receiver.select(Mode.SPI)
        prior=receiver.generator()
        result['generador_previo']=prior.active.__dict__
        result['adc']=receiver.config.__dict__
        try:
            receiver.wav_request()
            deadline=time.monotonic()+3
            while receiver.wav_pending and time.monotonic()<deadline: receiver.pump()
            if receiver.wav_status is None: raise RuntimeError('Sin capacidad WAV confirmada')
            with tempfile.TemporaryDirectory() as directory:
                t=np.arange(44100*2)/44100
                path=Path(directory)/'stereo.wav'
                wavfile.write(path,44100,np.column_stack((.6*np.sin(2*np.pi*997*t),.6*np.sin(2*np.pi*2003*t))).astype('float32'))
                for channel in ('L','R','Mix'):
                    source=prepare_wav(path,channel)
                    rows.clear();states.clear()
                    receiver.wav_request(1,source.codes)
                    deadline=time.monotonic()+8
                    while time.monotonic()<deadline:
                        receiver.pump()
                        if states and states[-1].state in (State.DONE,State.UNDERRUN,State.FAULT): break
                    final=receiver.wav_status
                    entry={'canal':channel,'estado':final.state.name,'reason':final.reason,'accepted':final.accepted,'played':final.played,'total':final.total,'pares_adc':len(rows)}
                    if len(rows)>receiver.config.rate:
                        samples=np.asarray(rows,dtype=np.float64)[-int(receiver.config.rate):,1:3]
                        peaks=[]; tones=[]
                        for trace in samples.T:
                            spec=np.abs(np.fft.rfft((trace-trace.mean())*np.hanning(len(trace))))
                            freq=np.fft.rfftfreq(len(trace),1/receiver.config.rate)
                            peaks.append(float(freq[np.argmax(spec[1:])+1]))
                            tones.append({str(f):float(spec[np.argmin(abs(freq-f))]/max(spec[1:])) for f in (997,2003)})
                        entry['picos_adc_hz']=peaks
                        entry['tonos_relativos']=tones
                        expected=(997,2003) if channel=='Mix' else (997,) if channel=='L' else (2003,)
                        if any(tone[str(f)]<.5 for tone in tones for f in expected): raise RuntimeError('Tonos incorrectos: '+str(entry))
                    result['pruebas'].append(entry)
                    if final.state!=State.DONE or final.played!=len(source.codes): raise RuntimeError(str(entry))
                    for _ in range(4): receiver.pump()
                source=prepare_wav(path,'L')
                receiver.wav_request(1,source.codes)
                deadline=time.monotonic()+4
                while time.monotonic()<deadline:
                    receiver.pump()
                    if receiver.wav_status and receiver.wav_status.state==State.PLAYING: break
                receiver.wav_request(3)
                deadline=time.monotonic()+3
                while receiver.wav_pending and time.monotonic()<deadline: receiver.pump()
                result['detener_estado']=receiver.wav_status.state.name
                if receiver.wav_status.state!=State.IDLE: raise RuntimeError('Detener no confirmado')
            after=receiver.generator()
            result['generador_restaurado']=after.active==prior.active and after.running==prior.running
            result['ok']=result['generador_restaurado']
        finally:
            if receiver.wav_codes is not None or receiver.wav_status and receiver.wav_status.state in (State.PLAYING,State.UNDERRUN,State.FAULT):
                receiver.wav_request(3)
                deadline=time.monotonic()+3
                while receiver.wav_pending and time.monotonic()<deadline: receiver.pump()
            receiver.close()
            folder=Path('diagnosticos/resultados_wav');folder.mkdir(exist_ok=True)
            (folder/'20261005_20ksps_regresion.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
