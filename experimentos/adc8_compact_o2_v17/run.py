"""Compact ADC8 high-rate format experiment."""
import errno
import hashlib
import struct
import numpy as np
import json
from pathlib import Path
import signal
import select
import socket
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from experimentos.adc8_ping_word_v17.run import PingProbe,optimized,TimingDecoder
import experimentos.maxfreq_v16.contract as original_contract
from experimentos.adc8_compact_o2_v17.contract import Decoder as CompactDecoder
from experimentos.maxfreq_v16.contract import Session
from monitor.v16.receiver.unoq_usb import Connection
from monitor.v16.receiver.unoq_generator import GeneratorConfig
from tools.unoq import Board
from spi_benchmark import IMAGE

EXP=Path(__file__).resolve().parent
optimized.EXP=EXP
optimized.send.EXP=EXP


class CompactTimingDecoder(CompactDecoder):
    def __init__(self):
        super().__init__()
        self.timing_buffer=bytearray();self.reset_timing();TimingDecoder.latest=self
    reset_timing=TimingDecoder.reset_timing
    summary=TimingDecoder.summary
    def reset_metrics(self):
        super().reset_metrics();self.reset_timing()
    def feed(self,data):
        self.timing_buffer.extend(data)
        while len(self.timing_buffer)>=992:
            p=bytes(self.timing_buffer[:992]);del self.timing_buffer[:992]
            super().feed(p)
            kind=struct.unpack_from('<H',p,6)[0]
            if kind in (20,21):
                prepare,check=struct.unpack_from('<II',p,52 if kind==21 else 40)
                self.prepare_us.append(prepare);self.check_us.append(check)

original_contract.Decoder=CompactTimingDecoder

def start_relay(board,target):
    return optimized.send.start_experimental_relay(board,target)



class CompactProbe(PingProbe):
    def __init__(self):
        (EXP/'arduino/v16/oscilloscope/sketch/compact_variant.h').write_text('#pragma once\n#define SCOPE_COMPACT_ADC8 0\n')
        super().__init__()
        cfg=dict(self.candidate.config)
        cfg.update(local_app='experimentos/adc8_compact_o2_v17/arduino/v16/oscilloscope',
                   experiment_compact=True)
        self.candidate=Board(cfg)
        self.report['runner_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self.report['gate']='2% improvement in send time per sample, B headroom and no overlap at both rates'
        self.report.update(revision='adc8_compact_abba_v17',variants={},
            nodes={'A':3456,'B':3632},payload_samples={'A':864,'B':908},policy_checks=[],
            mcu='WORD reference; A kind20/864, B experimental high-rate ADC8 kind21/908',
            instrumentation='Only existing MCU prepare/check fields; no per-syscall profiler',
            plan=dict(order=['A','B','B','A'],ticks=[114,112],node_pairs={'A':3456,'B':3632},seconds=30,
                      extra_readers_per_block=3,qualification_seconds=[60,120,120,120]))

    def trial(self,*args,**kwargs):
        row=super().trial(*args,**kwargs)
        row['payload_capacity']=self.report['payload_samples'][self.variant]
        self.logs(f"case_{len(self.report['cases'])-1:02d}_relay.log")
        self.save()
        return row

    def load(self,variant):
        optimized.send.usb_stream.stop(self.candidate)
        self.candidate.stop()
        (EXP/'arduino/v16/oscilloscope/sketch/compact_variant.h').write_text(
            '#pragma once\n#define SCOPE_COMPACT_ADC8 '+('1' if variant=='B' else '0')+'\n')
        files=self.candidate.check_sources()
        self.candidate.push_sources(files,self.candidate.remote)
        self.report['variants'][variant]={p.relative_to(self.candidate.local).as_posix():
            hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        self.variant=variant;self.save()
        self.candidate.start()
        start_relay(self.candidate,self.deployment['candidate_relay'])
        self.dirty=False

    def gate(self):
        decisions=[]
        for ticks in (114,112):
            rows=[c for c in self.report['cases'] if c['stage']=='abba' and c['ticks']==ticks]
            a=[r for r in rows if r['variant']=='A'];b=[r for r in rows if r['variant']=='B']
            av=[r['metrics']['send_mean_us']/r['node_pairs'] for r in a]
            bv=[r['metrics']['send_mean_us']/r['node_pairs'] for r in b]
            valid=len(a)==len(b)==2 and all(r['ok'] for r in rows)
            gain=1-float(np.mean(bv))/float(np.mean(av)) if valid else 0
            decisions.append(dict(ticks=ticks,a_send_us_per_sample=av,b_send_us_per_sample=bv,
                relative_gain=gain,passes=valid and gain>=.02 and max(bv)<min(av) and
                all(r.get('headroom_ok',False) for r in b)))
        self.report['abba_decisions']=decisions;self.save()
        return all(d['passes'] for d in decisions)

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
            session.configure(8,114,self.report['nodes'][self.variant])
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
            session.configure(8,112,self.report['nodes'][self.variant])
            before=session.decoder.pairs
            deadline=time.monotonic()+.1
            while time.monotonic()<deadline:session.pump()
            if session.decoder.pairs<=before:raise RuntimeError('No primary data after configuration ACK')
            result['post_probe_applied']=list(session.decoder.profile)
            session.configure(8,640,self.report['nodes'][self.variant])
            before=session.decoder.pairs
            end=time.monotonic()+.1
            while time.monotonic()<end:session.pump()
            result['low_rate_legacy_samples']=session.decoder.pairs-before
            if result['low_rate_legacy_samples']<=0:raise RuntimeError('No low-rate legacy data')
            session.configure(8,112,self.report['nodes'][self.variant])

        result['ok']=True
        self.logs(f'policy_{block:02d}_relay.log')
        self.save()

    def run_probe(self):
        self.save()
        try:
            self.prepare()
            self.report['variants']={'A':self.report['candidate_source_hashes']}
            self.report['changes']=['Experimental kind21 ADC8 high-rate header80/payload908','ADC8 nodes3456/3632 aligned to four frames','Retain kind20 for all other formats and low rates','SPI clock, WORD DMA, fresh READY and TCP per-frame unchanged']
            self.candidate.start()
            start_relay(self.candidate,self.deployment['candidate_relay'])
            for block,variant in enumerate(('A','B','B','A')):
                if block:self.load(variant)
                for index,ticks in enumerate((114,112)):
                    row=self.trial(8,ticks,self.report['nodes'][variant],30,'abba',restart=index>0)
                    row['abba_block']=block
                    self.save()
                    if not row['ok']:raise RuntimeError('ABBA integrity failure')
                self.policy_probe(block)
            self.report['policy_ok']=all(r['ok'] for r in self.report['policy_checks'])
            if self.gate() and self.report['policy_ok']:
                self.load('B')
                self.report['winners']['8']=self.qualify(8,112,3632)
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
    raise SystemExit(CompactProbe().run_probe())
