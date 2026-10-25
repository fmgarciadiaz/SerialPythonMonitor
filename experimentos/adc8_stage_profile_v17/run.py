"""Diagnostic stage timings; no rate qualification or production changes."""
import json
from pathlib import Path
import signal
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
import experimentos.maxfreq_optimized_v17.run as optimized
import experimentos.maxfreq_v16.contract as contract
from experimentos.adc8_stage_profile_v17.decoder import ProfileDecoder
from tools.unoq import Board

EXP=Path(__file__).resolve().parent
optimized.EXP=EXP
optimized.send.EXP=EXP
contract.Decoder=ProfileDecoder
RELAY_NAMES=('ping_build','ready_wait','spi_ioctl','validate','host_io','loop_total')


def relay_summary(log):
    groups={}
    for line in log.splitlines():
        if line.startswith('PROFILE_RELAY '):
            row=json.loads(line[len('PROFILE_RELAY '):])
            groups.setdefault((row['start_s'],row['end_s']),{})[row['stage']]=row
    # Drop startup window. Each case has a fresh process. Use up to the last
    # two complete ten-second windows; these are not exactly the host interval.
    windows=[v for k,v in sorted(groups.items()) if len(v)==6][1:][-2:]
    result={}
    for index,name in enumerate(RELAY_NAMES):
        rows=[w[index] for w in windows]
        count=sum(r['count'] for r in rows)
        if count:
            total=sum(r['sum_ns'] for r in rows)
            result[name]=dict(count=count,sum_ns=total,mean_us=total/count/1000,
                maximum_us=max(r['max_ns'] for r in rows)/1000,
                windows=[dict(start_s=r['start_s'],end_s=r['end_s']) for r in rows])
    return result


class StageProfile(optimized.OptimizedSweep):
    def __init__(self,control):
        super().__init__()
        config=dict(self.candidate.config)
        config['local_app']='experimentos/adc8_stage_profile_v17/arduino/historico/v16/oscilloscope'
        self.candidate=Board(config)
        self.control=control
        self.report.update(revision='adc8_stage_profile_v17',instrumentation=not control,
            plan={'ticks':[114] if control else [114,112,114], 'node_pairs':3456,
                  'seconds':30,'rate_qualification':False},
            production_sources_modified=False,
            timing_caveats=['Elapsed inclusive times, not exclusive CPU costs',
                           'Build includes packing; MCU and relay intervals overlap',
                           'MCU max since boot; mean from coherent cumulative snapshots',
                           'Relay means cover complete logged windows, excluding startup',
                           'Instrumented throughput is not production acceptance'])

    def run_probe(self):
        self.save()
        try:
            self.prepare()
            self.candidate.start()
            optimized.send.start_experimental_relay(self.candidate,self.deployment['candidate_relay'])
            ticks_list=[114] if self.control else [114,112,114]
            for index,ticks in enumerate(ticks_list):
                row=self.trial(8,ticks,3456,30,'control' if self.control else 'profile',restart=index>0)
                if ProfileDecoder.latest is not None:
                    row['mcu_stages']=ProfileDecoder.latest.summary()
                log=self.logs(f'case_{index:02d}_relay.log') or ''
                row['relay_stages']=relay_summary(log)
                self.save()
                if not row['ok']:break
                if not self.control and (len(row['mcu_stages'])!=11 or len(row['relay_stages'])!=6):
                    raise RuntimeError('Incomplete stage timing evidence')
            self.report['ok']=len(self.report['cases'])==len(ticks_list) and all(r['ok'] for r in self.report['cases'])
        except BaseException as exc:
            self.report['error']=str(exc) or type(exc).__name__
            print('EXPERIMENT ERROR',repr(exc),flush=True)
        finally:
            if self.switched:
                try:self.restore()
                except BaseException as exc:self.report['restore_error']=str(exc)
            else:self.report['restored']=True
            self.save()
        print('REPORT',self.folder/'report.json','OK',self.report['ok'],
              'RESTORED',self.report['restored'],flush=True)
        return 0 if self.report['ok'] and self.report['restored'] else 1


def interrupted(signum,frame):raise KeyboardInterrupt(f'signal {signum}')


if __name__=='__main__':
    signal.signal(signal.SIGINT,interrupted)
    signal.signal(signal.SIGTERM,interrupted)
    control='--control' in sys.argv
    for folder in ('oscilloscope/sketch','relay'):
        (EXP/'arduino/historico/v16'/folder/'profile_config.h').write_text(
            '#pragma once\n#define SCOPE_STAGE_PROFILE '+('0' if control else '1')+'\n')
    raise SystemExit(StageProfile(control).run_probe())
