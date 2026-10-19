"""Vectorized native payload unpacking; wire validation stays in the decoder."""
try:
    import numpy as np
except ImportError:
    np = None  # Keep stdlib diagnostic readers usable without NumPy.


class NativeRecords:
    """Array-backed sample sequence; Python rows are materialized on demand."""
    def __init__(self, array):
        self.array = array
    def __len__(self):
        return len(self.array)
    def __getitem__(self, index):
        if isinstance(index, slice):
            return NativeRecords(self.array[index])
        return tuple(int(value) for value in self.array[index])
    def __iter__(self):
        return (tuple(int(value) for value in row) for row in self.array)


def numeric_records(rows):
    if np is None or isinstance(rows, NativeRecords):
        return rows
    return NativeRecords(np.asarray(rows, dtype=np.uint64).reshape(-1, 4))


def join_records(blocks):
    return NativeRecords(np.concatenate([block.array for block in blocks])) if blocks else []


def unpack_native(payload, bits, channels, count, timestamp, period, index, numeric=False):
    if np is None:
        return None
    if bits in (8, 16):
        values = np.frombuffer(payload, dtype='u1' if bits == 8 else '<u2')
    else:
        group = 4 if bits in (10, 14) else 2
        width = group * bits // 8
        octets = np.frombuffer(payload, dtype=np.uint8).reshape(-1, width)
        words = np.zeros(len(octets), dtype=np.uint64)
        for byte in range(width):
            words |= octets[:, byte].astype(np.uint64) << (8 * byte)
        shifts = np.arange(group, dtype=np.uint64) * bits
        values = ((words[:, None] >> shifts) & ((1 << bits) - 1)).reshape(-1)
    values = values.reshape(count, channels)
    offsets = np.arange(count, dtype=np.uint64)
    timestamps = (timestamp + offsets * period) & 0xffffffff
    indices = (index + offsets) & 0xffffffff
    if numeric:
        b = values[:, 1] if channels == 2 else np.zeros(count, dtype=np.uint64)
        return NativeRecords(np.column_stack((timestamps, values[:, 0], b, indices)))
    timestamps = timestamps.tolist()
    indices = indices.tolist()
    a = values[:, 0].tolist()
    b = values[:, 1].tolist() if channels == 2 else [0] * count
    return list(zip(timestamps, a, b, indices))
