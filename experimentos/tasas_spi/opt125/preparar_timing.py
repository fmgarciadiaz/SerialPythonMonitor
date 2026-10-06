"""Derive RAM-only diagnostic variants from opt125 without changing normal variants."""
import argparse,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def prepare(variant):
    base=HERE/variant;target=HERE/(variant+'_timing')
    template=(ROOT/'experimentos/tasas_spi/preparar_firmware_diagnostico.py').read_text()
    template=template.replace('ROOT=Path(__file__).resolve().parents[2]',f'ROOT=Path({str(ROOT)!r})')
    template=template.replace("root=ROOT/'experimentos/tasas_spi/firmware_diagnostico'",f'root=Path({str(target)!r})')
    template=template.replace("ROOT/'arduino/historico/v9_fast/oscilloscope'",f'Path({str(base/"oscilloscope")!r})')
    template=template.replace("ROOT/'arduino/historico/v9_fast/unoq.json'",f'Path({str(base/"unoq.json")!r})')
    name='Scope Opt125 '+variant.upper()+' Timing';remote='/home/arduino/ArduinoApps/scope-opt125-'+variant+'-timing'
    template=template.replace('Scope SPI Timing Diagnostic',name).replace('/home/arduino/ArduinoApps/scope-spi-timing-diagnostic',remote)
    exec(compile(template,'diagnostic-template','exec'),{'__file__':str(__file__)})
    config=json.loads((target/'unoq.json').read_text());config['container']='serialmonitor-opt125-'+variant+'-timing';(target/'unoq.json').write_text(json.dumps(config,indent=2)+'\n')
    header=target/'oscilloscope/sketch/timing_diag.h';s=header.read_text()
    s=s.replace('memset(p,0,512)','memset(p,0,scope_bench::BLOCK_BYTES)').replace('put16(p+4,2)','put16(p+4,scope_bench::VERSION)').replace('put32(p+12,492)','put32(p+12,scope_bench::PAYLOAD_BYTES)').replace('put32(p+508,scope_bench::crc32(p,508))','put32(p+scope_bench::BLOCK_BYTES-4,scope_bench::crc32(p,scope_bench::BLOCK_BYTES-4))')
    s=s.replace('static uint32_t queue_max=0;', 'static uint32_t queue_max=0, queue_count=0;\nstatic uint8_t queue_first[64]{},queue_last[64]{};\nstatic void observe_queue(uint32_t used) { if(queue_count<64)queue_first[queue_count]=used;queue_last[queue_count%64]=used;++queue_count; }')
    s=s.replace('queue_max=0; }','queue_max=queue_count=0;memset(queue_first,0,64);memset(queue_last,0,64); }')
    s=s.replace('    scope_bench::put32(p+scope_bench::BLOCK_BYTES-4,', '''    memcpy(p+192,"QTR1",4);scope_bench::put32(p+196,queue_count);
    scope_bench::put32(p+200,queue_count<64?queue_count:64);scope_bench::put32(p+204,queue_count<64?queue_count:64);
    memcpy(p+208,queue_first,64);memcpy(p+272,queue_last,64);
    scope_bench::put32(p+scope_bench::BLOCK_BYTES-4,''')
    header.write_text(s)
    acquisition=target/'oscilloscope/sketch/acquisition.h'
    text=acquisition.read_text().replace('if(occupancy>timing_diag::queue_max)', 'timing_diag::observe_queue(occupancy);\n            if(occupancy>timing_diag::queue_max)')
    acquisition.write_text(text)
    sketch=target/'oscilloscope/sketch/sketch.ino';s=sketch.read_text()
    s=s.replace('else if (valid_ping(rx)) last_ping', '''else if(!memcmp(rx,"SCP1",4) && get32(rx+8)>=0x80000000U && get32(rx+8)!=0xffffffffU && get16(rx+6)==12 && get16(rx+4)==VERSION && get32(rx+12)==PAYLOAD_BYTES &&
            get32(rx+BLOCK_BYTES-4)==crc32(rx,BLOCK_BYTES-4)) {
        bool padding_ok=true;for(unsigned i=16;i<BLOCK_BYTES-4;++i)if(rx[i])padding_ok=false;
        if(padding_ok) {
            LL_TIM_DisableCounter(TIM2);
            k_thread_abort(&acquisition::producer_thread_data);
            k_thread_abort(&output_thread_data);
            timing_diag::frozen=true;
        } else ++bad_ping;
    } else if (valid_ping(rx)) last_ping''')
    sketch.write_text(s)
    # Diagnostic relay extracts type 11 only after normal capture has stopped.
    relay=target/'relay';relay.mkdir(exist_ok=True)
    for p in (base/'relay').glob('*.[ch]'):(relay/p.name).write_bytes(p.read_bytes())
    p=relay/'unoq_config_stream.c';s=p.read_text()
    s=s.replace('DualChecker before=checker;', '''if(get16(rx+6)==11) {
            if(crc32(rx,BLOCK-4)!=get32(rx+BLOCK-4))goto done;
            fprintf(stderr,"MCU_SNAPSHOT ");for(unsigned i=0;i<BLOCK;++i)fprintf(stderr,"%02x",rx[i]);
            fputc('\\n',stderr);goto done;
        }
        DualChecker before=checker;''')
    s=s.replace('            goto done;\n        }\n        previous_tx=', '            if(get32(rx+56) && !get32(rx+60)) { ++command;continue; }\n            goto done;\n        }\n        previous_tx=',1)
    s=s.replace('if (!dual_command(pc_command)) {','if (!(get16(pc_command+6)==12 && get16(pc_command+4)==VERSION && get32(pc_command+12)==PAYLOAD && get32(pc_command+BLOCK-4)==crc32(pc_command,BLOCK-4)) && !dual_command(pc_command)) {')
    p.write_text(s)
    print(target)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('variant',choices=('p512','p992'));prepare(p.parse_args().variant)
