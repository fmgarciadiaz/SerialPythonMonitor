"""Sequential installed-pair V19 checks; no firmware deployment."""
import argparse,json,subprocess,sys,time,signal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CASES=[
 ('v19_8_long','v19',8,86,120,710,65536,False),
 ('v19_10_us','v19',10,118,25,400,16384,True),
 ('v19_12','v19',12,145,20,400,16384,False),
 ('v19_14','v19',14,160,20,400,16384,False),
 ('v19_16_single','v19',16,1060,20,30,16384,False),
 ('v19_16_dual','v19',16,2099,20,20,16384,False),
 ('v19_8_dual','v19',8,253,20,250,16384,False),
]


def run_case(command,log,timeout):
    process=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    try:process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        # The wrapper owns restoration. Request cancellation and let its
        # finally block run; subprocess.run(timeout=...) would kill it.
        process.send_signal(signal.SIGTERM)
        try:process.wait(timeout=90)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('El dueño del Q sigue activo; matriz detenida sin matarlo') from exc
        return process.returncode or 1
    return process.returncode

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true')
    p.add_argument('--baseline-python',help=argparse.SUPPRESS) # accepted for old invocations; V19 uses current Python
    p.add_argument('--serial',required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if not args.run:print(json.dumps(CASES,indent=2));return 0
    args.output.mkdir(parents=True,exist_ok=True)
    report=dict(ok=False,firmware_deployment=False,cases=[])
    def save():(args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    for name,version,bits,ticks,hold,frequency,fft,us in CASES:
        command=[sys.executable,str(ROOT/'tools/probe_radio_rate_v19.py'),'--serial',args.serial,
                 '--bits',str(bits),'--ticks',str(ticks),'--hold',str(hold),
                 '--frequency-khz',str(frequency),'--fft-size',str(fft),'--crop-radios']
        if us:command+=['--us']
        print('START',name,flush=True)
        try:
            with (args.output/(name+'.log')).open('w') as log:
                exit_code=run_case(command,log,hold+180)
        except Exception as exc:
            report['cases'].append(dict(name=name,ok=False,error=str(exc)));save();return 1
        text=(args.output/(name+'.log')).read_text()
        folder=next((Path(line) for line in text.splitlines() if line.startswith(str(ROOT/'diagnosticos'))),None)
        result=json.loads((folder/'report.json').read_text()) if folder is not None else {}
        row=dict(name=name,version=version,bits=bits,ticks=ticks,hold=hold,evidence=str(folder),
                 exit_code=exit_code,ok=exit_code==0 and result.get('ok') is True,
                 visible=result.get('visible_gui_ok'),restored=result.get('restoration',{}).get('hardware_restored'))
        report['cases'].append(row);save();print('RESULT',json.dumps(row),flush=True)
        if not row['ok']:return 1
    report['ok']=True;save();return 0

if __name__=='__main__':raise SystemExit(main())
