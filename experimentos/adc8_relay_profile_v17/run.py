"""Relay syscall timing only; unchanged reference WORD MCU and validation."""
import json
from pathlib import Path
import signal
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
import experimentos.maxfreq_optimized_v17.run as optimized
from tools.unoq import Board

EXP=Path(__file__).resolve().parent
optimized.EXP=EXP
optimized.send.EXP=EXP
NAMES=('ping_build','ready_wait','spi_ioctl','validate','host_io','loop_total',
       'recv','accept','send')


def summarize(log):
    groups={}
    for line in log.splitlines():
        if line.startswith('PROFILE_RELAY '):
            row=json.loads(line[len('PROFILE_RELAY '):])
            if row['stage'] not in range(len(NAMES)):raise ValueError('Unknown stage')
            groups.setdefault((row['start_s'],row['end_s']),{})[row['stage']]=row
    windows=[v for _,v in sorted(groups.items()) if len(v)==len(NAMES)][1:][-2:]
    result={}
    for index,name in enumerate(NAMES):
        rows=[w[index] for w in windows]
        count=sum(r['count'] for r in rows)
        if not count:continue
        total=sum(r['sum_ns'] for r in rows)
        result[name]=dict(count=count,sum_ns=total,mean_us=total/count/1000,
            maximum_us=max(r['max_ns'] for r in rows)/1000,
            windows=[dict(start_s=r['start_s'],end_s=r['end_s']) for r in rows])
        for field in ('success','again','interrupted','errors','bytes','short_count'):
            result[name][field]=sum(r[field] for r in rows)
    return result


class RelayProfile(optimized.OptimizedSweep):
    def __init__(self):
        super().__init__()
        cfg=dict(self.candidate.config)
        cfg['local_app']='experimentos/adc8_relay_profile_v17/arduino/historico/v16/oscilloscope'
        self.candidate=Board(cfg)
        self.report.update(revision='adc8_relay_syscall_profile_v17',
            plan=dict(ticks=[114,112,112,114],node_pairs=3456,seconds=30,
                      rate_qualification=False),
            mcu_variant='Reference PING, WORD DMA, burst four bytes; no MCU stage profiler',
            production_sources_modified=False,
            caveats=['Inclusive elapsed syscall times, not exclusive CPU',
                     'host_io includes recv/accept/send plus timing overhead',
                     'Discard startup window; last two complete ten-second windows',
                     'Diagnostic only, no sustained rate/headroom acceptance'])

    def run_probe(self):
        self.save()
        try:
            self.prepare()
            self.candidate.start()
            optimized.send.start_experimental_relay(self.candidate,self.deployment['candidate_relay'])
            for index,ticks in enumerate((114,112,112,114)):
                row=self.trial(8,ticks,3456,30,'relay_profile',restart=index>0)
                log=self.logs(f'case_{index:02d}_relay.log') or ''
                row['relay_stages']=summarize(log)
                self.save()
                if not row['ok']:break
                if len(row['relay_stages'])!=len(NAMES):raise RuntimeError('Incomplete relay timing evidence')
            self.report['ok']=len(self.report['cases'])==4 and all(r['ok'] for r in self.report['cases'])
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
    signal.signal(signal.SIGTERM,interrupted)
    signal.signal(signal.SIGINT,interrupted)
    raise SystemExit(RelayProfile().run_probe())
