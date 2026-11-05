"""Private exact-output experiment; does not edit the product module or operate Q."""
import difflib,hashlib,importlib.util,json,os,statistics,sys,time,types
from dataclasses import asdict,replace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
HELPER='''@lru_cache(maxsize=256)
def _dx_note_values(carrier):
    # Immutable note coefficients; never cache phase, envelopes or audio.
    brightness=np.clip((440/max(carrier,.1))**.2,.65,1.35)
    low_depth=min(1.0,max(0.0,np.log2(220/max(carrier,.1))/2))
    return brightness,low_depth


'''
def candidate(text):
    changes={
      '@dataclass(frozen=True)':HELPER+'@dataclass(frozen=True)',
      "np.clip((440/max(parameters.carrier,.1))**.2,.65,1.35) if self.previous.carrier==parameters.carrier":"_dx_note_values(parameters.carrier)[0] if self.previous.carrier==parameters.carrier",
      "min(1.0,max(0.0,np.log2(220/max(parameters.carrier,.1))/2))":"_dx_note_values(parameters.carrier)[1]",
    }
    # Apply call sites before inserting helper, so its reference formula is untouched.
    for old,new in reversed(tuple(changes.items())):
        expected=2 if old.startswith('min(1.0') else 1
        if text.count(old)!=expected:raise RuntimeError('Source anchor changed: '+old)
        text=text.replace(old,new)
    return text

def load(text):
    name='monitor.v20._dx_cache_candidate';module=types.ModuleType(name)
    module.__file__=str(ROOT/'monitor/v20/fm_source.py');sys.modules[name]=module
    exec(compile(text,module.__file__,'exec'),module.__dict__)
    return module

def main():
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from PySide6 import QtWidgets
    from monitor.v20.fm_panel import FMPanel
    from monitor.v20 import fm_source as original
    import numpy as np
    app=QtWidgets.QApplication([]);box=QtWidgets.QWidget();QtWidgets.QGridLayout(box)
    owner=types.SimpleNamespace(generator_panel=box,generator_mode=QtWidgets.QComboBox(),serial_worker=None,generator_status=QtWidgets.QLabel())
    panel=FMPanel(owner);panel.output_rate.setCurrentIndex(panel.output_rate.findData(40000))
    p=replace(panel.parameters(1),notes=tuple((n,100) for n in range(48,68)))
    path=ROOT/'monitor/v20/fm_source.py';before=path.read_text();after=candidate(before);optimized=load(after)
    equality=[]
    # Covers finite note coefficients, changing carrier ramps, releases and note changes.
    for rate in (20000,40000):
        a=original.FMSource(rate,p);b=optimized.FMSource(rate,p)
        for i in range(140):
            if i==50:
                params=replace(p,notes=tuple((n,95) for n in range(49,69)),note_id=1)
                a.update(params);b.update(params)
            if i==100:
                params=replace(p,notes=(),note_id=2)
                a.update(params);b.update(params)
            x=a._render(slice(i*480,(i+1)*480),quantize=False)
            y=b._render(slice(i*480,(i+1)*480),quantize=False)
            if not np.array_equal(x,y):raise AssertionError(f'Audio differs: {rate}/{i}')
            if set(a.voices)!=set(b.voices):raise AssertionError('Voice allocation differs')
        equality.append(dict(rate=rate,blocks=140,float_audio_exact=True))
    timings={key:[] for key in ('baseline','candidate')}
    for repetition in range(6):
        order=(('baseline',original),('candidate',optimized))
        if repetition%2:order=tuple(reversed(order))
        for key,module in order:
            source=module.FMSource(40000,p)
            for i in range(16):source.render_dac_codes(i*480,(i+1)*480,.5,1.65)
            began=time.perf_counter()
            for i in range(16,116):source.render_dac_codes(i*480,(i+1)*480,.5,1.65)
            timings[key].append((time.perf_counter()-began)*10)
    medians={key:statistics.median(values) for key,values in timings.items()}
    out=ROOT/'diagnosticos/resultados_v20/dx_note_cache_candidate_20261102';out.mkdir(exist_ok=False)
    (out/'candidate.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='fm_source.py',tofile='fm_source.py')))
    result=dict(private=True,promoted=False,product_changed=False,source_sha256=hashlib.sha256(before.encode()).hexdigest(),candidate_sha256=hashlib.sha256(after.encode()).hexdigest(),
                float_audio_equality=equality,mean_block_ms_by_run=timings,median_block_ms=medians,
                local_speedup_fraction=1-medians['candidate']/medians['baseline'],cache_info=str(optimized._dx_note_values.cache_info()),
                note='Local in-process A/B, six alternating repetitions. Excludes IPC/Q. No physical acceptance.')
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    panel.close();app.quit()
if __name__=='__main__':main()
