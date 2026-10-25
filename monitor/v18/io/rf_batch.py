"""Compact RF delivery: wire-width arrays cross IPC, voltages stay in the host."""
from dataclasses import dataclass
import time
import numpy as np
from monitor.v18.numeric_batch import NumericBatch


def should_compact_adc8_ipc(acquisition, enabled=None):
    if enabled is None:
        enabled = bool((getattr(acquisition, '_native', None) or {}).get('compact_adc8_ipc', False))
    return bool(enabled and acquisition.bits == 8 and acquisition.channels == 1)


def take_rf_prefix(chunks,maximum):
    """Split references before concatenating: never copy an entire RF backlog."""
    if maximum<1:raise ValueError('Positive RF batch limit required')
    prefix=[];remaining=[];count=0
    for chunk in chunks:
        take=min(len(chunk),maximum-count)
        if take:
            prefix.append(chunk[:take]);count+=take
        if take<len(chunk):remaining.append(chunk[take:])
    return prefix,remaining,count

@dataclass
class RawRfBatch:
    samples: np.ndarray
    acquisition: object
    receiver_generation: int
    receiver_batch_id: int
    published_at: float

    def __len__(self):
        return len(self.samples)

    def materialize(self, clock):
        batch = NumericBatch(self.samples, self.acquisition.maximum, clock,
                             self.acquisition.channels)
        batch.acquisition = self.acquisition
        batch.receiver_generation = self.receiver_generation
        batch.receiver_batch_id = self.receiver_batch_id
        batch.published_at = self.published_at
        return batch


@dataclass
class CompactAdc8RfBatch:
    """ADC8 CH1 samples across IPC; timestamp/index are arithmetic sequences.

    The RF decoder has already checked value range and sample continuity.
    This transport only checks the profile and record layout, avoiding a second
    full scan of the batch on the receiver's critical path.
    """
    values: np.ndarray
    first_timestamp: int
    first_index: int
    period: int
    acquisition: object
    receiver_generation: int
    receiver_batch_id: int
    published_at: float

    @classmethod
    def from_records(cls, records, acquisition, generation, batch_id, published_at):
        if (getattr(acquisition, 'bits', None) != 8 or
                getattr(acquisition, 'channels', None) != 1 or
                getattr(acquisition, 'maximum', None) != 255):
            raise ValueError('Compact RF IPC requires ADC8 CH1')
        period = acquisition.period
        if not isinstance(period, int) or not 0 < period <= 0xffffffff:
            raise ValueError('Invalid compact RF IPC period')
        if not isinstance(records, np.ndarray) or records.dtype != np.uint32 or records.ndim != 2 or records.shape[1] != 4 or not len(records):
            raise ValueError('Invalid compact RF IPC records')
        return cls(records[:, 1].astype(np.uint8, copy=True),
                   int(records[0, 0]), int(records[0, 3]), period,
                   acquisition, generation, batch_id, published_at)

    def __len__(self):
        return len(self.values)

    def materialize(self, clock):
        if self.values.dtype != np.uint8 or self.values.ndim != 1 or not self.values.flags.c_contiguous:
            raise ValueError('Invalid compact RF IPC values')
        offsets = np.arange(len(self.values), dtype=np.uint32)
        records = np.zeros((len(self.values), 4), dtype=np.uint32)
        records[:, 0] = self.first_timestamp + offsets * self.period
        records[:, 1] = self.values
        records[:, 3] = self.first_index + offsets
        return RawRfBatch(records, self.acquisition, self.receiver_generation,
                          self.receiver_batch_id, self.published_at).materialize(clock)
