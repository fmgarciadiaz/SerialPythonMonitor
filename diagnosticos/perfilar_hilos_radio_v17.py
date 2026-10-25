"""Sample only the owned RADIO diagnostic process; never contact Q."""
import argparse
import json
from pathlib import Path
import subprocess
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('--eager-symbols',action='store_true')
    args=parser.parse_args()
    command=subprocess.check_output(['ps','-p',str(args.pid),'-o','command='],text=True)
    if 'diagnosticos/validar_generador_radio_v17.py' not in command or '--retune-stress' not in command:
        raise ValueError('PID does not identify the intended RADIO stress diagnostic')
    folder=Path(__file__).resolve().parent/'resultados_v17'/('radio_host_sample_'+time.strftime('%Y%m%d_%H%M%S'))
    folder.mkdir()
    report=dict(pid=args.pid,target_command=command.strip(),duration_seconds=45,interval_ms=20,
                eager_symbols=args.eager_symbols,
                started_monotonic=time.monotonic(),started_wall=time.time(),
                limitation='External native sampling can perturb scheduling; diagnostic evidence, not acceptance.')
    target=folder/'report.json'
    target.write_text(json.dumps(report,indent=2)+'\n')
    try:
        sample_command=['/usr/bin/sample',str(args.pid),'45','20']
        if args.eager_symbols:sample_command+=['-mayDie']
        sample_command+=['-fullPaths','-file',str(folder/'stacks.txt')]
        result=subprocess.run(sample_command,capture_output=True,text=True,timeout=90)
        report.update(exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr)
    except BaseException as exc:
        report['error']=repr(exc)
        raise
    finally:
        report.update(ended_monotonic=time.monotonic(),ended_wall=time.time())
        target.write_text(json.dumps(report,indent=2)+'\n')
        print('PROFILE',target,flush=True)


if __name__=='__main__':main()
