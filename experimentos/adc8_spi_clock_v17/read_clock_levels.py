"""Read fixed QCM2290 S5 clock configuration only; never writes registers."""
import json
import mmap
import os
import struct
from pathlib import Path


def read_levels():
    result = {'kind': 'read_only_qcm2290_s5_clock_levels',
              'rcg_address': '0x0141f738'}
    names = ['gcc_qupv3_wrap0_s5_clk', 'gcc_qupv3_wrap0_s5_clk_src',
             'gpll0', 'gpll0_out_aux2', 'gpll6', 'bi_tcxo']
    result['clocks'] = {}
    for name in names:
        entry = {}
        for field in ['clk_rate', 'clk_parent', 'clk_possible_parents', 'clk_flags']:
            p = Path('/clocks') / name / field
            if p.exists():
                entry[field] = p.read_text().strip()
        result['clocks'][name] = entry
    fd = os.open('/dev/mem', os.O_RDONLY | os.O_SYNC)
    try:
        with mmap.mmap(fd, 4096, flags=mmap.MAP_SHARED,
                       prot=mmap.PROT_READ, offset=0x0141f000) as page:
            def reg(offset):
                return struct.unpack_from('<I', page, 0x738 + offset)[0]
            result['snapshots'] = [
                {'cmd': reg(0), 'cfg': reg(4), 'm': reg(8), 'n': reg(12),
                 'dfs_control': reg(0x14),
                 'levels': [{'cfg': reg(0x1c + 4*i),
                             'm': reg(0x5c + 4*i),
                             'n': reg(0x9c + 4*i)} for i in range(8)]}
                for _ in range(3)]
    finally:
        os.close(fd)
    return result


if __name__ == '__main__':
    print(json.dumps(read_levels(), indent=2))
