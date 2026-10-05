from pathlib import Path
import shutil,json
ROOT=Path(__file__).resolve().parents[2]
root=ROOT/'experimentos/tasas_spi/firmware_diagnostico';app=root/'oscilloscope'
shutil.copytree(ROOT/'arduino/v9_fast/oscilloscope',app,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
c=json.loads((ROOT/'arduino/v9_fast/unoq.json').read_text());c.update(name='Scope SPI Timing Diagnostic',remote_app='/home/arduino/ArduinoApps/scope-spi-timing-diagnostic',local_app=str(app.relative_to(ROOT)));(root/'unoq.json').write_text(json.dumps(c,indent=2)+'\n')
(app/'app.yaml').write_text('name: Scope SPI Timing Diagnostic\ndescription: "DIAGNOSTICO AISLADO | Detiene ADC al perder nodo y entrega estadisticas RAM tipo 11. No usar con monitores."\nports: []\nbricks: []\n')
header='''#pragma once
namespace timing_diag {
enum Metric { PREPARE, ARM, READY_TO_IRQ, IRQ_TO_RETURN, CHECK, HANDOFF, NODE_SEND, POLL, COPY, COUNT };
struct Stats { uint64_t cycles=0; uint32_t count=0, maximum=0; };
static Stats stats[COUNT];
static volatile uint32_t irq_cycle=0;
static uint32_t queue_max=0;
static bool frozen=false;
static inline void record(Metric metric,uint32_t start,uint32_t end=k_cycle_get_32()) {
    if(frozen) return;
    const uint32_t delta=end-start;
    auto &s=stats[metric];s.cycles+=delta;++s.count;if(delta>s.maximum)s.maximum=delta;
}
static void reset() { for(auto &s:stats)s=Stats{};queue_max=0; }
static void encode(uint8_t *p,uint32_t seq,uint32_t period,uint32_t epoch,uint32_t dropped,uint32_t fatal) {
    memset(p,0,512);memcpy(p,"SCP1",4);scope_bench::put16(p+4,2);scope_bench::put16(p+6,11);
    scope_bench::put32(p+8,seq);scope_bench::put32(p+12,492);
    scope_bench::put32(p+16,period);scope_bench::put32(p+20,epoch);
    scope_bench::put32(p+24,dropped);scope_bench::put32(p+28,fatal);scope_bench::put32(p+32,queue_max);
    scope_bench::put32(p+36,COUNT);scope_bench::put32(p+40,CONFIG_SYS_CLOCK_HW_CYCLES_PER_SEC);
    for(unsigned i=0;i<COUNT;++i) {
        const auto &s=stats[i];auto *q=p+48+i*16;
        scope_bench::put32(q,s.count);scope_bench::put32(q+4,uint32_t(s.cycles));
        scope_bench::put32(q+8,uint32_t(s.cycles>>32));scope_bench::put32(q+12,s.maximum);
    }
    scope_bench::put32(p+508,scope_bench::crc32(p,508));
}
}
'''
(app/'sketch/timing_diag.h').write_text(header)
p=app/'sketch/sketch.ino';s=p.read_text().replace('#include "benchmark_protocol.h"','#include "benchmark_protocol.h"\n#include "timing_diag.h"')
s=s.replace('completed = true;','timing_diag::irq_cycle=k_cycle_get_32();\n        completed = true;',1)
s=s.replace('static int exchange() {','static int exchange() {\n    const uint32_t diag_arm=k_cycle_get_32();')
s=s.replace('    publish_ready(true);','    const uint32_t diag_ready=k_cycle_get_32();\n    timing_diag::record(timing_diag::ARM,diag_arm,diag_ready);\n    publish_ready(true);',1)
s=s.replace('    publish_ready(false);\n    SPI3->IER = 0;','    timing_diag::record(timing_diag::READY_TO_IRQ,diag_ready,timing_diag::irq_cycle);\n    publish_ready(false);\n    SPI3->IER = 0;',1)
s=s.replace('    return result;\n}', '    timing_diag::record(timing_diag::IRQ_TO_RETURN,timing_diag::irq_cycle);\n    return result;\n}',1)
s=s.replace('        if (mode == scope_control::UART)', '        const uint32_t diag_node=k_cycle_get_32();\n        if (mode == scope_control::UART)',1)
s=s.replace('                build_samples(sample_frame, node, offset, count);','                const uint32_t diag_frame=k_cycle_get_32();\n                build_samples(sample_frame, node, offset, count);')
s=s.replace('                offset += count;', '                timing_diag::record(timing_diag::HANDOFF,diag_frame);\n                offset += count;',1)
s=s.replace('        acquisition::release();','        timing_diag::record(timing_diag::NODE_SEND,diag_node);\n        acquisition::release();',1)
s=s.replace('    scope_control::Reply reply{};\n    scope_acq::Reply config_reply{};', '''    if(acquisition::dropped_nodes || acquisition::fatal_errors || timing_diag::frozen) {
        if(!timing_diag::frozen) {
            LL_TIM_DisableCounter(TIM2);
            k_thread_abort(&acquisition::producer_thread_data);
            k_thread_abort(&output_thread_data);
            timing_diag::frozen=true;
        }
        timing_diag::encode(tx,sequence++,acquisition::period,acquisition::epoch,
                            acquisition::dropped_nodes,acquisition::fatal_errors);
        exchange();return;
    }
    scope_control::Reply reply{};
    scope_acq::Reply config_reply{};''',1)
s=s.replace('    prepare_us = elapsed_us(started);','    timing_diag::record(timing_diag::PREPARE,started);\n    prepare_us = elapsed_us(started);',1)
s=s.replace('    check_us = elapsed_us(started);','    timing_diag::record(timing_diag::CHECK,started);\n    check_us = elapsed_us(started);',1)
p.write_text(s)
p=app/'sketch/acquisition.h';s=p.read_text()
s=s.replace('        last_poll = current;', '        timing_diag::record(timing_diag::POLL,last_poll,current);\n        last_poll = current;',1)
s=s.replace('            Node &slot = queue[producer_slot];','            const uint32_t occupancy=QUEUE_SLOTS-k_sem_count_get(&empty_slots);\n            if(occupancy>timing_diag::queue_max)timing_diag::queue_max=occupancy;\n            Node &slot = queue[producer_slot];',1)
s=s.replace('            if (reserved) {\n                slot.index', '            timing_diag::record(timing_diag::COPY,copying);\n            if (reserved) {\n                slot.index',1)
s=s.replace('    bits = requested_bits; period = requested_period;', '    timing_diag::reset();\n    bits = requested_bits; period = requested_period;',1)
p.write_text(s)
