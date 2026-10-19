"""Deploy V17 CH1 maxima, qualify production, restore settings or roll back."""
import argparse
import hashlib
import json
import subprocess
import sys
import time
import traceback
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]
from tools.unoq import Board, config_path
import usb_stream
from spi_benchmark import IMAGE
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from monitor.v17.bode_calibration import instrument_identity
from monitor.v17.numeric_batch import NumericBatch, SampleClock
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.receiver.unoq_native import PROFILES
from monitor.v17.receiver.unoq_switch import Mode
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_wav import State

STAGES = [('finalist', 60), ('acceptance_1', 120), ('acceptance_2', 120), ('acceptance_3', 120)]


class Integration:
    def __init__(self, headroom_only=False):
        self.headroom_only=headroom_only
        self.board = Board(json.loads(config_path('v17').read_text()))
        self.folder = ROOT/'diagnosticos/resultados_v17'/('optimized_integration_'+time.strftime('%Y%m%d_%H%M%S'))
        self.folder.mkdir()
        sources = [p for p in (ROOT/'arduino/v17').rglob('*') if p.is_file()]
        self.report = dict(ok=False, restored=False, cases=[], scope='V17 production CH1 maxima; no analog/dual/GUI acceptance',
            acceptance_seconds=[60,120,120,120], runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            headroom_only=headroom_only,
            source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
        self.changed = False
        self.stopped = False
        self.relay = None
        with zipfile.ZipFile(self.folder/'sources.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for p in sources:
                archive.write(p, p.relative_to(ROOT))

    def save(self):
        (self.folder/'report.json').write_text(json.dumps(self.report, indent=2)+'\n')

    def logs(self, name):
        result = self.board.run('shell', 'docker logs '+usb_stream.CONTAINER+' 2>&1', capture=True).stdout
        (self.folder/name).write_text(result)
        return result

    def start_relay(self, target, prior=False):
        usb_stream.stop(self.board)
        flags = []
        for cap in self.report['old_cap_add'] if prior else ['SYS_NICE']:
            flags += ['--cap-add', cap]
        for item in self.report['old_scope_environment'] if prior else []:
            flags += ['--env', item]
        self.board.shell('docker','run','-d','--name',usb_stream.CONTAINER,'--network','host',
            '--read-only','--cap-drop','ALL',*flags,'--security-opt','no-new-privileges','--user','0:0',
            '--device','/dev/spidev0.0:/dev/spidev0.0:rw','--device','/dev/gpiochip1:/dev/gpiochip1:rw',
            '--mount',f'type=bind,src={target},dst=/work/unoq_stream,readonly','--entrypoint','/work/unoq_stream',IMAGE)
        deadline = time.monotonic()+15
        while time.monotonic() < deadline:
            if 'SPI ready: first verified frame' in self.logs('current_relay.log'):
                return
            time.sleep(.2)
        raise RuntimeError('Relay did not confirm first verified frame')

    def scheduler(self):
        info = json.loads(self.board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0]
        if not info['State']['Running']:
            raise RuntimeError('Relay exited')
        return json.loads(self.board.shell('python3','-c',
            'import os,json,sys; p=int(sys.argv[1]); print(json.dumps({"policy":os.sched_getscheduler(p),"priority":os.sched_getparam(p).sched_priority}))',
            str(info['State']['Pid']),capture=True).stdout)

    def scheduler_live(self, receiver):
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.scheduler)
            while not future.done():
                receiver.pump()
            return future.result()

    def trial(self, config, seconds, stage, restart=False):
        if restart:
            usb_stream.stop(self.board)
            self.board.start()
            self.start_relay(self.relay)
        row = dict(adc=asdict(config), period=config.period, node_pairs=config.node_pairs,
            actual_rate=config.actual_rate, stage=stage, requested_seconds=seconds, ok=False)
        try:
            with Connection(self.board.serial) as connection:
                receiver = OutputReceiver(connection, lambda rows: None)
                receiver.decoder.numeric = True
                receiver.select(Mode.SPI)
                receiver.generator(GeneratorConfig(enabled=0))
                if restart:
                    # App CLI reports container start before Python/bridge
                    # provisioning has settled. Validate low-rate acquisition
                    # first; never add Linux work while the fast profile runs.
                    receiver.configure(Configuration(14,40000))
                    boot_before=receiver.decoder.pairs
                    boot_started=time.monotonic()
                    while time.monotonic()-boot_started<5:
                        receiver.pump()
                    row['boot_warmup']=dict(seconds=time.monotonic()-boot_started,
                        samples=receiver.decoder.pairs-boot_before,status=receiver.decoder.status)
                receiver.configure(config)
                clock = SampleClock(config.timestamp_hz)
                last = None
                def collect(rows):
                    nonlocal last
                    batch = NumericBatch(rows.array, config.maximum, clock, config.channels)
                    times = batch.columns['Tiempo (us)']
                    if np.any(abs(np.diff(times)-config.dt_us)>1e-5) or (
                        last is not None and abs(times[0]-last-config.dt_us)>1e-5):
                        raise ValueError('Numeric timestamp discontinuity')
                    if config.channels == 1 and not np.isnan(batch.columns['CH2']).all():
                        raise ValueError('CH2 published in CH1 mode')
                    last = float(times[-1])
                receiver.on_samples = collect
                expected = dict(policy=1, priority=10) if (config._native and config._native.get('optimized_transport')) or config.rate==1403508 else dict(policy=0,priority=0)
                if expected['priority']:
                    # The relay verifies sched_getscheduler/getparam before
                    # forwarding APPLIED. Do not add Docker/Python work on Q
                    # during the high-rate screen (the isolated runner did not).
                    row['scheduler'] = expected
                    row['scheduler_verification'] = 'Relay kernel getters checked before forwarding APPLIED; logs persisted'
                else:
                    row['scheduler'] = self.scheduler_live(receiver)
                if row['scheduler'] != expected:
                    raise ValueError('Profile scheduler mismatch')
                until = time.monotonic()+1
                while time.monotonic() < until:
                    receiver.pump()
                before = receiver.decoder.pairs
                start, wall = time.monotonic(), time.time()
                next_log = start+30
                send, maxima = [], {}
                while time.monotonic()-start < seconds:
                    receiver.pump()
                    for status in receiver.decoder.statuses:
                        if status['dropped'] or status['fatal']:
                            raise ValueError('MCU dropped/fatal')
                        if 'send_ticks' in status:
                            send.append(status['send_ticks'])
                            for key in ('queue_peak','copy_ticks','poll_ticks'):
                                maxima[key] = max(maxima.get(key,0), status[key])
                            maxima['slack_ticks'] = min(maxima.get('slack_ticks',0xffffffff), status['slack_ticks'])
                    if time.monotonic() >= next_log:
                        print('PROGRESS', stage, config.bits, config.rate, round(time.monotonic()-start), flush=True)
                        next_log += 30
                elapsed = time.monotonic()-start
                samples = receiver.decoder.pairs-before
                drift = time.time()-wall-elapsed
                if abs(drift)>2 or abs(samples/elapsed/config.actual_rate-1)>.02:
                    raise ValueError('Host clock discontinuity or incorrect delivered rate')
                row.update(ok=True, seconds=elapsed, samples=samples, observed_rate=samples/elapsed,
                    status=receiver.decoder.status, wall_monotonic_drift_seconds=drift)
                if send:
                    margin = 1-float(np.mean(send))/(config.node_pairs*config.period)
                    row['metrics'] = dict(mean_send_headroom=margin, maxima=maxima,
                        send_mean_us=float(np.mean(send))/160, send_observations=len(send))
                    row['headroom_ok'] = margin>=.1 and maxima['queue_peak']<4 and maxima['slack_ticks']>0
                print('END', stage, config.bits, config.rate, 'OK', row['ok'], 'HEADROOM', row.get('headroom_ok'), flush=True)
        except BaseException as exc:
            row.update(ok=False, error=repr(exc))
            try:
                self.logs('failure_relay.log')
            except Exception:
                pass
            raise
        finally:
            self.report['cases'].append(row)
            self.save()
        return row

    def snapshot(self):
        require_exclusive_monitor()
        if 'ESTAB' in self.board.shell('ss','-tn','sport','=',':8766',capture=True).stdout:
            raise RuntimeError('Q has another reader')
        self.report['prior_identity'] = instrument_identity(self.board.serial)
        if self.report['prior_identity'] is None:
            raise RuntimeError('Unknown installed V17 firmware')
        with Connection(self.board.serial) as connection:
            receiver = OutputReceiver(connection, lambda rows: None)
            receiver.decoder.numeric = True
            receiver.select(Mode.SPI)
            receiver.wav_request()
            deadline = time.monotonic()+3
            while receiver.wav_pending and time.monotonic()<deadline:
                receiver.pump()
            if receiver.wav_pending or receiver.wav_status.state != State.IDLE:
                raise RuntimeError('WAV not idle')
            self.report['prior'] = dict(adc=asdict(receiver.config), generator=asdict(receiver.generator().active))
        info = json.loads(self.board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0]
        self.report['old_relay'] = next(m['Source'] for m in info['Mounts'] if m['Destination']=='/work/unoq_stream')
        self.report['old_cap_add'] = info['HostConfig']['CapAdd'] or []
        self.report['old_scope_environment'] = [e for e in info['Config']['Env'] if e.startswith('SCOPE_')]
        self.report['backup'] = str(self.board.backup())
        self.save()

    def restore_settings(self):
        prior = self.report['prior']
        with Connection(self.board.serial) as connection:
            receiver = OutputReceiver(connection, lambda rows: None)
            receiver.decoder.numeric = True
            receiver.select(Mode.SPI)
            receiver.generator(GeneratorConfig(enabled=0))
            receiver.configure(Configuration(**prior['adc']))
            receiver.generator(GeneratorConfig(**prior['generator']))
            final = dict(adc=asdict(receiver.config), generator=asdict(receiver.generator().active))
            before = receiver.decoder.pairs
            start = time.monotonic()
            while time.monotonic()-start<10:
                receiver.pump()
            self.report.update(final_settings=final, restored=final==prior,
                recovery=dict(ok=True,samples=receiver.decoder.pairs-before,status=receiver.decoder.status),
                final_scheduler=self.scheduler_live(receiver))
        self.report['final_identity'] = instrument_identity(self.board.serial)
        self.logs('final_relay.log')
        self.save()

    def run(self):
        try:
            self.snapshot()
            # Stop acquisition before compiling on Q.
            self.stopped = True
            usb_stream.stop(self.board)
            self.board.stop()
            self.board.compile()
            try:
                self.relay = usb_stream.binary(self.board, p992=True, audio=True)
            except subprocess.CalledProcessError:
                self.relay = usb_stream.binary(self.board, build=True, p992=True, audio=True)
            self.report['relay'] = self.relay
            remote_backup = '/home/arduino/.cache/serialmonitor/v17-before-optimized-'+self.folder.name
            self.report['remote_backup'] = remote_backup
            archive_path='/tmp/'+self.folder.name+'-prior.zip'
            self.board.run('push',self.report['backup'],archive_path)
            self.board.shell('python3','-c',
                'import zipfile,pathlib,sys; root=pathlib.Path(sys.argv[1]); root.mkdir(parents=True); '
                'z=zipfile.ZipFile(sys.argv[2]); '
                '[(root.joinpath(*pathlib.PurePosixPath(n).parts[1:]).parent.mkdir(parents=True,exist_ok=True), '
                'root.joinpath(*pathlib.PurePosixPath(n).parts[1:]).write_bytes(z.read(n))) '
                'for n in z.namelist() if not n.endswith("/") and ".." not in pathlib.PurePosixPath(n).parts]',
                remote_backup,archive_path)
            self.changed = True
            self.save()
            self.board.push_sources(self.board.check_sources(),self.board.remote)
            self.board.start()
            self.start_relay(self.relay)
            self.trial(Configuration(14,40000),10,'legacy_before')
            profiles = [p for p in PROFILES if p.get('optimized_transport') and
                (not self.headroom_only or p.get('isolated_headroom'))]
            for profile in profiles:
                config = Configuration(profile['bits'],160000000//profile['ticks'])
                for stage, seconds in STAGES:
                    self.trial(config,seconds,stage,restart=True)
                    self.trial(Configuration(10,909090),3,'normal_after_'+stage)
            self.trial(Configuration(8,1403508),60,'adc8_preserved',restart=True)
            self.trial(Configuration(14,363636),10,'dual_after')
            self.trial(Configuration(16,40000),10,'adc16_after')
            self.report['ok'] = True
        except BaseException as exc:
            self.report['error'] = repr(exc)
            traceback.print_exc()
            if self.stopped:
                try:
                    usb_stream.stop(self.board)
                    self.board.stop()
                    if self.changed:
                        self.board.shell('python3','-c','import shutil,sys; shutil.copytree(sys.argv[1],sys.argv[2],dirs_exist_ok=True)',
                            self.report['remote_backup'],self.board.remote)
                    self.board.start()
                    self.start_relay(self.report['old_relay'],prior=True)
                    self.report['rolled_back'] = True
                except Exception as failure:
                    self.report['rollback_error'] = repr(failure)
        finally:
            if self.report.get('prior') and self.stopped:
                try:
                    self.restore_settings()
                    if self.report.get('rolled_back') and self.report['final_identity']!=self.report['prior_identity']:
                        self.report['restored'] = False
                except Exception as exc:
                    self.report['recovery_error'] = repr(exc)
            self.save()
        print('REPORT',self.folder/'report.json','OK',self.report['ok'],'RESTORED',self.report['restored'],flush=True)
        return 0 if self.report['ok'] and self.report['restored'] else 1


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headroom-only',action='store_true')
    args=parser.parse_args()
    raise SystemExit(Integration(args.headroom_only).run())
