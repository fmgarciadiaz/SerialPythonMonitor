"""Read only fixed, non-destructive GENI SPI configuration registers. No writes."""
import json
import mmap
import os
import struct

REGISTERS={'serial_clock_config':0x48,'fifo_interface_disabled':0x64,
           'firmware_revision':0x68,'clock_select':0x7c,'dma_mode':0x258,
           'gsi_event_enable':0xe18,'dma_interface_enable':0xe20}


def read_config():
    result={'kind':'read_only_configuration_not_electrical_measurement',
            'spi_base':'0x04a94000','wrapper_base':'0x04ac0000'}
    with open('/clock_rate') as f:result['source_hz_before']=int(f.read())
    with open('/branch_rate') as f:result['branch_cached_hz']=int(f.read())
    fd=os.open('/dev/mem',os.O_RDONLY|os.O_SYNC)
    try:
        with mmap.mmap(fd,4096,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ,offset=0x04a94000) as page:
            result['snapshots']=[{name:struct.unpack_from('<I',page,offset)[0]
                                  for name,offset in REGISTERS.items()} for _ in range(3)]
        with mmap.mmap(fd,4096,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ,offset=0x04ac0000) as page:
            result['wrapper_version']=struct.unpack_from('<I',page,4)[0]
        with mmap.mmap(fd,4096,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ,offset=0x0141f000) as page:
            result['gcc_dfs_control']=struct.unpack_from('<I',page,0x738+0x14)[0]
    finally:os.close(fd)
    with open('/clock_rate') as f:result['source_hz_after']=int(f.read())
    return result


if __name__=='__main__':print(json.dumps(read_config(),indent=2))
