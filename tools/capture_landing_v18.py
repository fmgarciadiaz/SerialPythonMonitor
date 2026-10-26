"""Generate V18 landing demos offline; never connect to or modify the Q."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys,time,json,shutil
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from PyQt6 import QtCore,QtGui,QtWidgets
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from monitor.v18.app import SerialMonitorWindow

def main():
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setStyle('Fusion')
    assets=ROOT/'assets';archive=assets/'historico/antes_v18_20261026'
    archive.mkdir(parents=True,exist_ok=True)
    cases=[('monitor_vt',0,0),('monitor_fft_spectrum',1,0),
           ('monitor_heatmap',2,0),('monitor_bode',3,0),
           ('monitor_generator',0,0),('monitor_filter',1,0),
           ('monitor_wav',0,4),('monitor_synth',0,5)]
    manifest=[]
    with patch('monitor.v18.app.usb_devices',return_value=[]),patch('monitor.v18.app.list_ports.comports',return_value=[]),patch('monitor.v18.app.Connection',side_effect=RuntimeError('Offline documentation only')),patch('monitor.v18.fm_panel.FMPanel.refresh_midi',return_value=None):
        for name,mode,generator in cases:
            if len(sys.argv)>1 and name not in sys.argv[1:]:continue
            w=SerialMonitorWindow()
            try:
                w.resize(1440,1000);w.show();app.processEvents()
                w.start_demo();w.demo_timer.stop();w.render_timer.stop()
                w.generator_mode.setCurrentIndex(generator)
                d=w.spectral;d.size.setCurrentText('2048');d.set_mode(mode)
                if mode==2:d.seconds.setValue(2)
                w.h_scale=2500
                if name=='monitor_filter':
                    w.filter_source.setCurrentText('CH1')
                    d.channels[1].setCurrentText('FILTER')
                    for i in range(w.trigger_filter_tabs.count()):
                        if w.trigger_filter_tabs.tabText(i)=='Filtro':w.trigger_filter_tabs.setCurrentIndex(i)
                frames=[]
                def feed(count):
                    if mode in (1,2):
                        start=w.sample_counter
                        t=(np.arange(count)+start)/2500
                        envelope=.8+.2*np.sin(2*np.pi*.7*t)
                        a=1.65+envelope*(.8*np.sin(2*np.pi*80*t)+.25*np.sin(2*np.pi*220*t))
                        b=1.65+envelope*(.45*np.sin(2*np.pi*80*t-.5)+.08*np.sin(2*np.pi*220*t-1))
                        w.handle_batch([{'Muestra':float(start+i+1),'Tiempo (us)':float((start+i)*400),'CH1':float(a[i]),'CH2':float(b[i])} for i in range(count)])
                    else:
                        for _ in range(max(1,count//50)):w._generate_demo_samples()
                feed(10000)
                for frame in range(24):
                    feed(1000 if mode==2 else 200)
                    if mode==3:
                        freq=np.geomspace(1,1000,90)
                        size=min(90,12+frame*4)
                        h=1/(1+1j*freq/35)
                        panel=d.bode.panels[0]
                        panel.result=list(zip(freq[:size],20*np.log10(abs(h[:size])),np.angle(h[:size],deg=True)))
                        d.bode.status.setText('Demo · filtro RC simulado')
                        d.bode.start.setValue(1);d.bode.end.setValue(1000)
                        d.bode.draw();d.refresh_bode_view()
                    else:
                        d.last_fast_render=0;w.render_frame()
                        if mode==1:d._render_fft_analysis(w,2500,2048)
                        if mode==2:d._render_heatmaps(w,2048)
                    app.processEvents()
                    pix=w.grab().scaledToWidth(1000,QtCore.Qt.TransformationMode.SmoothTransformation)
                    image=pix.toImage().convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
                    ptr=image.bits();ptr.setsize(image.sizeInBytes())
                    frames.append(Image.frombytes('RGBA',(image.width(),image.height()),bytes(ptr)).convert('RGB'))
                png=assets/(name+'.png');gif=assets/(name+'.gif')
                if name!='monitor_generator' and png.exists() and not (archive/png.name).exists():shutil.copy2(png,archive/png.name)
                frames[12].save(png)
                palette=frames[0].quantize(colors=96)
                compact=[image.quantize(palette=palette,dither=Image.Dither.NONE) for image in frames]
                compact[0].save(gif,save_all=True,append_images=compact[1:],duration=125,loop=0,optimize=True)
                manifest.append(dict(name=name,source='V18 GUI, offline synthetic demo; no Q',frames=len(frames),gif_bytes=gif.stat().st_size))
                print(name,gif.stat().st_size,flush=True)
            finally:
                w.close();app.processEvents()
    target=assets/'landing_v18_manifest.json'
    if len(sys.argv)>1 and target.exists():
        names={item['name'] for item in manifest}
        manifest=[item for item in json.loads(target.read_text()) if item['name'] not in names]+manifest
    target.write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':main()
