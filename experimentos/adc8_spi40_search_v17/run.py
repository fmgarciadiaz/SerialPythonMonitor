"""Isolated SPI40 sustained integrity/headroom validation; no electrical qualification."""
import errno
import hashlib
import json
from pathlib import Path
import signal
import select
import socket
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from experimentos.adc8_ping_word_v17.run import PingProbe,optimized
from experimentos.maxfreq_v16.contract import Session
from monitor.historico.v16.receiver.unoq_usb import Connection
from monitor.historico.v16.receiver.unoq_generator import GeneratorConfig
from tools.unoq import Board
from spi_benchmark import IMAGE

EXP=Path(__file__).resolve().parent
optimized.EXP=EXP
optimized.send.EXP=EXP


def start_relay(board,target):
    interval=board.config.get('experiment_spi_hz',38000000)
    optimized.send.usb_stream.stop(board)
    board.shell('docker','run','-d','--name',optimized.send.usb_stream.CONTAINER,
        '--network','host','--read-only','--cap-drop','ALL','--cap-add','SYS_NICE',
        '--env','SCOPE_EXPERIMENT_RT=1','--env',f'SCOPE_SPI_HZ={interval}',
        '--security-opt','no-new-privileges','--user','0:0',
        '--device','/dev/spidev0.0:/dev/spidev0.0:rw',
        '--device','/dev/gpiochip1:/dev/gpiochip1:rw',
        '--mount',f'type=bind,src={target},dst=/work/unoq_stream,readonly',
        '--entrypoint','/work/unoq_stream',IMAGE)
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        log=board.run('shell','docker logs '+optimized.send.usb_stream.CONTAINER+' 2>&1',capture=True).stdout
        if ('SPI ready: first verified frame' in log and 'SCHED_FIFO priority 10' in log
            and f'Experimental SPI requested={interval} Hz' in log):return
        time.sleep(.2)
    raise RuntimeError('Relay did not confirm interval, scheduler and first frame')


optimized.send.sweep_module.start_relay=start_relay
optimized.send.probe_module.start_relay=start_relay


class ClockSearch(PingProbe):
    def __init__(self):
        super().__init__()
        cfg=dict(self.candidate.config)
        cfg.update(local_app='experimentos/adc8_spi40_search_v17/arduino/historico/v16/oscilloscope',
                   experiment_spi_hz=40000000)
        self.candidate=Board(cfg)
        self.report['runner_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self.report['changes']=['Only SPI requested clock38/40MHz; source/DFS verification without cache','Original kind20 payload864 and WORD DMA; no compact format or TCP batching']
        self.variant='B'
        self.screens={}
        self.qualified={}
        self.report.update(revision='adc8_spi40_search_v17',variants={},
            relay_spi_hz={'A':38000000,'B':40000000},policy_checks=[],
            mcu='Reference PING, corrected WORD DMA; identical for A and B',
            instrumentation='Only existing MCU prepare/check fields; no per-syscall profiler',
            plan=dict(reference_ticks=112,screen_start=[111,110],coarse_step=2,minimum_ticks=78,
                      screen_seconds=10,qualification_seconds=[60,120,120,120],
                      refine_first_failing_interval=True,failure_repeat_is_diagnostic_only=True,
                      node_pairs=3456,electrical_acceptance=False))

    def trial(self,*args,**kwargs):
        row=super().trial(*args,**kwargs)
        row['spi_requested_hz']=self.candidate.config['experiment_spi_hz']
        self.logs(f"case_{len(self.report['cases'])-1:02d}_relay.log")
        self.save()
        return row

    def load(self,variant):
        self.variant=variant
        self.candidate.config['experiment_spi_hz']=self.report['relay_spi_hz'][variant]
        self.fast_reset()

    def configuration(self,name):
        out=self.stable.shell('docker','run','--rm','--read-only','--network','none',
            '--cap-drop','ALL','--cap-add','SYS_RAWIO','--security-opt','no-new-privileges',
            '--user','0:0','--device','/dev/mem:/dev/mem:r',
            '--mount','type=bind,src=/tmp/serialmonitor-spi-read-config.py,dst=/reader.py,readonly',
            '--mount','type=bind,src=/sys/kernel/debug/clk/gcc_qupv3_wrap0_s5_clk_src/clk_rate,dst=/clock_rate,readonly',
            '--mount','type=bind,src=/sys/kernel/debug/clk/gcc_qupv3_wrap0_s5_clk/clk_rate,dst=/branch_rate,readonly',
            '--entrypoint','python3',IMAGE,'/reader.py',capture=True).stdout
        (self.folder/name).write_text(out)
        data=json.loads(out)
        snapshots=data['snapshots']
        if not all(x==snapshots[0] for x in snapshots):raise RuntimeError('Unstable SPI clock snapshot')
        div=(snapshots[0]['serial_clock_config']>>4)&4095
        if not div or data['source_hz_before']!=data['source_hz_after']:raise RuntimeError('Unstable source clock')
        data['configured_hz']=data['source_hz_before']/div
        data['gcc_active_level']=(data['gcc_dfs_control']>>1)&15
        if data['gcc_active_level']!=snapshots[0]['clock_select']:raise RuntimeError('GENI/GCC DFS levels disagree')
        return data

    def measure(self,ticks,seconds,stage):
        row=self.trial(8,ticks,3456,seconds,stage,restart=bool(self.report['cases']))
        row['configuration']=self.configuration(f"case_{len(self.report['cases'])-1:02d}_configuration.json")
        row['clock_matches']=abs(row['configuration']['configured_hz']-40000000)<1
        self.save()
        if not row['clock_matches']:raise RuntimeError('SPI40 configuration mismatch')
        return row

    def screen(self,ticks):
        if ticks in self.screens:return self.screens[ticks]
        row=self.measure(ticks,10,'screen')
        self.screens[ticks]=row
        if not row['ok']:
            repeated=self.measure(ticks,10,'repeat_failure')
            row['failure_repeat_ok']=repeated['ok']
            row['intermittent']=bool(repeated['ok'])
            # A passing retry never erases the original failure or makes it eligible.
            self.save()
        return row

    def qualify_profile(self,ticks):
        if ticks in self.qualified:return self.qualified[ticks]
        rows=[]
        for stage,seconds in [('finalist',60),('acceptance_1',120),('acceptance_2',120),('acceptance_3',120)]:
            row=self.measure(ticks,seconds,stage);rows.append(row)
            if not row['ok']:
                self.qualified[ticks]=None
                return None
        result=dict(bits=8,channels=1,ticks=ticks,node_pairs=3456,actual_rate=160000000/ticks,
            integrity_accepted=True,headroom_accepted=all(r.get('headroom_ok',False) for r in rows),
            qualification_seconds=[60,120,120,120],samples=sum(r['samples'] for r in rows))
        self.qualified[ticks]=result
        self.report.setdefault('qualified_profiles',[]).append(result);self.save()
        return result

    def search(self):
        self.screen(111)
        for ticks in range(110,77,-2):
            row=self.screen(ticks)
            if not row['ok']:
                self.report['first_coarse_failure_ticks']=ticks
                if ticks+1<112:self.screen(ticks+1)
                self.save();break
        candidates=sorted(t for t,r in self.screens.items() if r['ok'])
        self.report['eligible_ticks']=candidates;self.save()
        integrity=None
        for ticks in candidates:
            integrity=self.qualify_profile(ticks)
            if integrity is not None:break
        headroom=integrity if integrity and integrity['headroom_accepted'] else None
        if integrity and headroom is None:
            for ticks in candidates:
                if ticks<=integrity['ticks'] or not self.screens[ticks].get('headroom_ok',False):continue
                candidate=self.qualify_profile(ticks)
                if candidate and candidate['headroom_accepted']:
                    headroom=candidate;break
        self.report['winners']['8']=dict(best_integrity_above_reference=integrity,
                                         best_headroom_above_reference=headroom)
        self.save()

    def run_probe(self):
        self.save()
        try:
            self.stable.run('push',str(EXP/'read_config.py'),'/tmp/serialmonitor-spi-read-config.py')
            self.report['initial_configuration']=self.configuration('initial_configuration.json')
            self.prepare()
            self.candidate.start()
            start_relay(self.candidate,self.deployment['candidate_relay'])
            baseline=self.measure(112,10,'reference')
            if not baseline['ok']:raise RuntimeError('Previously qualified reference failed')
            self.search()
            self.report['ok']=True
        except BaseException as exc:
            self.report['error']=str(exc) or type(exc).__name__
            print('EXPERIMENT ERROR',repr(exc),flush=True)
        finally:
            if self.switched:
                try:
                    self.restore()
                    self.report['restored_configuration']=self.configuration('restored_configuration.json')
                except BaseException as exc:self.report['restore_error']=str(exc)
            else:self.report['restored']=True
            self.save()
        print('REPORT',self.folder/'report.json','OK',self.report['ok'],'RESTORED',self.report['restored'],flush=True)
        return 0 if self.report['ok'] and self.report['restored'] else 1


def interrupted(signum,frame):raise KeyboardInterrupt(f'signal {signum}')


if __name__=='__main__':
    signal.signal(signal.SIGTERM,interrupted)
    signal.signal(signal.SIGINT,interrupted)
    raise SystemExit(ClockSearch().run_probe())
