"""Focused V16 trial8 acceptance at ADC8/114/N3456, retaining startup peak evidence."""
import json
import time
from pathlib import Path
from experimentos.send1400_v16.run import SendProbe, Probe, ROOT, EXP
import experimentos.maxfreq_v16.contract as contract
from experimentos.maxfreq_v16.sweep import usb_stream
from monitor.v16.bode_calibration import instrument_identity
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor

OriginalDecoder=contract.Decoder
EVENTS=[]
class ObservedDecoder(OriginalDecoder):
    def __init__(self):
        super().__init__()
        self.pending=bytearray();self.started=time.monotonic();self.previous_peak=None
    def record(self,event):
        EVENTS.append({'event':event,'elapsed':time.monotonic()-self.started,
                       'sequence':self.seq,'samples_seen':self.pairs,
                       'status':dict(self.status) if self.status else None})
    def feed(self,data):
        # Pass complete frames to the unchanged decoder and observe every status.
        self.pending.extend(data)
        while len(self.pending)>=992:
            frame=bytes(self.pending[:992]);del self.pending[:992]
            super().feed(frame)
            if self.status:
                key=(self.status['epoch'],self.status['queue_peak'])
                if key!=self.previous_peak:
                    self.record('peak_change');self.previous_peak=key
    def reset_metrics(self):
        self.record('measurement_start')
        return super().reset_metrics()
contract.Decoder=ObservedDecoder

class MarginProbe(SendProbe):
    def __init__(self):
        super().__init__()
        self.report.update(revision='send1400_spi38_fifo10_pointer_pipeline_v8_observed',
            plan={'ticks':[114],'nodes':[3456],'baseline_seconds':10,
                  'acceptance_seconds':[60,120,120,120,600]},
            queue_peak_observation='Every decoded frame; sticky peak retained, including startup')
        self.report['experiment_label']='V16 isolated send experiment, trial8 with peak observations'
        self.report['runner_sha256']=__import__('hashlib').sha256(Path(__file__).read_bytes()).hexdigest()
    def observed_trial(self,*args,**kwargs):
        EVENTS.clear()
        row=Probe.trial(self,*args,**kwargs)
        row['queue_peak_events']=list(EVENTS)
        self.save()
        return row
    def run_probe(self):
        self.save()
        try:
            self.prepare()
            require_exclusive_monitor()
            self.candidate.start()
            from experimentos.send1400_v16.run import start_experimental_relay
            start_experimental_relay(self.candidate,self.deployment['candidate_relay'])
            baseline=self.observed_trial(8,131,6912,10,'baseline')
            if not baseline['ok']:raise RuntimeError('V16 experiment failed reference, higher rate not tested')
            rows=[]
            for stage,seconds in [('finalist',60),('acceptance_1',120),('acceptance_2',120),
                                  ('acceptance_3',120),('endurance',600)]:
                row=self.observed_trial(8,114,3456,seconds,stage,restart=True)
                rows.append(row)
                if not row['ok']:break
            self.report['ok']=len(rows)==5 and all(c['ok'] for c in rows)
            self.report['headroom_accepted']=self.report['ok'] and all(c.get('headroom_ok',False) for c in rows)
            if self.report['ok']:
                self.report['winners']['8']={'ticks':114,'node_pairs':3456,
                    'actual_rate':160000000/114,'headroom_accepted':self.report['headroom_accepted']}
        except BaseException as exc:
            self.report['error']=str(exc)
            print('PROBE ERROR',exc,flush=True)
        finally:
            if self.switched:
                try:
                    self.restore()
                    self.report['final_identity']=instrument_identity(self.stable.serial)
                    self.report['restored'] &= self.report['final_identity']==self.report['prior_identity']
                except Exception as exc:self.report['restore_error']=str(exc)
            else:self.report['restored']=True
            self.save()
        print('REPORT',self.folder/'report.json','ACCEPTED',self.report['ok'],
              'HEADROOM',self.report.get('headroom_accepted',False),'RESTORED',self.report['restored'],flush=True)
        return 0 if self.report['restored'] else 1
if __name__=='__main__':raise SystemExit(MarginProbe().run_probe())
