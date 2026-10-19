"""Bounded ADC8 CH1 screen near 1.4 MHz; preserves earlier campaign evidence."""
import sys
import json
import time
import hashlib
from pathlib import Path
from dataclasses import asdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experimentos.maxfreq_v16.sweep import Sweep, EXP, start_relay, usb_stream
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from monitor.v16.receiver.unoq_usb import Connection
from monitor.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.v16.receiver.unoq_switch import Mode
from monitor.v16.receiver.unoq_wav import State
from monitor.v16.bode_calibration import instrument_identity


class Probe(Sweep):
    def __init__(self):
        super().__init__()
        self.folder = EXP / ('probe_1400_' + time.strftime('%Y%m%d_%H%M%S'))
        self.folder.mkdir()
        self.report.update(cases=[], winners={}, prior=None, revision='adc8_1400_existing_specialized_v2',
                           plan={'ticks': [115,114], 'nodes': [3456,6912,8192],
                                 'screen_seconds': 5, 'acceptance_seconds': [60,120,120,120,600]},
                           selector_modified=False)

    def save(self):
        (self.folder/'report.json').write_text(json.dumps(self.report, indent=2)+'\n')

    def logs(self, name):
        try:
            data = self.stable.run('shell', 'docker logs '+usb_stream.CONTAINER+' 2>&1', capture=True).stdout
            (self.folder/name).write_text(data)
            return data
        except Exception as exc:
            self.report['log_error'] = str(exc)

    def trial(self, *args, **kwargs):
        wall, mono = time.time(), time.monotonic()
        row = super().trial(*args, **kwargs)
        row['wall_monotonic_drift_seconds'] = (time.time()-wall)-(time.monotonic()-mono)
        if abs(row['wall_monotonic_drift_seconds']) > 2:
            row.update(ok=False, error='Host sleep/clock discontinuity')
            self.dirty = True
        self.save()
        return row

    def snapshot(self):
        require_exclusive_monitor()
        if 'ESTAB' in self.stable.shell('ss','-tn','sport','=',':8766',capture=True).stdout:
            raise RuntimeError('Q has another reader')
        self.report['prior_identity'] = instrument_identity(self.stable.serial)
        if self.report['prior_identity'] is None:
            raise RuntimeError('Unknown production firmware identity')
        with Connection(self.stable.serial) as connection:
            receiver = OutputReceiver(connection, lambda batch: None)
            deadline = time.monotonic()+3
            while receiver.decoder.mode is None and time.monotonic()<deadline:
                receiver.pump()
            if receiver.decoder.mode != Mode.SPI:
                raise RuntimeError('Requires SPI prior state')
            receiver.select(Mode.SPI)
            generator = receiver.generator().active
            receiver.wav_request()
            deadline = time.monotonic()+3
            while receiver.wav_pending and time.monotonic()<deadline:
                receiver.pump()
            if receiver.wav_pending or receiver.wav_status is None or receiver.wav_status.state != State.IDLE:
                raise RuntimeError('WAV not idle')
            self.prior = {'adc': asdict(receiver.config), 'generator': asdict(generator)}
        self.report['prior'] = self.prior
        mounts = json.loads(self.stable.shell('docker','inspect','--format','{{json .Mounts}}',
                                             usb_stream.CONTAINER,capture=True).stdout)
        targets = [m['Source'] for m in mounts if m['Destination']=='/work/unoq_stream']
        if len(targets)!=1:
            raise RuntimeError('Cannot identify current relay binary')
        self.deployment['stable_relay'] = targets[0]
        self.save()

    def prepare(self):
        self.snapshot()
        # Reuse the already compiled candidate only when its sources match exactly.
        hashes = {p.relative_to(self.candidate.local).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.candidate.check_sources()}
        code = ('import json,hashlib,pathlib,sys; root=pathlib.Path(sys.argv[1]); '
                'expected=json.loads(sys.argv[2]); '
                'assert all((root/p).is_file() and hashlib.sha256((root/p).read_bytes()).hexdigest()==h '
                'for p,h in expected.items()), "Candidate sources differ"')
        self.candidate.shell('python3','-c',code,self.candidate.remote,json.dumps(hashes))
        self.candidate.shell('test','-x',self.deployment['candidate_relay'])
        self.report['candidate_source_hashes'] = hashes
        self.report['deployment'] = dict(self.deployment)
        self.report['backup'] = str(self.stable.backup())
        self.save()

    def run_probe(self):
        self.save()
        try:
            self.prepare()
            require_exclusive_monitor()
            self.switched = True
            usb_stream.stop(self.stable)
            self.stable.stop()
            self.candidate.start()
            start_relay(self.candidate,self.deployment['candidate_relay'])
            passing = []
            for node in (3456,6912,8192):
                for ticks in (115,114):
                    row = self.trial(8,ticks,node,5,'screen',restart=bool(self.report['cases']))
                    if row['ok']:
                        passing.append((ticks,node))
            for ticks,node in sorted(passing):
                accepted = True
                for stage,seconds in [('finalist',60),('acceptance_1',120),('acceptance_2',120),
                                      ('acceptance_3',120),('endurance',600)]:
                    row = self.trial(8,ticks,node,seconds,stage,restart=True)
                    if not row['ok']:
                        accepted = False
                        break
                if accepted:
                    self.report['winners']['8'] = {'ticks':ticks,'node_pairs':node,
                                                   'actual_rate':160000000/ticks}
                    break
            self.report['ok'] = bool(self.report['winners'])
        except BaseException as exc:
            self.report['error'] = str(exc)
            print('PROBE ERROR',exc,flush=True)
        finally:
            if self.switched:
                try:
                    self.restore()
                    self.report['final_identity'] = instrument_identity(self.stable.serial)
                    self.report['restored'] &= self.report['final_identity']==self.report['prior_identity']
                except Exception as exc:
                    self.report['restore_error'] = str(exc)
            else:
                self.report['restored'] = True
            self.save()
        print('REPORT',self.folder/'report.json','ACCEPTED',self.report['ok'],
              'RESTORED',self.report['restored'],flush=True)
        return 0 if self.report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(Probe().run_probe())
