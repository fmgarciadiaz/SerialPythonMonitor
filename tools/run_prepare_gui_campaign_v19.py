#!/usr/bin/env python3
"""Private O2 GUI qualification: 60 s + three independent 120 s runs."""
import argparse,json,signal,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True);parser.add_argument('--build-report',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();root=args.output.resolve()
    if root.exists() or not root.is_relative_to(ROOT/'diagnosticos/resultados_v19'):
        parser.error('New diagnostic directory required')
    root.mkdir(parents=True);report=dict(private=True,promoted=False,ok=False,cases=[])
    def save():(root/'campaign.json').write_text(json.dumps(report,indent=2)+'\n')
    child=None
    def cancel(*_):
        report['cancelled']=True;save()
        if child is not None and child.poll() is None:
            child.send_signal(signal.SIGINT)
            try:child.wait(timeout=120)
            except subprocess.TimeoutExpired:
                report['owner_still_active']=True;save()
        raise KeyboardInterrupt('Campaign cancelled; child restoration requested')
    previous={sig:signal.signal(sig,cancel) for sig in (signal.SIGINT,signal.SIGTERM)}
    try:
        for index,hold in enumerate((60,120,120,120),1):
            output=root/f'run_{index}_{hold}s'
            row=dict(index=index,hold=hold,output=str(output),state='running');report['cases'].append(row);save()
            print(f'Case {index}: {hold}s, backup/load/GUI/restore',flush=True)
            cmd=[sys.executable,str(ROOT/'tools/probe_prepare_gui_v19.py'),'--serial',args.serial,
                 '--build-report',str(args.build_report.resolve()),'--output',str(output),'--hold',str(hold)]
            with (root/f'run_{index}.log').open('w') as log:
                child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
                row['pid']=child.pid;save();code=child.wait()
            detail=json.loads((output/'report.json').read_text()) if (output/'report.json').exists() else {}
            gui=detail.get('gui',{})
            row.update(state='complete',returncode=code,ok=code==0 and detail.get('ok') is True,
                       restored=detail.get('restoration',{}).get('ok') is True,
                       visible=gui.get('visible_gui_ok') is True,headroom=gui.get('headroom_pass') is True)
            row['pass']=all(row[k] for k in ('ok','restored','visible','headroom'));save()
            print(json.dumps(row),flush=True)
            if not row['pass']:return 1
        report['ok']=True;save();return 0
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)
        save()

if __name__=='__main__':raise SystemExit(main())
