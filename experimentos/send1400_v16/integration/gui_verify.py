"""Exercise the unmodified V16 GUI/recorder at the new profile and a normal one."""
import os,sys,time
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
import diagnosticos.validar_grabacion_wav_v16 as check
from monitor.historico.v16.receiver.unoq_acquisition import Configuration
from monitor.historico.v16.receiver.unoq_config_receiver import OutputReceiver
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
class NumericReceiver(OutputReceiver):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.decoder.numeric=True
check.OutputReceiver=NumericReceiver
check.PROFILES=[Configuration(8,1403508),Configuration(14,40000)]
check.REPEATS=1;check.RECORD_MS=6000
check.OUTPUT=Path(__file__).resolve().parent/('gui_'+time.strftime('%Y%m%d_%H%M%S')+'.json')
check.report.update(scope='Production V16 GUI live ADC8/CH1 1403508 and ordinary ADC14/dual40000 PCM16 WAV;6s each',profiles=[{'bits':c.bits,'rate':c.rate} for c in check.PROFILES])
# The original verifier uses two channels for every ADC16 case; parameterize
# that assertion here without changing the production recorder or GUI.
# Run a specialized copy of main with expected profile.channels instead of2.
import inspect
source=inspect.getsource(check.main).replace("case['channels'] == 2", "case['channels'] == profile.channels")
source=source.replace('    def record():', """    def complete_live():
        if active['stopping']: return
        case=report['cases'][-1]
        profile,_=cases[active['index']]
        elapsed=time.perf_counter()-active['started']
        samples=window.sample_counter-active['before_samples']
        case.update(elapsed_s=elapsed,samples=samples,continuity_errors=getattr(window,'continuity_errors',[]),
                    applied={'bits':window.applied_configuration.bits,'rate':window.applied_configuration.rate},
                    dt_us=window._horizontal_dt_us(),ch2_enabled=window.graph_channel_actions['CH2'].isEnabled(),
                    wav_allowed=window._wav_recording_allowed())
        case['ok']=(samples>profile.actual_rate*elapsed*.95 and not getattr(window,'continuity_errors',[]) and
                    window.applied_configuration==profile and not case['ch2_enabled'] and not case['wav_allowed'])
        case['status']='PASS' if case['ok'] else 'FAIL'
        window.grab().save(str(OUTPUT.with_suffix('.png')))
        save();print('GUI LIVE',case['status'],profile.rate,samples,flush=True)
        if case['ok']:next_case()
        else:report['errors'].append('High-rate live GUI validation failed');finish()

    def record():""")
source=source.replace("        if window.applied_configuration != profile or not window.record_btn.isEnabled():","""        if profile.rate==1403508:
            if window.applied_configuration!=profile:
                report['errors'].append('High profile not confirmed');finish();return
            report['cases'].append({'configuration':asdict(profile),'stage':'live','status':'RUNNING'})
            active['before_samples']=window.sample_counter;active['started']=time.perf_counter()
            QtCore.QTimer.singleShot(RECORD_MS,complete_live);return
        if window.applied_configuration != profile or not window.record_btn.isEnabled():""")
exec(compile(source,str(Path(check.__file__)),'exec'),check.__dict__)
if __name__=='__main__':
 require_exclusive_monitor();check.main()
