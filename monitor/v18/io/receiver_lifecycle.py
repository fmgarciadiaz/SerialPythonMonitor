"""Read-only baseline and exact restoration for the functional receiver owner."""
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from monitor.v18.io.device_snapshot import DeviceIdentity, DeviceSnapshot, Observation
from monitor.v18.receiver.unoq_switch import Mode, Phase
from monitor.v18.receiver.unoq_wav import State


class ReceiverLifecycle:
    def __init__(self, receiver, identity, snapshot_dir=None):
        self.receiver = receiver
        self.identity = DeviceIdentity(**identity)
        self.snapshot = None
        self.snapshot_dir = (Path(snapshot_dir) if snapshot_dir is not None else
            Path(__file__).resolve().parents[3] / 'diagnosticos/resultados_v18/sessions')
        self.path = None

    def _query(self):
        receiver = self.receiver
        deadline = time.monotonic() + 3
        while receiver.decoder.config is None or receiver.decoder.mode is None:
            receiver.pump()
            if time.monotonic() >= deadline:
                raise TimeoutError('Sin perfil ADC y transporte inicial confirmados')
        receiver.wav_request()
        while receiver.wav_pending:
            receiver.pump()
            if time.monotonic() >= deadline:
                raise TimeoutError('Sin estado WAV inicial confirmado')
        reply = receiver.generator()
        if reply.phase != Phase.APPLIED:
            raise RuntimeError('Consulta del generador rechazada; no se acepta snapshot')
        if receiver.wav_status is None:
            raise RuntimeError('No se recibió el estado WAV')
        return Observation(self.identity, receiver.decoder.config, reply.active,
                           reply.running, receiver.wav_status.state,
                           receiver.decoder.mode)

    def capture(self):
        observed = self._query()
        self.snapshot = DeviceSnapshot.capture(observed)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
        self.path = self.snapshot_dir / f'session_{stamp}.json'
        self.path.write_text(json.dumps(dict(snapshot=self.snapshot.to_dict(),
            state='captured', hardware_restored=False), indent=2) + '\n')
        return self.snapshot

    def restore(self, recovery_seconds=10):
        """Call while the child still owns connection/lock; cancellation disabled."""
        result = dict(hardware_restored=False, errors=[], recovery=None)
        receiver = self.receiver
        if self.snapshot is None:
            return result
        old_samples, old_generator = receiver.on_samples, receiver.on_generator
        old_config, old_wav = receiver.on_configuration, receiver.on_wav
        receiver.on_samples = lambda samples: None
        receiver.on_generator = lambda reply: None
        receiver.on_configuration = lambda config: None
        receiver.on_wav = lambda status: None
        try:
            receiver.running = lambda: True
            receiver.reset_wav_output()
            # Stop active generator before any profile restoration.
            active = receiver.generator()
            if active.running or active.active.enabled:
                receiver.generator(replace(active.active, enabled=0))
            receiver.select(Mode.SPI)
            receiver.configure(self.snapshot.acquisition)
            receiver.generator(self.snapshot.generator)
            if not self.snapshot.matches(self._query()):
                raise RuntimeError('Lectura final distinta del snapshot inicial')
            samples = 0
            def count(records):
                nonlocal samples
                samples += len(records)
            receiver.on_samples = count
            started = time.monotonic()
            required = int(self.snapshot.acquisition.actual_rate * recovery_seconds)
            # The TCP buffer may be partly full at either wall-clock edge.
            # Require both the requested wall time and continuous RF duration;
            # do not misclassify that bounded edge skew as missing ADC data.
            while samples < required or time.monotonic() - started < recovery_seconds:
                receiver.pump()
                if time.monotonic() - started > recovery_seconds + 2:
                    raise RuntimeError('Recuperación sin cantidad suficiente de muestras')
            elapsed = time.monotonic() - started
            result['recovery'] = dict(seconds=elapsed, samples=samples, required=required)
            status = receiver.decoder.status or {}
            if status.get('dropped') != 0 or status.get('fatal') != 0:
                raise RuntimeError('Recuperación con errores de adquisición')
            if not self.snapshot.matches(self._query()):
                raise RuntimeError('El estado cambió durante la recuperación')
            result.update(hardware_restored=True, recovery=dict(seconds=elapsed,
                samples=samples, dropped=0, fatal=0, continuous=True))
        except Exception as exc:
            result['errors'].append(f'{type(exc).__name__}: {exc}')
        finally:
            receiver.on_samples, receiver.on_generator = old_samples, old_generator
            receiver.on_configuration, receiver.on_wav = old_config, old_wav
            if self.path is not None:
                self.path.write_text(json.dumps(dict(snapshot=self.snapshot.to_dict(),
                    state='closed', **result), indent=2) + '\n')
        return result

    def finalize(self, result):
        """Persist the complete outcome after transport/identity cleanup."""
        if self.path is not None and self.snapshot is not None:
            self.path.write_text(json.dumps(dict(snapshot=self.snapshot.to_dict(),
                state='closed', **result), indent=2) + '\n')
