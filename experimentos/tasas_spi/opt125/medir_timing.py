"""Measure the RAM-only timing variant and request its frozen snapshot after capture."""
import argparse,importlib,json,struct,sys,time,zlib,subprocess
from datetime import datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(ROOT))
NAMES=['prepare','arm_dma','ready_to_irq','irq_to_return','check','handoff','node_send','producer_poll','producer_copy']
def decode_snapshot(packet):
    block=len(packet);version=2 if block==512 else 3
    if block not in (512,992) or struct.unpack_from('<4sHH',packet)!=(b'SCP1',version,11) or struct.unpack_from('<I',packet,12)[0]!=block-20 or zlib.crc32(packet[:-4])!=struct.unpack_from('<I',packet,block-4)[0]:raise ValueError('Snapshot invalido')
    period,epoch,dropped,fatal,peak,n,clock=struct.unpack_from('<7I',packet,16)
    if n!=len(NAMES) or not clock or peak>4:raise ValueError('Metricas invalidas')
    metrics={}
    for i,name in enumerate(NAMES):
        count,total,maximum=struct.unpack_from('<IQI',packet,48+i*16)
        metrics[name]={'count':count,'mean_us':total/count/clock*1e6 if count else None,'max_us':maximum/clock*1e6}
    if packet[192:196]!=b'QTR1':raise ValueError('Sin historia de cola')
    total,first_n,last_n=struct.unpack_from('<3I',packet,196)
    if first_n!=min(total,64) or last_n!=min(total,64) or not total:raise ValueError('Historia de cola invalida')
    first=list(packet[208:208+first_n]);last=list(packet[272:272+last_n])
    if any(x>4 for x in first+last) or any(packet[336:block-4]):raise ValueError('Padding o ocupacion invalidos')
    first_mean=sum(first)/len(first);last_mean=sum(last)/len(last)
    return {'period_us':period,'epoch':epoch,'dropped':dropped,'fatal':fatal,'queue_peak':peak,'queue_nodes':total,'queue_first':first,'queue_last':last,'queue_first_mean':first_mean,'queue_last_mean':last_mean,'queue_no_growth':last_mean<=first_mean+.5,'metrics':metrics}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=('p512','p992'),required=True);parser.add_argument('--seconds',type=float,default=5);parser.add_argument('--rate',type=int,default=125000);parser.add_argument('--generator',choices=('off','on'),default='off');args=parser.parse_args()
    if args.seconds<=0:parser.error('seconds must be positive')
    package='experimentos.tasas_spi.opt125.'+args.variant+'.receiver'
    def module(name):return importlib.import_module(package+'.'+name)
    block=module('unoq_usb').BLOCK;version=2 if block==512 else 3
    folder=HERE/'resultados'/datetime.now().strftime('%Y%m%d_%H%M%S_%f');folder.mkdir(parents=True)
    report={'variant':args.variant+'_timing','rate':args.rate,'generator':args.generator,'passed':False,'errors':[]};count=0
    try:
        with module('unoq_usb').Connection('1060031107') as c:
            c.socket.settimeout(.1);r=module('unoq_config_receiver').OutputReceiver(c,lambda samples:None)
            try:
                G=module('unoq_generator').GeneratorConfig
                r.generator(G(0,int(args.generator=='on'),0,2500,2500,0,4095,1000))
                r.configure(module('unoq_acquisition').Configuration(14,args.rate))
                def consume(samples):
                    nonlocal count
                    count+=len(samples)
                r.on_samples=consume;started=time.monotonic()
                try:
                    while time.monotonic()-started<args.seconds:r.pump()
                    packet=bytearray(block);struct.pack_into('<4sHHII',packet,0,b'SCP1',version,12,0x80000123,block-20);struct.pack_into('<I',packet,block-4,zlib.crc32(packet[:-4]));c.socket.sendall(packet)
                    # The relay emits the snapshot to its log and closes the PC.
                    until=time.monotonic()+3
                    while time.monotonic()<until:
                        if not c.socket.recv(65536):break
                except Exception as exc:report['errors'].append(str(exc))
                report.update(pairs=count,elapsed_s=time.monotonic()-started,status=r.decoder.status)
            finally:r.close()
    except Exception as exc:report['errors'].append(str(exc))
    from hardware import board_for
    b=board_for(args.variant+'_timing')
    result=subprocess.run([b.adb,'-s',b.serial,'shell','docker','logs',b.config['container']],check=True,text=True,capture_output=True)
    log=result.stdout+result.stderr
    (folder/'relay.log').write_text(log)
    frames=[line.split(' ',1)[1] for line in log.splitlines() if line.startswith('MCU_SNAPSHOT ')]
    try:
        if len(frames)!=1:raise ValueError('Sin instantanea unica')
        snapshot=decode_snapshot(bytes.fromhex(frames[0]));report['snapshot']=snapshot
        if snapshot['period_us']!=1000000//args.rate or snapshot['epoch']!=report.get('status',{}).get('epoch'):raise ValueError('Perfil/epoca snapshot no coincide')
        if snapshot['queue_nodes']<128 or snapshot['metrics']['node_send']['count']<128:raise ValueError('Menos de 128 nodos: historia de cola insuficiente')
        report['passed']=not report['errors'] and not snapshot['dropped'] and not snapshot['fatal'] and snapshot['queue_no_growth'] and snapshot['metrics']['node_send']['mean_us'] is not None and snapshot['metrics']['node_send']['mean_us']<=2048*snapshot['period_us']*.9
    except Exception as exc:report['errors'].append(str(exc))
    (folder/'informe.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);print(folder)
    return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
