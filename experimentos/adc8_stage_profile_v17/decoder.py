"""Read experimental timing slots only after the full integrity decoder accepts."""
import struct
from experimentos.maxfreq_v16.contract import Decoder as IntegrityDecoder

NAMES = ('cache', 'validate_copy', 'pack', 'build_frame', 'frame_free_wait',
         'seal', 'exchange_setup', 'ready_to_done', 'exchange_cleanup', 'rx_check', 'probe')


class ProfileDecoder(IntegrityDecoder):
    latest = None

    def __init__(self):
        super().__init__()
        self.profile_buffer = bytearray()
        self.reset_profile()
        ProfileDecoder.latest = self

    def reset_profile(self):
        self.part = {}
        self.previous = {}
        self.timing_profile = {}

    def reset_metrics(self):
        super().reset_metrics()
        self.reset_profile()

    def feed(self, data):
        self.profile_buffer.extend(data)
        while len(self.profile_buffer) >= 992:
            packet = bytes(self.profile_buffer[:992])
            del self.profile_buffer[:992]
            super().feed(packet)
            if struct.unpack_from('<H', packet, 6)[0] != 20:
                continue
            tag, value = struct.unpack_from('<II', packet, 40)
            if tag >> 16 != 0xd17a:
                continue
            metric, field = divmod(tag & 65535, 3)
            if metric >= len(NAMES):
                raise ValueError('Unknown profile metric')
            if field == 0:
                self.part[metric] = [value]
            elif metric in self.part and len(self.part[metric]) == field:
                self.part[metric].append(value)
                if field == 2:
                    count, total, maximum = self.part.pop(metric)
                    old = self.previous.get(metric)
                    self.previous[metric] = (count, total)
                    if old is not None:
                        dc, ds = (count-old[0]) & 0xffffffff, (total-old[1]) & 0xffffffff
                        if dc:
                            row = self.timing_profile.setdefault(NAMES[metric], dict(count=0, sum_ticks=0, maximum_since_boot_ticks=0))
                            row['count'] += dc
                            row['sum_ticks'] += ds
                            row['maximum_since_boot_ticks'] = max(row['maximum_since_boot_ticks'], maximum)

    def summary(self):
        return {name: dict(row, mean_us=row['sum_ticks']/160/row['count'],
                           maximum_since_boot_us=row['maximum_since_boot_ticks']/160)
                for name, row in self.timing_profile.items()}
