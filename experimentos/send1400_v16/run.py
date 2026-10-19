"""Isolated optimized MCU and relay experiment for ADC8 CH1 near 1.4 MHz."""
import sys
import json
import hashlib
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experimentos.maxfreq_v16.probe_1400 import Probe
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from tools.unoq import Board
import usb_stream
from spi_benchmark import IMAGE
import experimentos.maxfreq_v16.sweep as sweep_module
import experimentos.maxfreq_v16.probe_1400 as probe_module

original_start_relay = sweep_module.start_relay

def start_experimental_relay(board, target):
    if board.config['name'] != 'Scope V16 Send1400 Experimental':
        return original_start_relay(board, target)
    usb_stream.stop(board)
    board.shell('docker','run','-d','--name',usb_stream.CONTAINER,
                '--network','host','--read-only','--cap-drop','ALL',
                '--cap-add','SYS_NICE','--env','SCOPE_EXPERIMENT_RT=1',
                '--security-opt','no-new-privileges','--user','0:0',
                '--device','/dev/spidev0.0:/dev/spidev0.0:rw',
                '--device','/dev/gpiochip1:/dev/gpiochip1:rw',
                '--mount',f'type=bind,src={target},dst=/work/unoq_stream,readonly',
                '--entrypoint','/work/unoq_stream',IMAGE)
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        logs=board.run('shell','docker logs '+usb_stream.CONTAINER+' 2>&1',capture=True).stdout
        if 'SPI ready: first verified frame' in logs and 'SCHED_FIFO priority 10' in logs:
            return
        time.sleep(.2)
    raise RuntimeError('Experimental RT relay did not confirm scheduler and first frame')

sweep_module.start_relay = start_experimental_relay
probe_module.start_relay = start_experimental_relay

EXP = Path(__file__).resolve().parent


class SendProbe(Probe):
    def __init__(self):
        super().__init__()
        target = EXP/self.folder.name
        self.folder.rename(target)
        self.folder = target
        config = dict(self.stable.config)
        config.update(name='Scope V16 Send1400 Experimental',
                      remote_app='/home/arduino/ArduinoApps/scope-v16-send1400-experimental',
                      local_app='experimentos/send1400_v16/arduino/v16/oscilloscope')
        self.candidate = Board(config)
        self.report['revision'] = 'send1400_spi38_fifo10_pointer_pipeline_v8'
        self.report['source_hashes'] = {
            str(p.relative_to(EXP)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((EXP/'arduino').rglob('*')) if p.is_file()}
        self.report['changes'] = ['Three aligned frame buffers queued by reference, no payload copy; last-fragment physical acknowledgement retains ADC node ownership',
                                  'Experimental Linux relay SCHED_FIFO priority10; stable restoration uses original launcher',
                                  'SPI requested 38 MHz',
                                  'READY userspace spin bounded to 50us before poll; fresh edge/sequence checks preserved',
                                  'MCU yields without artificial 5us busy wait while fragment is being prepared',
                                  'Timestamp and ADC range validation O3/unroll4; every sample checked',
                                  'Fixed SPI DMA configuration reused only after stopped/reset verification',
                                  'ADC8 relay boundary validation without per-byte reconstruction',
                                  'Read queued READY edge before polling; unchanged edge sequence checks']
        self.baseline_done = False

    def snapshot(self):
        # Keep the original live snapshot across setup, including a stopped MCU.
        if self.report.get("prior") is None:
            super().snapshot()

    def prepare(self):
        self.snapshot()
        self.report['backup'] = str(self.stable.backup())
        self.save()
        # Any setup failure now restores this live snapshot in the parent finally.
        self.switched = True
        # No high-rate acquisition during a Linux relay build.
        usb_stream.stop(self.stable)
        self.stable.stop()
        require_exclusive_monitor()
        if 'ESTAB' in self.stable.shell('ss','-tn','sport','=',':8766',capture=True).stdout:
            raise RuntimeError('Q has another reader')
        apps = json.loads(self.candidate.cli('app','list','--format','json',capture=True).stdout)['apps']
        if any(a.get('name')==self.candidate.config['name'] for a in apps):
            self.candidate.push_sources(self.candidate.check_sources(),self.candidate.remote)
        else:
            self.candidate.create()
        usb_stream.ROOT = EXP
        try:
            try:
                relay = usb_stream.binary(self.candidate,p992=True,audio=True)
            except subprocess.CalledProcessError:
                relay = usb_stream.binary(self.candidate,build=True,p992=True,audio=True)
        finally:
            usb_stream.ROOT = ROOT
        self.deployment['candidate_relay'] = relay
        # Dedicated network avoids the exhausted default Docker address pool.
        networks = self.stable.shell('docker','network','ls','--format','{{.Name}}',capture=True).stdout.splitlines()
        name = 'scope-v16-send1400-experimental_default'
        if name not in networks:
            self.stable.shell('docker','network','create','--subnet','10.203.141.0/24',
                              '--label','com.docker.compose.network=default',
                              '--label','com.docker.compose.project=scope-v16-send1400-experimental',name)
        self.report['experimental_network'] = {'name':name,'subnet':'10.203.141.0/24'}
        super().prepare()

    def trial(self, *args, **kwargs):
        if not self.baseline_done:
            self.baseline_done = True
            baseline = super().trial(8,131,6912,10,'baseline')
            if not baseline['ok']:
                raise RuntimeError('Optimized variant failed baseline; no higher-rate acceptance')
            kwargs['restart'] = True
        return super().trial(*args, **kwargs)


if __name__ == '__main__':
    raise SystemExit(SendProbe().run_probe())
