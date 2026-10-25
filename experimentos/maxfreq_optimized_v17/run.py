"""Isolated CH1 ADC10/12/14 search using the accepted ADC8 send pipeline.

One Q owner; live V17 snapshot, backup, per-case evidence and exact restoration.
User shortened acceptance to 60 + three independent 120 s runs (no 600 s).
"""
import sys
import json
import time
import hashlib
from pathlib import Path
from dataclasses import asdict

ROOT = Path(__file__).resolve().parents[2]
EXP = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]
import experimentos.send1400_v16.run as send
import experimentos.maxfreq_v16.contract as contract
from experimentos.maxfreq_v16.sweep import Sweep
from tools.unoq import Board, config_path
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.receiver.unoq_switch import Mode
from monitor.v17.receiver.unoq_wav import State
from monitor.v17.bode_calibration import instrument_identity
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from spi_benchmark import IMAGE

contract.CAPACITY[12] = 576
send.EXP = EXP
NODES = {10: [2784, 5568, 8192], 12: [2304, 4608, 8192], 14: [1984, 3968, 7936]}
STAGES = [('finalist', 60), ('acceptance_1', 120), ('acceptance_2', 120), ('acceptance_3', 120)]


class OptimizedSweep(send.SendProbe):
    def __init__(self):
        super().__init__()
        self.stable = Board(json.loads(config_path('v17').read_text()))
        config = dict(self.stable.config)
        # Dedicated experimental app; never push sources into scope-v17.
        config.update(name='Scope V16 Send1400 Experimental',
            remote_app='/home/arduino/ArduinoApps/scope-v16-send1400-experimental',
            local_app='experimentos/maxfreq_optimized_v17/arduino/historico/v16/oscilloscope')
        self.candidate = Board(config)
        self.report.update(revision='optimized_ch1_adc10_12_14_v17', cases=[], winners={},
            plan={'bits': [10, 12, 14], 'nodes': NODES, 'ticks_bounds': [78, 640],
                'screen_seconds': 10, 'acceptance_seconds': [60, 120, 120, 120]},
            channels=1, acceptance_limit='User requested no 600 s run; maximum run 120 s',
            selector_modified=False, analog='Not measured')
        self.report['source_hashes'] = {
            str(p.relative_to(EXP)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((EXP/'arduino').rglob('*')) if p.is_file()}
        self.report['runner_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self.observed = {}
        self.accepted = {}
        self.rejected = set()

    def snapshot(self):
        if self.report.get('prior') is not None:
            return
        require_exclusive_monitor()
        if 'ESTAB' in self.stable.shell('ss', '-tn', 'sport', '=', ':8766', capture=True).stdout:
            raise RuntimeError('Q has another reader')
        identity = instrument_identity(self.stable.serial)
        if identity is None:
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
        mounts = json.loads(self.stable.shell('docker', 'inspect', '--format', '{{json .Mounts}}',
            send.usb_stream.CONTAINER, capture=True).stdout)
        targets = [m['Source'] for m in mounts if m['Destination'] == '/work/unoq_stream']
        if len(targets) != 1:
            raise RuntimeError('Cannot identify current relay binary')
        self.deployment['stable_relay'] = targets[0]
        self.report['stable_cap_add'] = json.loads(self.stable.shell('docker', 'inspect',
            '--format', '{{json .HostConfig.CapAdd}}', send.usb_stream.CONTAINER, capture=True).stdout) or []
        environment = json.loads(self.stable.shell('docker', 'inspect', '--format', '{{json .Config.Env}}',
            send.usb_stream.CONTAINER, capture=True).stdout)
        self.report['stable_scope_environment'] = [item for item in environment if item.startswith('SCOPE_')]
        self.report.update(prior=self.prior, prior_identity=identity)
        self.save()

    def trial(self, *args, **kwargs):
        # Avoid the legacy ADC8-only auto-baseline; this campaign runs its own.
        return send.Probe.trial(self, *args, **kwargs)

    def check(self, bits, ticks, node, stage='screen', seconds=10):
        key = (bits, ticks, node)
        if stage == 'screen' and key in self.observed:
            return self.observed[key]
        row = self.trial(bits, ticks, node, seconds, stage)
        if not row['ok']:
            row = self.trial(bits, ticks, node, seconds, 'repeat_failure', restart=True)
        self.observed[key] = row
        return row

    def boundaries(self, bits, node, margin=False):
        # Binary integer-tick search; physical failures are independently repeated.
        stage = 'margin_screen' if margin else 'screen'
        def passes(ticks):
            row = self.check(bits, ticks, node, stage)
            return row['ok'] and (not margin or row.get('headroom_ok', False))
        if not passes(640):
            raise RuntimeError(f'Baseline ADC{bits} N{node} failed at 250 kHz')
        if passes(78):
            return 78
        fail, good = 78, 640
        while good-fail > 1:
            ticks = (good+fail)//2
            if passes(ticks): good = ticks
            else: fail = ticks
        self.report.setdefault('boundaries', []).append(dict(bits=bits, node_pairs=node,
            criterion='headroom' if margin else 'integrity', passing_ticks=good,
            failing_ticks=fail, monotonic_search=True))
        self.save()
        return good

    def qualify(self, bits, ticks, node):
        key = (bits, ticks, node)
        if key in self.accepted: return self.accepted[key]
        if key in self.rejected: return None
        rows = []
        for stage, seconds in STAGES:
            row = self.trial(bits, ticks, node, seconds, stage, restart=True)
            rows.append(row)
            if not row['ok']:
                self.rejected.add(key)
                return None
        result = dict(bits=bits, ticks=ticks, node_pairs=node, actual_rate=160000000/ticks,
            integrity_accepted=True, headroom_accepted=all(r.get('headroom_ok', False) for r in rows),
            acceptance_seconds=[60, 120, 120, 120])
        self.accepted[key] = result
        return result

    def search(self):
        for bits, nodes in NODES.items():
            starts = {node: self.boundaries(bits, node) for node in nodes}
            winner = None
            # Recheck neighboring integer profiles if screening overestimated stability.
            while winner is None:
                ticks = min(starts.values())
                if ticks > 640: raise RuntimeError(f'No accepted ADC{bits} profile')
                for node in nodes:
                    if starts[node] != ticks: continue
                    winner = self.qualify(bits, ticks, node)
                    if winner is not None: break
                    starts[node] += 1
            self.report['winners'][str(bits)] = dict(maximum_integrity=winner, maximum_headroom=None)
            self.save()
            if winner['headroom_accepted']:
                self.report['winners'][str(bits)]['maximum_headroom'] = winner
            else:
                starts = {node: self.boundaries(bits, node, margin=True) for node in nodes}
                margin_winner = None
                while margin_winner is None:
                    ticks = min(starts.values())
                    if ticks > 640: raise RuntimeError(f'No headroom ADC{bits} profile')
                    for node in nodes:
                        if starts[node] != ticks: continue
                        result = self.qualify(bits, ticks, node)
                        if result is not None and result['headroom_accepted']:
                            margin_winner = result; break
                        starts[node] += 1
                self.report['winners'][str(bits)]['maximum_headroom'] = margin_winner
            self.save()

    def restore(self):
        self.logs('final_candidate_relay.log')
        send.usb_stream.stop(self.candidate)
        self.candidate.stop()
        self.stable.start()
        flags = []
        for cap in self.report['stable_cap_add']: flags += ['--cap-add', cap]
        for item in self.report['stable_scope_environment']: flags += ['--env', item]
        self.stable.shell('docker', 'run', '-d', '--name', send.usb_stream.CONTAINER,
            '--network', 'host', '--read-only', '--cap-drop', 'ALL', *flags,
            '--security-opt', 'no-new-privileges', '--user', '0:0',
            '--device', '/dev/spidev0.0:/dev/spidev0.0:rw',
            '--device', '/dev/gpiochip1:/dev/gpiochip1:rw',
            '--mount', f'type=bind,src={self.deployment["stable_relay"]},dst=/work/unoq_stream,readonly',
            '--entrypoint', '/work/unoq_stream', IMAGE)
        deadline = time.monotonic()+15
        while time.monotonic()<deadline:
            if 'SPI ready: first verified frame' in self.logs('restored_relay.log'): break
            time.sleep(.2)
        else: raise RuntimeError('Restored relay did not confirm first frame')
        with Connection(self.stable.serial) as connection:
            receiver = OutputReceiver(connection, lambda batch: None, print)
            receiver.select(Mode.SPI)
            receiver.generator(GeneratorConfig(enabled=0))
            receiver.configure(Configuration(**self.prior['adc']))
            receiver.generator(GeneratorConfig(**self.prior['generator']))
            self.report['final_adc'] = asdict(receiver.config)
            self.report['final_generator'] = asdict(receiver.generator().active)
            before = receiver.decoder.pairs
            start = time.monotonic()
            while time.monotonic()-start < 10: receiver.pump()
            self.report['restore_samples'] = receiver.decoder.pairs-before
            self.report['restore_integrity_ok'] = self.report['restore_samples'] > 0
        self.report['final_identity'] = instrument_identity(self.stable.serial)
        self.report['restored'] = (self.report['final_adc'] == self.prior['adc'] and
            self.report['final_generator'] == self.prior['generator'] and
            self.report['final_identity'] == self.report['prior_identity'] and self.report['restore_integrity_ok'])

    def run_probe(self):
        self.save()
        try:
            self.prepare()
            require_exclusive_monitor()
            self.candidate.start()
            send.start_experimental_relay(self.candidate, self.deployment['candidate_relay'])
            baseline = self.trial(8, 131, 6912, 10, 'baseline')
            if not baseline['ok']: raise RuntimeError('Optimized ADC8 baseline failed')
            self.search()
            self.report['ok'] = len(self.report['winners']) == 3
        except BaseException as exc:
            self.report['error'] = str(exc)
            print('SWEEP ERROR', exc, flush=True)
        finally:
            if self.switched:
                try: self.restore()
                except Exception as exc: self.report['restore_error'] = str(exc)
            else: self.report['restored'] = True
            self.save()
        print('REPORT', self.folder/'report.json', 'OK', self.report['ok'], 'RESTORED', self.report['restored'], flush=True)
        return 0 if self.report['restored'] and self.report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(OptimizedSweep().run_probe())
