"""Read-only GENI clock evidence and diagnostic MCU NSS/host ioctl pairing."""
import json
from pathlib import Path
import signal
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from experimentos.adc8_relay_profile_v17.run import RelayProfile,optimized,summarize
from tools.unoq import Board
from spi_benchmark import IMAGE

EXP=Path(__file__).resolve().parent
optimized.EXP=EXP
optimized.send.EXP=EXP


def nss_summary(log,windows):
    rows={}
    for line in log.splitlines():
        if line.startswith('PROFILE_NSS '):
            row=json.loads(line[len('PROFILE_NSS '):])
            rows[(row['start_s'],row['end_s'])]=row
    chosen=[rows[(w['start_s'],w['end_s'])] for w in windows]
    count=sum(r['count'] for r in chosen)
    if not count:raise ValueError('No matching NSS/sequence evidence')
    mismatch=sum(r['mismatched'] for r in chosen)
    return dict(count=count,mismatched=mismatch,match_fraction=count/(count+mismatch),
        negative=sum(r['negative'] for r in chosen),
        nss_mean_us=sum(r['nss_ticks'] for r in chosen)/160/count,
        paired_ioctl_mean_us=sum(r['ioctl_ns'] for r in chosen)/1000/count,
        estimated_outside_mean_us=sum(r['outside_ns'] for r in chosen)/1000/count,
        nss_min_us=min(r['nss_min_ticks'] for r in chosen)/160,
        nss_max_us=max(r['nss_max_ticks'] for r in chosen)/160,
        estimated_outside_min_us=min(r['outside_min_ns'] for r in chosen)/1000,
        estimated_outside_max_us=max(r['outside_max_ns'] for r in chosen)/1000,
        windows=windows)


class ClockProbe(RelayProfile):
    def __init__(self):
        super().__init__()
        cfg=dict(self.candidate.config)
        cfg['local_app']='experimentos/adc8_spi_clock_v17/arduino/v16/oscilloscope'
        self.candidate=Board(cfg)
        self.report.update(revision='adc8_spi_clock_nss_diagnostic_v17',
            plan=dict(ticks=[114,112],node_pairs=3456,seconds=30,rate_qualification=False),
            mcu_variant='Reference WORD, additional diagnostic GPIO EXTI on existing NSS pin',
            caveats=['NSS callbacks include interrupt latency; not electrical SCK measurement',
                     'NSS sequence N paired with host ioctl N, reported by MCU in frame N+1',
                     'Estimated ioctl minus NSS includes all outside-window delays',
                     'Independent MCU/Linux clocks; nominal MCU160MHz conversion',
                     'Diagnostic interrupts/profiling perturb throughput; no rate acceptance'])

    def configuration(self,name):
        out=self.stable.shell('docker','run','--rm','--read-only','--network','none',
            '--cap-drop','ALL','--cap-add','SYS_RAWIO','--security-opt','no-new-privileges',
            '--user','0:0','--device','/dev/mem:/dev/mem:r',
            '--mount','type=bind,src=/tmp/serialmonitor-spi-read-config.py,dst=/read_config.py,readonly',
            '--mount','type=bind,src=/sys/kernel/debug/clk/gcc_qupv3_wrap0_s5_clk/clk_rate,dst=/clock_rate,readonly',
            '--entrypoint','python3',IMAGE,'/read_config.py',capture=True).stdout
        (self.folder/name).write_text(out)
        return json.loads(out)

    def run_probe(self):
        self.save()
        try:
            self.prepare()
            self.candidate.start()
            optimized.send.start_experimental_relay(self.candidate,self.deployment['candidate_relay'])
            for index,ticks in enumerate((114,112)):
                row=self.trial(8,ticks,3456,30,'nss_profile',restart=index>0)
                log=self.logs(f'case_{index:02d}_relay.log') or ''
                row['relay_stages']=summarize(log)
                self.save()
                if not row['ok']:break
                row['nss']=nss_summary(log,row['relay_stages']['spi_ioctl']['windows'])
                row['configuration']=self.configuration(f'case_{index:02d}_configuration.json')
                self.save()
                if row['nss']['match_fraction']<.95 or row['nss']['negative']/row['nss']['count']>.01:
                    raise RuntimeError('NSS capture quality insufficient')
            self.report['ok']=len(self.report['cases'])==2 and all(r['ok'] for r in self.report['cases'])
        except BaseException as exc:
            self.report['error']=str(exc) or type(exc).__name__
            print('EXPERIMENT ERROR',repr(exc),flush=True)
        finally:
            if self.switched:
                try:
                    self.restore()
                    self.report['restored_spi_configuration']=self.configuration('restored_configuration.json')
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
    raise SystemExit(ClockProbe().run_probe())
