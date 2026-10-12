"""Sigue la quinta por mezcla, niveles del receiver y trama DAC, sin abrir el Q."""
import json,wave
from dataclasses import replace
from pathlib import Path
import numpy as np
from diagnosticos.synth_presets_v16 import panel_presets
from monitor.v16.fm_source import FMSource
from monitor.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.v16.receiver.unoq_wav import chunk

def run():
    notes=(57,64)  # Quinta de la captura más reciente del usuario.
    folder=Path('diagnosticos/resultados_piano/eficiencia_v16/quinta_cadena')
    folder.mkdir(parents=True,exist_ok=True)
    p=panel_presets(['Seno limpio'])['Seno limpio']
    rows=[]
    for velocity in ((90,94),(127,127)):
        for vol in (.5,.75,.8,.97,1.25,2.5):
            source=FMSource(20000,replace(p,notes=((notes[0],velocity[0]),(notes[1],velocity[1])),gate=True))
            receiver=OutputReceiver.__new__(OutputReceiver)
            receiver.wav_codes=source;receiver.wav_levels=(vol,1.65);receiver.wav_previous_levels=None
            blocks=[];gains=[]
            for i in range(167):
                codes=receiver._wav_chunk_codes(i*480,(i+1)*480)
                frame=chunk(0x80000001,1,i*480,codes)
                received=np.frombuffer(frame,dtype='<u2',count=480,offset=28)
                np.testing.assert_array_equal(received,codes)
                blocks.append(received.copy());gains.append(source.compressor_gain)
            codes=np.concatenate(blocks)
            audio=codes[40000:80000].astype(float)*3.3/4095-1.65
            t=np.arange(len(audio))/20000
            basis=np.column_stack([f(2*np.pi*440*2**((n-69)/12)*t)
                                   for n in notes for f in (np.sin,np.cos)]+[np.ones(len(t))])
            fitted=basis@np.linalg.lstsq(basis,audio,rcond=None)[0]
            row=dict(notes=notes,vol=vol,velocity=velocity,codes_min=int(codes.min()),codes_max=int(codes.max()),
                     min_gain=min(gains),max_gain=max(gains),
                     residual_db=float(20*np.log10(np.std(audio-fitted)/np.std(fitted))),
                     transport_exact=True)
            rows.append(row)
            # Equal peak for listening comparisons: this is an offline reference,
            # not a recording of the actual Q output or amplifier.
            if velocity==(90,94) and vol in (.75,.97):
                centered=codes.astype(float)-2047.5
                pcm=np.rint(centered/max(abs(centered))*.8*32767).astype('<i2')
                with wave.open(str(folder/f'quinta_vol_{vol:g}_referencia.wav'),'wb') as output:
                    output.setnchannels(1);output.setsampwidth(2);output.setframerate(20000)
                    output.writeframes(pcm.tobytes())
    (folder/'resultados.json').write_text(json.dumps(rows,indent=2))
    print(json.dumps(rows,indent=2))

if __name__=='__main__':run()
