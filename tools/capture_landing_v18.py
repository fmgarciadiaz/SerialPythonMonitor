"""Generate V18 landing demos offline; never connect to or modify the Q."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_SCALE_FACTOR','2')
import sys,time,json,shutil
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from PyQt6 import QtCore,QtGui,QtWidgets
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from monitor.v18.app import SerialMonitorWindow
from monitor.v18.receiver.unoq_acquisition import Configuration

def main():
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setStyle('Fusion')
    assets=ROOT/'assets';archive=assets/'historico/antes_v18_20261026'
    archive.mkdir(parents=True,exist_ok=True)
    cases=[('monitor_vt',0,0),('monitor_fft_spectrum',1,0),
           ('monitor_heatmap',2,0),('monitor_bode',3,0),
           ('monitor_generator',0,0),('monitor_filter',1,0),
           ('monitor_wav',0,4),('monitor_synth',0,5),
           ('monitor_radio_710',1,7),('monitor_radio_equ',1,7)]
    manifest=[]
    with patch('monitor.v18.app.usb_devices',return_value=[]),patch('monitor.v18.app.list_ports.comports',return_value=[]),patch('monitor.v18.app.Connection',side_effect=RuntimeError('Offline documentation only')),patch('monitor.v18.fm_panel.FMPanel.refresh_midi',return_value=None):
        for name,mode,generator in cases:
            if len(sys.argv)>1 and name not in sys.argv[1:]:continue
            w=SerialMonitorWindow()
            try:
                w.resize(1600,1100);w.show();app.processEvents()
                w.start_demo();w.demo_timer.stop();w.render_timer.stop()
                w.generator_mode.setCurrentIndex(generator)
                d=w.spectral;d.size.setCurrentText('2048');d.set_mode(mode)
                if mode==2:d.seconds.setValue(2)
                w.h_scale=2500
                radio=name.startswith('monitor_radio_')
                if radio:
                    w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(8))
                    w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(1860465))
                    w._auto_apply_timer.stop()
                    w.applied_configuration=Configuration(8,1860465)
                    w._sync_radio_input_controls()
                    d.size.setCurrentText('16384');d.channels[1].setCurrentText('Ninguno')
                    d.fft_mode.setCurrentText('Radio')
                    w.radio_frequency.setValue(710)
                    w.radio_candidates=[dict(frequency=f) for f in (670000,690000,710000,730000,750000)]
                    d.refresh_radio_overlay();d.radio_crop.setChecked(True)
                    for i in range(w.trigger_filter_tabs.count()):
                        if w.trigger_filter_tabs.tabText(i)=='Radio':w.trigger_filter_tabs.setCurrentIndex(i)
                    w.radio_status.setText('Demo AM · portadoras y audio simulados')
                    w.radio_output_panel.frequency.setText('RADIO · 710 kHz → A0 · Demo')
                    w.radio_output_panel.state.setText('Demo · audio simulado · sin salida A0')
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
                    if radio:
                        w._auto_apply_timer.stop()
                        w.applied_configuration=Configuration(8,1860465)
                        w._sync_radio_input_controls()
                        with QtCore.QSignalBlocker(w.radio_frequency):
                            w.radio_frequency.setRange(1,930)
                            w.radio_frequency.setValue(710)
                        w._sync_radio_dials()
                        w._refresh_status_boxes()
                        fs=w.applied_configuration.actual_rate
                        frequency=np.fft.rfftfreq(16384,1/fs)
                        rng=np.random.default_rng(frame)
                        power=np.full(len(frequency),-90.)+rng.normal(0,1.5,len(frequency))
                        for j,carrier in enumerate((670000,690000,710000,730000,750000)):
                            distance=frequency-carrier
                            peak=-24-5*abs(j-2)
                            power=np.maximum(power,peak-12*np.log10(1+(distance/110)**2))
                            for side in (-1,1):
                                envelope=-49-3*abs(j-2)+4*np.sin(frame*.3+j)
                                power=np.maximum(power,envelope-12*np.log10(1+((distance-side*1200)/450)**2))
                        d._draw_fft_arrays(w,fs,[power,None],frequency,'Spectre')
                        audio_t=np.arange(2048)/40000
                        audio=sum(.5/(j+1)*np.sin(2*np.pi*f*audio_t)*(.8+.2*np.sin(frame*.25+j)) for j,f in enumerate((125,500,1000,2000,4000)))
                        meter=w.radio_output_panel.audio_spectrum
                        meter.feed(audio,'demo',40000,0);meter.refresh(1+frame*.125,True,.6)
                        w.radio_output_panel.volume.audio_meter_level=.4+.12*np.sin(frame*.25)
                    elif mode==3:
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
                    pix=(w.generator_panel if name=='monitor_radio_equ' else w).grab()
                    image=pix.toImage().convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
                    ptr=image.bits();ptr.setsize(image.sizeInBytes())
                    frames.append(Image.frombytes('RGBA',(image.width(),image.height()),bytes(ptr)).convert('RGB'))
                png=assets/(name+'.png');gif=assets/(name+'.gif')
                if name!='monitor_generator' and png.exists() and not (archive/png.name).exists():shutil.copy2(png,archive/png.name)
                frames[12].save(png)
                # Render text at 2x device resolution; keep that lossless PNG.
                # GIF uses logical resolution and a full shared 256-color palette.
                frames=[image.resize((image.width//2,image.height//2),Image.Resampling.LANCZOS) for image in frames]
                # Preserve antialiased text: reserve 64 neutral shades instead
                # of building the palette from tiny thumbnails that lose glyphs.
                colors=frames[len(frames)//2].quantize(colors=192).getpalette()[:576]
                grayscale=[channel for value in range(0,256,4) for channel in (value,value,value)]
                palette=Image.new('P',(1,1));palette.putpalette(colors+grayscale)
                compact=[image.quantize(palette=palette,dither=Image.Dither.NONE) for image in frames]
                compact[0].save(gif,save_all=True,append_images=compact[1:],duration=80,loop=0,optimize=True)
                manifest.append(dict(name=name,source='V18 GUI, offline synthetic demo; no Q',frames=len(frames),gif_size=list(frames[0].size),png_scale=2,palette_colors=256,gif_bytes=gif.stat().st_size))
                print(name,gif.stat().st_size,flush=True)
            finally:
                w.close();app.processEvents()
    target=assets/'landing_v18_manifest.json'
    if len(sys.argv)>1 and target.exists():
        names={item['name'] for item in manifest}
        manifest=[item for item in json.loads(target.read_text()) if item['name'] not in names]+manifest
    target.write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':main()
