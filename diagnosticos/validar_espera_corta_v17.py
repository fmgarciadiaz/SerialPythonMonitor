"""Bounded sequential RADIO and A0 acceptance of private ADC1600 preparation."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def child_a0():
    from diagnosticos.medir_arranque_v17 import candidate_configure
    from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
    from diagnosticos.validar_generador_radio_v17 import main
    method,digest=candidate_configure(.5)
    sys.argv=['private_settle_a0','--bits','8','--rate','1600000','--seconds','120',
              '--audio-rate','40000','--analysis-audit','--refill-ring','--defer-diagnostics']
    with patch.object(OutputReceiver,'configure',method):
        report,folder=main()
    report.update(candidate_settle_seconds=.5,original_configure_sha256=digest)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('REPORT',folder/'report.json',flush=True)
    return bool(report['ok'] and report['restored'])

def campaign():
    folder=ROOT/'diagnosticos/resultados_v17'/('espera_corta_'+time.strftime('%Y%m%d_%H%M%S'))
    folder.mkdir()
    report=dict(ok=False,candidate_settle_seconds=.5,cases=[],
        prior_radio_evidence='diagnosticos/resultados_v17/arranque_20261020_110344.json')
    def save():(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    for mode,index in [('radio',2),('radio',3),('a0',1),('a0',2),('a0',3)]:
        print('BEGIN',mode,index,flush=True)
        before=set((ROOT/'diagnosticos/resultados_v17').glob('arranque_*.json')) if mode=='radio' else set((ROOT/'diagnosticos/resultados_v17').glob('generador_radio_*/report.json'))
        cmd=[sys.executable,str(ROOT/'diagnosticos/medir_arranque_v17.py'),'--candidate-settle','0.5','--target-seconds','120','--radio'] if mode=='radio' else [sys.executable,str(Path(__file__).resolve()),'--child-a0']
        with (folder/f'{mode}_{index}.log').open('w') as log:
            process=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,QT_QPA_PLATFORM='cocoa'))
        after=set((ROOT/'diagnosticos/resultados_v17').glob('arranque_*.json')) if mode=='radio' else set((ROOT/'diagnosticos/resultados_v17').glob('generador_radio_*/report.json'))
        created=after-before
        row=dict(mode=mode,index=index,exit_code=process.returncode,ok=False)
        if len(created)==1:
            path=created.pop();detail=json.loads(path.read_text())
            row.update(report=str(path.relative_to(ROOT)),ok=process.returncode==0 and detail.get('ok',False) and detail.get('restored',False),restored=detail.get('restored',False))
        report['cases'].append(row);save()
        print('END',mode,index,'ok',row['ok'],'restored',row.get('restored'),flush=True)
        if not row['ok']:break
    report['ok']=len(report['cases'])==5 and all(r['ok'] for r in report['cases'])
    save();print('REPORT',folder/'report.json',flush=True)
    return report['ok']

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child-a0',action='store_true')
    args=parser.parse_args()
    raise SystemExit(0 if (child_a0() if args.child_a0 else campaign()) else 1)
