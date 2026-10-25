"""Isolated SPI40 pilot, short physical evidence only; no electrical qualification."""
import errno
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


class ClockPilot(PingProbe):
    def __init__(self):
        super().__init__()
        cfg=dict(self.candidate.config)
        cfg.update(local_app='experimentos/adc8_spi40_pilot_v17/arduino/historico/v16/oscilloscope',
                   experiment_spi_hz=38000000)
        self.candidate=Board(cfg)
        self.report.update(revision='adc8_spi40_pilot_abba_v17',variants={},
            relay_spi_hz={'A':38000000,'B':40000000},policy_checks=[],
            mcu='Reference PING, corrected WORD DMA; identical for A and B',
            instrumentation='Only existing MCU prepare/check fields; no per-syscall profiler',
            plan=dict(matrix=[['A',640,10],['A',114,10],['B',640,10],['B',114,30],['B',112,30],['B',110,10]],
                      node_pairs=3456,stop_on_integrity_failure=True,electrical_acceptance=False))

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

    def run_probe(self):
        self.save()
        try:
            self.stable.run('push',str(EXP/'read_config.py'),'/tmp/serialmonitor-spi-read-config.py')
            self.report['initial_configuration']=self.configuration('initial_configuration.json')
            self.prepare()
            self.candidate.start()
            start_relay(self.candidate,self.deployment['candidate_relay'])
            matrix=[('A',640,10),('A',114,10),('B',640,10),('B',114,30),('B',112,30),('B',110,10)]
            for index,(variant,ticks,seconds) in enumerate(matrix):
                if index:self.load(variant)
                row=self.trial(8,ticks,3456,seconds,'clock_pilot')
                row['configuration']=self.configuration(f'case_{index:02d}_configuration.json')
                expected=40000000 if variant=='B' else 100000000/3
                row['clock_matches']=abs(row['configuration']['configured_hz']-expected)<1
                self.save()
                if not row['clock_matches']:raise RuntimeError('Requested clock did not configure as expected')
                if not row['ok']:
                    self.report['stopped_at_integrity_failure']=dict(variant=variant,ticks=ticks)
                    break
            self.report['pilot_integrity_ok']=all(c['ok'] for c in self.report['cases'])
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
    raise SystemExit(ClockPilot().run_probe())
