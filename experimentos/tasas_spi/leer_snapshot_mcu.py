"""Decode the RAM-only diagnostic frame from a saved relay log."""
import argparse,json,struct,zlib
from pathlib import Path
NAMES=['prepare','arm_dma','ready_to_irq','irq_to_return','check','handoff','node_send','producer_poll','producer_copy']
def decode(packet):
    if len(packet)!=512 or struct.unpack_from('<4sHH',packet)!=(b'SCP1',2,11):
        raise ValueError('Cabecera diagnóstica inválida')
    if struct.unpack_from('<I',packet,12)[0]!=492 or zlib.crc32(packet[:508])!=struct.unpack_from('<I',packet,508)[0]:
        raise ValueError('Longitud o CRC diagnóstico inválido')
    period,epoch,dropped,fatal,queue_max,count,clock=struct.unpack_from('<7I',packet,16)
    if count!=len(NAMES) or not clock or not period or queue_max>4 or any(packet[44:48]) or any(packet[48+count*16:508]):
        raise ValueError('Contenido diagnóstico inválido')
    metrics={}
    for i,name in enumerate(NAMES):
        n,total,maximum=struct.unpack_from('<IQI',packet,48+16*i)
        metrics[name]={'count':n,'mean_us':total/n/clock*1e6 if n else None,'maximum_us':maximum/clock*1e6}
    return {'period_us':period,'epoch':epoch,'dropped':dropped,'fatal':fatal,'queue_max':queue_max,'clock_hz':clock,'metrics':metrics}
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('log',type=Path);args=parser.parse_args()
    frames=[line.split(' ',1)[1] for line in args.log.read_text().splitlines() if line.startswith('MCU_SNAPSHOT ')]
    if len(frames)!=1:raise SystemExit('Se requiere exactamente una instantánea MCU')
    report=decode(bytes.fromhex(frames[0]));output=args.log.with_suffix('.mcu.json');output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
