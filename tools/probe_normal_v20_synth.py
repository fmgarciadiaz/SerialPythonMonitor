"""Bounded normal installed GUI connect/disconnect/reconnect; no Q deployment."""
import json,sys,time,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['MONITOR_V19_CHILD_STAGE_TIMING']='0'
from PySide6 import QtCore,QtWidgets
from monitor.v20 import app as mod
from monitor.v20.io.live_connection import installed_identity
from monitor.v20.board_owner import board_owner


def main():
    folder=ROOT/'diagnosticos/resultados_v20/normal_synth_journal20_20261104'
    folder.mkdir(exist_ok=False)
    serial='1060031107'
    with board_owner(serial,'normal reconnect identity before'):
        before=installed_identity(serial)
    report=dict(identity_before=before,stages=[],errors=[],sessions=[],ok=False,
                scope='Normal installed V20; ADC14 dual40k, DX Piano default20k; one Play20s, no RADIO/private overrides')
    def save(): (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    from monitor.v20.io import receiver_process
    original=receiver_process.ReceiverProcess
    class ObservedReceiver(original):
        def __init__(self,*args,**options):
            options.update(capture_lifecycle=True,snapshot_dir=str(folder/'sessions'),recovery_seconds=10)
            super().__init__(*args,**options)
    receiver_process.ReceiverProcess=ObservedReceiver
    qt=QtWidgets.QApplication([]);qt.setQuitOnLastWindowClosed(False)
    w=mod.SerialMonitorWindow();w.show()
    QtWidgets.QMessageBox.critical=lambda parent,title,text:report['errors'].append(str(text))
    QtWidgets.QMessageBox.warning=lambda parent,title,text:report['errors'].append(str(text))
    started=time.monotonic();phase='discovery';phase_at=started;cycle=0;samples_at=0
    observed={};initial_session=None;play_session=None;start_played=0
    original_wav=w._wav_confirmed
    def wav_status(status):
        observed.update(state=int(status.state),session=status.session,played=status.played,accepted=status.accepted,rate=status.rate,reason=status.reason)
        original_wav(status)
    w._wav_confirmed=wav_status
    def record(stage):
        report['stages'].append(dict(stage=stage,elapsed=time.monotonic()-started,
            connection=w.connection_state,samples=w.sample_counter,
            visible=w.isVisible(),exposed=bool(w.windowHandle() and w.windowHandle().isExposed()),
            shutdown=getattr(w,'_shutdown_status',None),wav=dict(observed),generator_status=w.generator_status.text(),start_phase=w.fm_panel._start_phase))
        save()
    def transition(next_phase):
        nonlocal phase,phase_at
        phase=next_phase;phase_at=time.monotonic();record(phase)
    def tick():
        nonlocal cycle,samples_at,initial_session,play_session,start_played
        try:
            now=time.monotonic()
            if phase=='discovery' and w.refresh_button.isEnabled():
                index=w.port_combo.findData(serial)
                if index<0:raise RuntimeError('Q missing from normal discovery')
                w.port_combo.setCurrentIndex(index)
                w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(14))
                w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(40000))
                w.connect_serial();transition('connecting1')
            elif phase.startswith('connecting') and w.connection_state=='connected' and w._wav_capable:
                initial_session=observed.get('session')
                w.generator_mode.setCurrentIndex(5)
                w.fm_panel.play.click();transition('preparing_synth')
            elif phase=='preparing_synth' and observed.get('state')==2 and observed.get('session')!=initial_session:
                play_session=observed['session'];start_played=observed['played']
                transition('playing_synth')
            elif phase=='playing_synth':
                if observed.get('state')!=2 or w.fm_panel.source is None:raise RuntimeError('Synth stopped before hold')
                if now-phase_at>=20:
                    if observed['played']-start_played<390000:raise RuntimeError('Insufficient DAC progress')
                    report['played_delta']=observed['played']-start_played
                    report['journal_path']=str(w.fm_panel._start_journal.path)
                    record('hold_complete');w.fm_panel.play.click();transition('stopping_synth')
            elif phase=='stopping_synth' and observed.get('session')==play_session and observed.get('state') in (0,3):
                cycle=2;record('stop_confirmed');w.close();transition('closing')
            elif phase in ('closing','failed_closing') and w.serial_worker is None and not getattr(w,'_close_pending',False):
                timer.stop();qt.quit();return
            if report['errors'] and phase not in ('failed_closing','closing'):
                raise RuntimeError('GUI reported a connection error')
            if now-phase_at>(75 if phase in ('failed_closing','closing') or phase.startswith('disconnecting') else 120 if phase=='preparing_synth' else 35):
                raise RuntimeError('Timeout in '+phase)
        except Exception as exc:
            report['errors'].append(str(exc));save()
            if phase=='failed_closing':
                timer.stop();qt.quit()
            else:w.close();transition('failed_closing')
    timer=QtCore.QTimer();timer.setInterval(100);timer.timeout.connect(tick);timer.start()
    record('window_ready');qt.exec()
    receiver_process.ReceiverProcess=original
    report['sessions']=[json.loads(p.read_text()) for p in sorted((folder/'sessions').glob('session_*.json'))]
    with board_owner(serial,'normal reconnect identity after'):
        report['identity_after']=installed_identity(serial)
    report['ok']=(cycle==2 and not report['errors'] and report['identity_after']==before
        and len(report['sessions'])==1 and all(s.get('hardware_restored') is True
        and s.get('recovery',{}).get('seconds',0)>=10 and not s.get('errors') for s in report['sessions']))
    save();print(json.dumps(dict(ok=report['ok'],errors=report['errors'],report=str(folder/'report.json'))))
    return 0 if report['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
