"""Uninstrumented PING reference/word ABBA; bounded conditional qualification."""
import hashlib
import json
from pathlib import Path
import signal
import struct
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
import experimentos.maxfreq_optimized_v17.run as optimized
import experimentos.maxfreq_v16.contract as contract
from tools.unoq import Board

EXP=Path(__file__).resolve().parent
optimized.EXP=EXP
optimized.send.EXP=EXP
SELECTOR=EXP/'arduino/v16/oscilloscope/sketch/ping_variant.h'
IntegrityDecoder=contract.Decoder


class TimingDecoder(IntegrityDecoder):
    latest=None

    def __init__(self):
        super().__init__()
        self.timing_buffer=bytearray()
        self.reset_timing()
        TimingDecoder.latest=self

    def reset_timing(self):self.prepare_us=[];self.check_us=[]

    def reset_metrics(self):
        super().reset_metrics()
        self.reset_timing()

    def feed(self,data):
        self.timing_buffer.extend(data)
        while len(self.timing_buffer)>=992:
            p=bytes(self.timing_buffer[:992]);del self.timing_buffer[:992]
            super().feed(p)
            if struct.unpack_from('<H',p,6)[0]==20:
                prepare,check=struct.unpack_from('<II',p,40)
                self.prepare_us.append(prepare);self.check_us.append(check)

    def summary(self):
        result={}
        for name,values in [('tx_prepare',self.prepare_us),('rx_check',self.check_us)]:
            if values:
                result[name]=dict(count=len(values),mean_us=float(np.mean(values)),
                    p50_p95_p99_max_us=np.percentile(values,[50,95,99,100]).tolist())
        return result


contract.Decoder=TimingDecoder


class PingProbe(optimized.OptimizedSweep):
    def __init__(self):
        super().__init__()
        cfg=dict(self.candidate.config)
        cfg['local_app']='experimentos/adc8_ping_word_v17/arduino/v16/oscilloscope'
        self.candidate=Board(cfg)
        self.variant='A'
        self.report.update(revision='adc8_ping_word_abba_v17',variants={},
            plan=dict(order=['A','B','B','A'],ticks=[114,112],node_pairs=3456,
                      seconds=30,qualification_seconds=[60,120,120,120]),
            instrumentation='Only existing prepare/check timing fields; no stage profiler',
            production_sources_modified=False,
            gate='All B cases intact and headroom true; B send means at least2% lower with no overlap against A at both rates')

    def trial(self,*args,**kwargs):
        row=super().trial(*args,**kwargs)
        row['variant']=self.variant
        row['legacy_timings']=TimingDecoder.latest.summary() if TimingDecoder.latest else {}
        self.save()
        return row

    def load(self,variant):
        optimized.send.usb_stream.stop(self.candidate)
        self.candidate.stop()
        SELECTOR.write_text('#pragma once\n#define SCOPE_WORD_PING '+('1' if variant=='B' else '0')+'\n')
        files=self.candidate.check_sources()
        self.candidate.push_sources(files,self.candidate.remote)
        self.report['variants'][variant]={p.relative_to(self.candidate.local).as_posix():
            hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        self.variant=variant;self.save()
        self.candidate.start()
        optimized.send.start_experimental_relay(self.candidate,self.deployment['candidate_relay'])
        self.dirty=False

    def gate(self):
        decisions=[]
        for ticks in (114,112):
            rows=[c for c in self.report['cases'] if c['stage']=='abba' and c['ticks']==ticks]
            a=[r for r in rows if r['variant']=='A'];b=[r for r in rows if r['variant']=='B']
            valid=len(a)==len(b)==2 and all(r['ok'] for r in rows)
            if not valid:
                decisions.append(dict(ticks=ticks,passes=False,reason='Missing or failed cases'))
                continue
            av=[r['metrics']['send_mean_us'] for r in a]
            bv=[r['metrics']['send_mean_us'] for r in b]
            gain=1-float(np.mean(bv))/float(np.mean(av))
            decisions.append(dict(ticks=ticks,a_send_mean_us=av,b_send_mean_us=bv,
                relative_gain=gain,passes=gain>=.02 and max(bv)<min(av) and
                all(r.get('headroom_ok',False) for r in b)))
        self.report['abba_decisions']=decisions
        self.save()
        return all(d['passes'] for d in decisions)

    def run_probe(self):
        self.save()
        try:
            self.prepare()
            self.report['variants']['A']=self.report['candidate_source_hashes']
            self.candidate.start()
            optimized.send.start_experimental_relay(self.candidate,self.deployment['candidate_relay'])
            for block,variant in enumerate(('A','B','B','A')):
                if variant!=self.variant:self.load(variant)
                elif block:self.fast_reset()
                for i,ticks in enumerate((114,112)):
                    row=self.trial(8,ticks,3456,30,'abba',restart=i>0)
                    row['abba_block']=block
                    self.save()
                    if not row['ok']:raise RuntimeError('ABBA integrity failure; stop experiment')
            if self.gate():
                self.load('B')
                winner=self.qualify(8,112,3456)
                self.report['winners']['8']=winner
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
    SELECTOR.write_text('#pragma once\n#define SCOPE_WORD_PING 0\n')
    raise SystemExit(PingProbe().run_probe())
