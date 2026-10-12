"""Held-out evaluation and a standalone acoustic comparison figure."""
import json
import numpy as np
from scipy.ndimage import uniform_filter1d
from ajustar_piano_referencia import prepare,render,error,features,write_audio,FOLDER,RATE

def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    cases=[]
    for note,velocity,name in ((60,48,'C4v6'),(63,60,'D#4v8')):
        reference,b,info=prepare(name,note)
        old=render(note,velocity,False);new=render(note,velocity,True)
        row=dict(name=name,note=note,velocity=velocity,identification=info,
                 before=error(reference,old,note,b),after=error(reference,new,note,b))
        cases.append(row)
        target=min(.025,*[np.sqrt(np.mean(x*x))*.8 for x in (reference,old,new)])
        for label,x in (('referencia',reference),('antes',old),('ajustado',new)):
            write_audio(FOLDER/(name+'_'+label+'.wav'),x,target)
    (FOLDER/'validacion_reservada.json').write_text(json.dumps(cases,indent=2)+'\n')
    note=60;velocity=60;name='C4v8'
    reference,b,_=prepare(name,note)
    audio=(reference,render(note,velocity,False),render(note,velocity,True))
    labels=('Referencia Yamaha C5','Modelo anterior','Modelo identificado')
    colors=('#444444','#dd9b40','#109e9a')
    fig,axes=plt.subplots(1,3,figsize=(14,4),layout='constrained')
    for x,label,color in zip(audio,labels,colors):
        normalized=x/max(np.sqrt(np.mean(x*x)),1e-12)
        t=np.arange(len(x))/RATE
        rms=np.sqrt(uniform_filter1d(normalized**2,size=200))
        axes[0].plot(t,rms,label=label,color=color)
        amplitude,_=features(normalized,note,b)
        axes[1].plot(np.arange(1,33),20*np.log10(amplitude+1e-12),color=color,marker='.',label=label)
        axes[2].plot(t,20*np.log10(np.maximum(rms,1e-5)),color=color,label=label)
    axes[0].set(xlim=(0,.25),xlabel='Tiempo (s)',ylabel='RMS local / RMS total',title='Ataque · ventanas de 10 ms')
    axes[1].set(xlim=(1,24),xlabel='Parcial',ylabel='Nivel relativo (dB)',title='Balance · 0,2–1,1 s')
    axes[2].set(xlim=(0,4),ylim=(-40,20),xlabel='Tiempo (s)',ylabel='RMS relativo (dB)',title='Evolución · cuatro segundos')
    for ax in axes:ax.grid(alpha=.2)
    axes[0].legend(fontsize=8)
    fig.suptitle('Do4, velocidad MIDI 60 · mismo RMS total · salida mono 20 kHz')
    fig.savefig(FOLDER/'comparacion_do4.png',dpi=160)
    fig.savefig(FOLDER/'comparacion_do4.svg')
    print(json.dumps(cases,indent=2))

if __name__=='__main__':main()
