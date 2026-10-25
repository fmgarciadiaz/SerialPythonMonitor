"""ABBA READY spin50/0 microseconds, strict fresh-edge handshake unchanged."""
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
    interval=board.config.get('experiment_ready_spin',50)
    optimized.send.usb_stream.stop(board)
    board.shell('docker','run','-d','--name',optimized.send.usb_stream.CONTAINER,
        '--network','host','--read-only','--cap-drop','ALL','--cap-add','SYS_NICE',
        '--env','SCOPE_EXPERIMENT_RT=1','--env',f'SCOPE_READY_SPIN_US={interval}',
        '--security-opt','no-new-privileges','--user','0:0',
        '--device','/dev/spidev0.0:/dev/spidev0.0:rw',
        '--device','/dev/gpiochip1:/dev/gpiochip1:rw',
        '--mount',f'type=bind,src={target},dst=/work/unoq_stream,readonly',
        '--entrypoint','/work/unoq_stream',IMAGE)
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        log=board.run('shell','docker logs '+optimized.send.usb_stream.CONTAINER+' 2>&1',capture=True).stdout
        if ('SPI ready: first verified frame' in log and 'SCHED_FIFO priority 10' in log
            and f'READY spin active={interval} us; fresh edge required' in log):return
        time.sleep(.2)
    raise RuntimeError('Relay did not confirm interval, scheduler and first frame')


optimized.send.sweep_module.start_relay=start_relay
optimized.send.probe_module.start_relay=start_relay


class ReadySleepProbe(PingProbe):
    def __init__(self):
        super().__init__()
        cfg=dict(self.candidate.config)
        cfg.update(local_app='experimentos/adc8_ready_sleep_v17/arduino/historico/v16/oscilloscope',
                   experiment_ready_spin=50)
        self.candidate=Board(cfg)
        self.report.update(revision='adc8_ready_sleep_abba_v17',variants={},
            relay_spin_us={'A':50,'B':0},policy_checks=[],
            mcu='Reference PING, corrected WORD DMA; identical for A and B',
            instrumentation='Only existing MCU prepare/check fields; no per-syscall profiler',
            plan=dict(order=['A','B','B','A'],ticks=[114,112],node_pairs=3456,seconds=30,
                      extra_readers_per_block=3,qualification_seconds=[60,120,120,120]))

    def trial(self,*args,**kwargs):
        row=super().trial(*args,**kwargs)
        row['ready_spin_us']=self.candidate.config['experiment_ready_spin']
        self.logs(f"case_{len(self.report['cases'])-1:02d}_relay.log")
        self.save()
        return row

    def load(self,variant):
        self.variant=variant
        self.candidate.config['experiment_ready_spin']=self.report['relay_spin_us'][variant]
        self.fast_reset()

    def policy_probe(self,block):
        result=dict(block=block,variant=self.variant,attempts=[],ok=False)
        self.report['policy_checks'].append(result)
        self.save()
        with Connection(self.stable.serial) as connection:
            session=Session(connection)
            started=time.monotonic()
            while not session.decoder.pairs and time.monotonic()-started<2:session.pump()
            if not session.decoder.pairs:raise RuntimeError('No primary-reader admission')
            result['primary_first_sample_ms']=(time.monotonic()-started)*1000
            session.generator(GeneratorConfig(enabled=0))
            session.configure(8,114,3456)
            for attempt in range(3):
                before=session.decoder.pairs
                started=time.monotonic()
                with socket.socket() as extra:
                    extra.setblocking(False)
                    error=extra.connect_ex(('127.0.0.1',connection.local_port))
                    if error not in (0,errno.EINPROGRESS,errno.EWOULDBLOCK):
                        raise RuntimeError(f'Extra-reader connect_ex:{error}')
                    connected=error==0
                    rejected=False
                    while time.monotonic()-started<1:
                        session.pump()  # Primary owner must keep draining during the probe.
                        if not connected:
                            if not select.select([],[extra],[],0)[1]:continue
                            error=extra.getsockopt(socket.SOL_SOCKET,socket.SO_ERROR)
                            if error:raise RuntimeError(f'Extra-reader connection:{error}')
                            connected=True
                        try:
                            data=extra.recv(992)
                            if data:raise RuntimeError('Extra reader received acquisition data')
                            rejected=True
                            break
                        except (BlockingIOError,InterruptedError):pass
                        except ConnectionResetError:
                            rejected=True
                            break
                    if not rejected:raise RuntimeError('Extra reader was not rejected within1s')
                    rejected_at=time.monotonic()
                end=time.monotonic()+.03
                while time.monotonic()<end:session.pump()
                count=session.decoder.pairs-before
                if count<=0:raise RuntimeError('Primary reader did not continue')
                result['attempts'].append(dict(rejected=True,data_received=0,
                    observed_reject_ms=(rejected_at-started)*1000,
                    primary_samples=count))
                self.save()
            # An ordinary configuration ACK must still complete for the owner.
            session.configure(8,112,3456)
            before=session.decoder.pairs
            deadline=time.monotonic()+.1
            while time.monotonic()<deadline:session.pump()
            if session.decoder.pairs<=before:raise RuntimeError('No primary data after configuration ACK')
            result['post_probe_applied']=list(session.decoder.profile)
        result['ok']=True
        self.logs(f'policy_{block:02d}_relay.log')
        self.save()

    def run_probe(self):
        self.save()
        try:
            self.prepare()
            self.report['variants']={k:self.report['candidate_source_hashes'] for k in ('A','B')}
            self.candidate.start()
            start_relay(self.candidate,self.deployment['candidate_relay'])
            for block,variant in enumerate(('A','B','B','A')):
                if block:self.load(variant)
                for index,ticks in enumerate((114,112)):
                    row=self.trial(8,ticks,3456,30,'abba',restart=index>0)
                    row['abba_block']=block
                    self.save()
                    if not row['ok']:raise RuntimeError('ABBA integrity failure')
                self.policy_probe(block)
            self.report['policy_ok']=all(r['ok'] for r in self.report['policy_checks'])
            if self.gate() and self.report['policy_ok']:
                self.load('B')
                self.report['winners']['8']=self.qualify(8,112,3456)
            self.report['ok']=True
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
    raise SystemExit(ReadySleepProbe().run_probe())
