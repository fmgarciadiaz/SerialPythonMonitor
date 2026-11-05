#!/usr/bin/env python3
"""Offline renderer profile using the real Synth panel defaults. Never opens Q."""
import argparse,cProfile,hashlib,json,os,statistics,sys,time
from collections import defaultdict
from dataclasses import asdict,replace
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'diagnosticos/resultados_v20'):parser.error('New V20 diagnostic directory required')
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from PySide6 import QtWidgets
    from monitor.v20.fm_panel import FMPanel
    from monitor.v20.fm_source import FMSource
    from tools.synth_transition_scenario_v20 import synth_probe_parameters
    app=QtWidgets.QApplication([]);panel_widget=QtWidgets.QWidget();QtWidgets.QGridLayout(panel_widget)
    owner=SimpleNamespace(generator_panel=panel_widget,generator_mode=QtWidgets.QComboBox(),serial_worker=None,generator_status=QtWidgets.QLabel())
    panel=FMPanel(owner);output.mkdir(parents=True)
    rows=[]
    for rate in (20000,40000):
        panel.output_rate.setCurrentIndex(panel.output_rate.findData(rate))
        params=replace(panel.parameters(1),notes=tuple((n,100) for n in range(48,68)))
        for name,p in (('DX Piano',params),('FM basic',synth_probe_parameters(params,20,'sustained-fm'))):
            source=FMSource(rate,p);priming=max(1,int(.2*rate/480))
            for i in range(priming):source.render_dac_codes(i*480,(i+1)*480,.5,1.65)
            stages=defaultdict(list)
            def trace(stage,start,end,**kwargs):stages[stage].append((end-start)*1000)
            source.audio_trace=trace;times=[];cpu=[];voices=[];blocks=int(2*rate/480)
            for i in range(priming,priming+blocks):
                start=time.perf_counter();thread=time.thread_time()
                source.render_dac_codes(i*480,(i+1)*480,.5,1.65)
                cpu.append((time.thread_time()-thread)*1000);times.append((time.perf_counter()-start)*1000);voices.append(len(source.voices))
            row=dict(preset=name,rate=rate,budget_ms=480/rate*1000,blocks=blocks,
                     mean_ms=statistics.mean(times),median_ms=statistics.median(times),max_ms=max(times),
                     mean_thread_cpu_ms=statistics.mean(cpu),voice_min=min(voices),voice_max=max(voices),
                     stages={k:dict(mean_ms=statistics.mean(v),max_ms=max(v)) for k,v in stages.items()},parameters=asdict(p))
            rows.append(row)
            # Separate replay: profiler overhead is not included in the wall benchmark.
            replay=FMSource(rate,p)
            prof=cProfile.Profile();prof.enable()
            for i in range(priming+blocks):replay.render_dac_codes(i*480,(i+1)*480,.5,1.65)
            prof.disable();prof.dump_stats(str(output/f'{rate}_{name.replace(" ","_")}.pstats'))
    paths=(ROOT/'monitor/v20/fm_source.py',ROOT/'monitor/v20/fm_panel.py',Path(__file__))
    report=dict(private=True,promoted=False,scope='Local renderer only, excludes process IPC/Q; no realtime acceptance',cases=rows,
                sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ('preset','rate','budget_ms','mean_ms','max_ms','voice_min','voice_max','stages')} for r in rows]))
    panel.close();app.quit()

if __name__=='__main__':main()
