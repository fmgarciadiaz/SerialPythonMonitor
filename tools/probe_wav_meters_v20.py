"""Normal GUI WAV preview/FPS smoke with exact installed-pair restoration."""
import sys,os,json,time,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['MONITOR_V19_CHILD_STAGE_TIMING']='0'
from monitor.v20 import app as mod
from monitor.v20.io.live_connection import installed_identity
from monitor.v20.board_owner import board_owner
from monitor.v20.io import receiver_process
from scipy.io import wavfile
import numpy as np
from PySide6 import QtCore,QtWidgets


def main():
    folder=ROOT/'diagnosticos/resultados_v20/wav_meters_20261104'
    folder.mkdir(exist_ok=False)
    serial='1060031107'
    with board_owner(serial,'WAV meter identity before'):before=installed_identity(serial)
    original=receiver_process.ReceiverProcess
    class Observed(original):
        def __init__(self,*args,**kwargs):
            kwargs.update(capture_lifecycle=True,snapshot_dir=str(folder/'sessions'),recovery_seconds=10)
            super().__init__(*args,**kwargs)
    receiver_process.ReceiverProcess=Observed
    report=dict(identity_before=before,errors=[],stages=[],max_level=0.,max_band=0.,max_fps=0.,mmap_loaded=False,ok=False)
    def save():(folder/'report.json').write_text(json.dumps(report,indent=2))
    qt=QtWidgets.QApplication([]);qt.setQuitOnLastWindowClosed(False)
    window=mod.SerialMonitorWindow();window.show()
    QtWidgets.QMessageBox.critical=lambda parent,title,text:report['errors'].append(str(text))
    QtWidgets.QMessageBox.warning=lambda parent,title,text:report['errors'].append(str(text))
    tone_path=Path(tempfile.gettempdir())/'arduscopio_wav_meter_smoke.wav'
    t=np.arange(300000)/20000
    wavfile.write(tone_path,20000,np.rint((.6*np.sin(2*np.pi*1000*t)+.2*np.sin(2*np.pi*250*t))*32767).astype(np.int16))
    phase='discovery';began=time.monotonic();phase_at=began
    def transition(name):
        nonlocal phase,phase_at
        phase=name;phase_at=time.monotonic()
        report['stages'].append(dict(stage=name,elapsed=phase_at-began));save()
    def tick():
        try:
            report['max_level']=max(report['max_level'],float(getattr(window.wav_amplitude_dial,'audio_meter_level',0.) or 0.))
            report['max_band']=max(report['max_band'],float(np.max(window.wav_audio_spectrum.levels)))
            report['max_fps']=max(report['max_fps'],window.current_fps)
            report['mmap_loaded'] |= isinstance(window.wav_meter.codes,np.memmap)
            if phase=='discovery' and window.refresh_button.isEnabled():
                index=window.port_combo.findData(serial)
                if index<0:raise RuntimeError('Q not discovered')
                window.port_combo.setCurrentIndex(index)
                window.config_bits_combo.setCurrentIndex(window.config_bits_combo.findData(14))
                window.config_rate_combo.setCurrentIndex(window.config_rate_combo.findData(40000))
                window.connect_serial();transition('connecting')
            elif phase=='connecting' and window.connection_state=='connected' and window._wav_capable:
                window.generator_mode.setCurrentIndex(4)
                window.wav_rate.setCurrentIndex(window.wav_rate.findData(20000))
                window._wav_file_selected(str(tone_path));window.wav_play.click();transition('starting')
            elif phase=='starting' and window.wav_meter.status is not None and int(window.wav_meter.status.state)==2:
                transition('playing')
            elif phase=='playing' and time.monotonic()-phase_at>=6:
                status=window.wav_meter.status
                report['played']=int(status.played) if status else 0
                report['visible']=window.isVisible()
                window.grab().save(str(folder/'wav_panel.png'))
                window.wav_play.click();transition('stopping')
            elif phase=='stopping' and not window._wav_active:
                window.close();transition('closing')
            elif phase in ('closing','failed_closing') and window.serial_worker is None and not getattr(window,'_close_pending',False):
                timer.stop();qt.quit();return
            if report['errors'] and phase not in ('closing','failed_closing'):raise RuntimeError(report['errors'][-1])
            limit=75 if phase in ('closing','failed_closing') else 35
            if time.monotonic()-phase_at>limit:raise RuntimeError('Timeout: '+phase)
        except Exception as error:
            report['errors'].append(str(error));save()
            if phase=='failed_closing':timer.stop();qt.quit()
            else:window.close();transition('failed_closing')
    timer=QtCore.QTimer();timer.setInterval(100);timer.timeout.connect(tick);timer.start();qt.exec()
    receiver_process.ReceiverProcess=original
    report['sessions']=[json.loads(p.read_text()) for p in sorted((folder/'sessions').glob('session_*.json'))]
    with board_owner(serial,'WAV meter identity after'):report['identity_after']=installed_identity(serial)
    report['ok']=(not report['errors'] and report['identity_after']==before and report['mmap_loaded']
                  and report['max_level']>.1 and report['max_band']>.1 and report['max_fps']>0
                  and report.get('played',0)>100000 and len(report['sessions'])==1
                  and all(s.get('hardware_restored') and s.get('recovery',{}).get('seconds',0)>=10 for s in report['sessions']))
    save();tone_path.unlink(missing_ok=True)
    print(json.dumps({k:v for k,v in report.items() if k not in ('sessions','identity_before','identity_after')}))
    return 0 if report['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
