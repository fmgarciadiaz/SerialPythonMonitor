"""Render identical V18/PySide demos in separate processes, without Q access."""
import argparse,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def capture(variant,folder,cases=()):
    # Reuse the same deterministic demo definitions and widget interactions.
    # Redirect every asset/archive write into the comparison folder.
    source=ROOT/'tools/capture_landing_v18.py'
    code=source.read_text().replace("assets=ROOT/'assets';archive=assets/'historico/antes_v18_20261026'",
        "assets=Path(os.environ['ARDUSCOPIO_COMPARISON_OUTPUT']);archive=assets/'archive'")
    if variant=='v19':
        code=code.replace('monitor.v18','monitor.v19').replace('from PyQt6','from PySide6')
        code=code.replace('ptr=image.bits();ptr.setsize(image.sizeInBytes())','ptr=image.bits()')
    code=code.replace('d.last_fast_render=0;w.render_frame()',
                      'd.last_fast_render=0;w._roll_position=None;w.render_frame()')
    # Freeze the roll endpoint too. A perf_counter-based fractional sample made
    # temporal traces differ between otherwise identical capture processes.
    code=code.replace('visual_end = self._roll_end_position(total_samples, time.perf_counter())',
                      'visual_end = float(total_samples)')
    output=folder/variant
    output.mkdir(parents=True,exist_ok=True)
    os.environ['ARDUSCOPIO_COMPARISON_OUTPUT']=str(output)
    sys.argv=[str(source),*cases]
    exec(compile(code,str(source),'exec'),{'__name__':'__main__','__file__':str(source)})

def compare(folder):
    import numpy as np
    from PIL import Image
    rows=[]
    for baseline in sorted((folder/'v18').glob('monitor_*.png')):
        candidate=folder/'v19'/baseline.name
        a=np.asarray(Image.open(baseline).convert('RGB'),dtype=np.uint8)
        b=np.asarray(Image.open(candidate).convert('RGB'),dtype=np.uint8)
        if a.shape!=b.shape:
            rows.append(dict(name=baseline.stem,ok=False,baseline_shape=a.shape,candidate_shape=b.shape));continue
        # Live FPS text is timing-dependent; ignore only its small title region.
        mask=np.ones(a.shape[:2],dtype=bool)
        if baseline.stem in ('monitor_vt','monitor_generator','monitor_wav','monitor_synth'):
            mask[int(a.shape[0]*.17):int(a.shape[0]*.21),int(a.shape[1]*.18):int(a.shape[1]*.81)]=False
        delta=np.abs(a.astype(np.int16)-b.astype(np.int16))
        row=dict(name=baseline.stem,size=list(a.shape[:2]),
                 exact_pixel_equal=bool(np.array_equal(a[mask],b[mask])),
                 exact_changed_pixel_fraction=float((delta.max(axis=2)[mask]>0).mean()),
                 mean_absolute_error=float(delta[mask].mean()),
                 changed_pixel_fraction=float((delta.max(axis=2)[mask]>20).mean()))
        row['ok']=row['changed_pixel_fraction']<.01 and row['mean_absolute_error']<1.
        diff=np.minimum(delta*4,255).astype('uint8')
        Image.fromarray(diff).save(folder/(baseline.stem+'_difference.png'))
        rows.append(row)
    report=dict(ok=bool(rows) and all(row['ok'] for row in rows),
                all_exact_pixels_equal=bool(rows) and all(row.get('exact_pixel_equal',False) for row in rows),
                physical=False,cases=rows,
                note='Deterministic offline GUI demos; timing-dependent title region excluded')
    (folder/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',choices=('v18','v19'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cases',nargs='*',default=[])
    args=parser.parse_args();folder=args.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    if args.capture:capture(args.capture,folder,args.cases)
    else:compare(folder)

if __name__=='__main__':main()
