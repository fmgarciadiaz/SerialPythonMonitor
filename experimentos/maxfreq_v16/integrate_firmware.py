"""Extend the legacy firmware; run once after incorporate.py passes its evidence gate."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
EXP = Path(__file__).resolve().parent
SKETCH = ROOT/'arduino/historico/v16/oscilloscope/sketch'


def main():
    if not (SKETCH/'native_profiles.h').exists():
        raise RuntimeError('Run the physical acceptance gate first')
    backup = EXP/'production_before_native'
    if backup.exists():
        raise RuntimeError('Integration already prepared; inspect existing files')
    shutil.copytree(SKETCH, backup/'sketch')
    shutil.copytree(ROOT/'arduino/historico/v16/relay', backup/'relay')
    p = SKETCH/'acquisition.h'; s = p.read_text()
    s = s.replace('#include "node_validation.h"', '#include "node_validation.h"\n#include "native_profiles.h"')
    s = s.replace('static bool single() { return (period == 267U || period == 242U || period == 133U); }', '''static const ScopeNativeProfile *native_profile = nullptr;
static bool native() { return native_profile != nullptr; }
static bool single() { return native() ? native_profile->channels==1 : (period==267U || period==242U || period==133U); }
static bool fast_clock() { return native() || single(); }''')
    s = s.replace('return period==133U?3584U:DMA_NODE_PAIRS;', 'return native()?native_profile->node_pairs:period==133U?3584U:DMA_NODE_PAIRS;')
    s = s.replace('node_pairs()*period/(single()?160U:1U)', 'node_pairs()*period/(fast_clock()?160U:1U)')
    s = s.replace('dmaBuffer[DMA_BUFFER_RESULTS]', 'dmaBuffer[SCOPE_NATIVE_MAX_RESULTS * DMA_NODE_COUNT]')
    s = s.replace('timestampBuffer[3584U * DMA_NODE_COUNT]', 'timestampBuffer[SCOPE_NATIVE_MAX_NODE * DMA_NODE_COUNT]')
    s = s.replace('const uint32_t sampling = bits != 16', 'const uint32_t sampling = native() ? LL_ADC_SAMPLINGTIME_5CYCLES : bits != 16')
    s = s.replace('single()?0U:TIM5_PRESCALER', 'fast_clock()?0U:TIM5_PRESCALER').replace('single()?0U:TIM2_PRESCALER', 'fast_clock()?0U:TIM2_PRESCALER')
    s = s.replace('struct Node { uint32_t index; uint32_t timestamp; ChannelPair samples[3584U]; };', '''struct SingleSample { uint16_t ch1; };
struct Node { uint32_t index; uint32_t timestamp;
    union { ChannelPair samples[SCOPE_NATIVE_MAX_DUAL]; SingleSample single_samples[SCOPE_NATIVE_MAX_SINGLE]; };
};''')
    metrics = '''static volatile uint32_t queue_peak=0,copy_max=0,poll_max=0,slack_min=0xffffffffU,send_previous=0,produced=0;
static uint32_t consumer_started=0;
'''
    s = s.replace('static void fail() {', metrics+'static void fail() {')
    s = s.replace('        last_poll = current;', '        if(native()) poll_max=max(uint32_t(poll_max),uint32_t(current-last_poll));\n        last_poll = current;')
    s = s.replace('            if (reserved) slot.timestamp', '            if(native()) queue_peak=max(uint32_t(queue_peak),uint32_t(QUEUE_SLOTS-k_sem_count_get(&empty_slots)));\n            if (reserved) slot.timestamp')
    s = s.replace('            if(single()) valid = reserved', '''            if(native() && single()) valid = reserved
                ? scope_validation::validate_node<true,true>(adc,timestamps,node_pairs(),bits,period,have_timestamp,previous_timestamp,slot.single_samples)
                : scope_validation::validate_node<false,true>(adc,timestamps,node_pairs(),bits,period,have_timestamp,previous_timestamp,slot.single_samples);
            else if(single()) valid = reserved''')
    s = s.replace('            if (!valid) {', '''            if(native()) {
                copy_max=max(uint32_t(copy_max),uint32_t(k_cycle_get_32()-copying));
                const int32_t slack=int32_t(timestamps[0]+2U*node_pairs()*period-TIM5->CNT);
                slack_min=min(uint32_t(slack_min),slack>0?uint32_t(slack):0U);
                valid=valid && slack>0;
                ++produced;
            }
            if (!valid) {''')
    s = s.replace('return k_sem_take(&full_slots, K_MSEC(100)) == 0 ? &queue[consumer_slot] : nullptr;', '''if(k_sem_take(&full_slots,K_MSEC(100))!=0) return nullptr;
    if(native()) consumer_started=k_cycle_get_32();
    return &queue[consumer_slot];''')
    s = s.replace('static void release() {', 'static void release() {\n    if(native()) send_previous=k_cycle_get_32()-consumer_started;')
    s = s.replace('    dropped_nodes = fatal_errors = 0;', '    dropped_nodes = fatal_errors = 0;\n    queue_peak=copy_max=poll_max=send_previous=produced=0;slack_min=0xffffffffU;')
    s = s.replace('bits = requested_bits; period = requested_period;', '''bits = requested_bits;
    native_profile=scope_native_find(bits,requested_period);
    period=native()?native_profile->ticks:requested_period;''')
    p.write_text(s)
    p = SKETCH/'node_validation.h'; s = p.read_text().replace('if constexpr (Copy) output[i] = {a, b};', 'if constexpr (Copy) { if constexpr (Single) { output[i] = {}; output[i].ch1 = a; } else output[i] = {a,b}; }'); p.write_text(s)
    p = SKETCH/'acquisition_protocol.h'; s = p.read_text().replace('#include "control_protocol.h"', '#include "control_protocol.h"\n#include "native_profiles.h"').replace('    if(period==133)', '    if(scope_native_find(bits,period)) return true;\n    if(period==133)'); p.write_text(s)
    p = SKETCH/'sketch.ino'; s = p.read_text()
    source = (EXP/'arduino/historico/v16/oscilloscope/sketch/sketch.ino').read_text()
    begin = source.index('static void build_samples('); end = source.index('\nstatic void output_worker', begin)
    native = source[begin:end].replace('build_samples(', 'build_native_samples(', 1).replace('node->samples+offset', 'node->single_samples+offset')
    # Native dual packing is added only after its independent physical campaign.
    attribute = '#if defined(__GNUC__) && !defined(__clang__)\n__attribute__((optimize("O2")))\n#endif\n'
    s = s.replace(attribute+'static void build_samples(', '#include "sample_packing.h"\n'+attribute+native+'\n'+attribute+'static void build_samples(',1)
    s = s.replace('    const bool mega=acquisition::period==133U;', '    if(acquisition::native()) { build_native_samples(frame,node,offset,count); return; }\n    const bool mega=acquisition::period==133U;',1)
    s = s.replace('const unsigned count = min(acquisition::period==133U?', 'const unsigned count = min(acquisition::native()?(acquisition::bits==8?864U:acquisition::bits==10?696U:496U):acquisition::period==133U?')
    s = s.replace('if (acquisition::period==133U && acquisition::threads_started', 'if ((acquisition::native() || acquisition::period==133U) && acquisition::threads_started')
    s = s.replace('put16(tx + 6, acquisition::period==133U?', 'put16(tx + 6, acquisition::native()?20:acquisition::period==133U?')
    s = s.replace('(acquisition::single() || acquisition::period < 32)', '(acquisition::native() || acquisition::single() || acquisition::period < 32)')
    p.write_text(s)


    p = ROOT/'arduino/historico/v16/relay/config_relay_protocol.h'; s = p.read_text()
    s = s.replace('#pragma once', '#pragma once\n#include "native_profiles.h"',1)
    s = s.replace('    if(period==133)', '    if(scope_native_find(bits,period)) return true;\n    if(period==133)',1)
    source = (EXP/'arduino/historico/v16/relay/config_relay_protocol.h').read_text()
    begin = source.index('    const uint32_t ticks=d->period')
    end = source.index('\n}\nstatic bool dual_command',begin)
    body = source[begin:end]
    body = body.replace('n=d->period>>16', 'n=(d->period>>16)&32767U')
    body = body.replace('p[67]!=1', 'p[67]!=native->channels')
    body = body.replace('unsigned count=get16(p+64),limit=d->bits==8?864U:d->bits==10?696U:496U;',
                        'unsigned count=get16(p+64),limit=(872U*8U/(d->bits*native->channels))&~3U;')
    body = body.replace('(count*d->bits+7)/8','count*d->bits*native->channels/8')
    body = body.replace('        while(available<d->bits)', '        for(unsigned channel=0;channel<native->channels;++channel) {\n        while(available<d->bits)')
    body = body.replace('        uint32_t timestamp=', '        if(value>((1U<<d->bits)-1U)) return false;\n        }\n        uint32_t timestamp=')
    body = body.replace('        if(value>((1U<<d->bits)-1U)) return false;\n        if(d->adc.have_sample', '        if(d->adc.have_sample')
    function = 'static bool native_feed(DualChecker *d,const uint8_t *p,const ScopeNativeProfile *native) {\n    unsigned kind=get16(p+6);\n'+body+'\n}\n'
    s = s.replace('static bool dual_feed(', function+'static bool dual_feed(',1)
    s = s.replace('    const bool mega=kind==19;', '    const ScopeNativeProfile *native=scope_native_find(d->bits,d->period);\n    if(kind==20) return native && native_feed(d,p,native);\n    if(native) return false;\n    const bool mega=kind==19;',1)
    p.write_text(s)


if __name__ == '__main__':
    main()
