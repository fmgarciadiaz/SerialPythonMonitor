#pragma once
#include "generator_protocol.h"
#include <math.h>
#include "generator_timing.h"
#ifndef GENERATOR_TEST
#include "generator_dma.h"
#endif
// Hardware TIM6 + GPDMA4 clock the waveform. k_timer only supervises sweeps/pulses/errors.
namespace generator {
static_assert(CONFIG_SYS_CLOCK_TICKS_PER_SEC % scope_gen::CONTROL_HZ == 0, "Generator tick rate");
static k_timer timer;
static scope_gen::Config active=scope_gen::defaults();
static scope_gen::Request last{};
static bool have_last=false, running=false, faulted=false;
static uint8_t last_reason=scope_control::OK;
static uint32_t steps=0;
static int64_t started_tick=0;
static unsigned current_position=0, points=256;
static Timing timings[129];
static uint32_t samples[256] __attribute__((aligned(32)));
static const uint16_t sine[256]={32768,33572,34375,35178,35979,36779,37575,38369,39160,39947,40729,41507,42279,43046,43807,44560,45307,46046,46777,47500,48214,48919,49613,50298,50972,51635,52287,52927,53555,54170,54773,55362,55938,56499,57047,57579,58097,58600,59087,59558,60013,60451,60873,61278,61666,62036,62389,62724,63041,63339,63620,63881,64124,64348,64553,64739,64905,65053,65180,65289,65377,65446,65496,65525,65535,65525,65496,65446,65377,65289,65180,65053,64905,64739,64553,64348,64124,63881,63620,63339,63041,62724,62389,62036,61666,61278,60873,60451,60013,59558,59087,58600,58097,57579,57047,56499,55938,55362,54773,54170,53555,52927,52287,51635,50972,50298,49613,48919,48214,47500,46777,46046,45307,44560,43807,43046,42279,41507,40729,39947,39160,38369,37575,36779,35979,35178,34375,33572,32768,31963,31160,30357,29556,28756,27960,27166,26375,25588,24806,24028,23256,22489,21728,20975,20228,19489,18758,18035,17321,16616,15922,15237,14563,13900,13248,12608,11980,11365,10762,10173,9597,9036,8488,7956,7438,6935,6448,5977,5522,5084,4662,4257,3869,3499,3146,2811,2494,2196,1915,1654,1411,1187,982,796,630,482,355,246,158,89,39,10,0,10,39,89,158,246,355,482,630,796,982,1187,1411,1654,1915,2196,2494,2811,3146,3499,3869,4257,4662,5084,5522,5977,6448,6935,7438,7956,8488,9036,9597,10173,10762,11365,11980,12608,13248,13900,14563,15237,15922,16616,17321,18035,18758,19489,20228,20975,21728,22489,23256,24028,24806,25588,26375,27166,27960,28756,29556,30357,31160,31963};
static uint16_t value(uint8_t wave,uint32_t ph,uint16_t low,uint16_t high) {
    uint32_t unit=0;
    if(wave==0) unit=ph<0x80000000U?65535:0;
    else if(wave==1) unit=sine[ph>>24];
    else if(wave==2) unit=ph<0x80000000U?ph>>15:(0xffffffffU-ph)>>15;
    else if(wave==3) unit=ph>>16;
    else unit=65535;
    return low+uint16_t((uint32_t(high-low)*unit+32767)/65535);
}
static void tick(k_timer *) {
    if(!running) return;
    if(!generator_hw::healthy()) {
        faulted=true;running=false;generator_hw::stop(0);return;
    }
    if(!active.mode && active.wave!=4) return;
    const uint64_t elapsed=uint64_t(k_uptime_ticks()-started_tick);
    if(elapsed>=steps) {
        running=false;faulted=!generator_hw::stop(active.low);return;
    }
    if(active.mode) {
        const unsigned position=unsigned(elapsed*128/steps);
        if(position!=current_position) {
            generator_hw::set_timing(timings[position]);current_position=position;
        }
    }
}
static bool apply(const scope_gen::Config &c) {
    // Floating-point chirp preparation happens outside IRQ; DMA reads immutable RAM.
    Timing prepared[129];
    const unsigned prepared_points=points_for(c);
    for(unsigned i=0;i<=128;++i) {
        double f=c.frequency;
        if(c.mode==1) f+=(double(c.final_frequency)-c.frequency)*i/128;
        else if(c.mode==2) f*=pow(double(c.final_frequency)/c.frequency,double(i)/128);
        prepared[i]=timing(uint32_t(f+0.5),prepared_points);
    }
    const unsigned key=irq_lock();
    running=false;
    if(!generator_hw::stop(0)) {faulted=true;irq_unlock(key);return false;}
    points=prepared_points;
    for(unsigned i=0;i<points;++i)
        samples[i]=value(c.wave,uint32_t((uint64_t(i)<<32)/points),c.low,c.high);
    bool ok=true;
    if(c.enabled) {
        if(c.wave==4) ok=generator_hw::stop(c.high);
        else ok=generator_hw::start(samples,points,prepared[0]);
    }
    if(ok) {
        active=c;memcpy(timings,prepared,sizeof(timings));current_position=0;
        steps=uint32_t(uint64_t(c.duration)*CONFIG_SYS_CLOCK_TICKS_PER_SEC/1000);
        started_tick=k_uptime_ticks();running=c.enabled;
    }
    faulted=!ok;irq_unlock(key);return ok;
}
static scope_gen::Reply reply(uint32_t id,uint8_t status,uint8_t reason,const scope_gen::Config &wanted) {
    const unsigned key=irq_lock();
    scope_gen::Reply r{id,status,reason,uint8_t(running),active,wanted};
    irq_unlock(key);return r;
}
static scope_gen::Reply submit(const scope_gen::Request &r) {
    if(r.query) return reply(r.id,faulted?scope_control::REJECTED:scope_control::APPLIED,
        faulted?scope_control::HARDWARE:scope_control::OK,active);
    if(have_last && r.id==last.id) {
        if(!scope_gen::equal(r.config,last.config))
            return reply(r.id,scope_control::REJECTED,scope_control::ID_CONFLICT,r.config);
        return reply(r.id,last_reason==scope_control::OK?scope_control::APPLIED:scope_control::REJECTED,
            last_reason,r.config);
    }
    last=r;have_last=true;
    last_reason=!scope_gen::valid(r.config)?scope_control::UNSUPPORTED:
        apply(r.config)?scope_control::OK:scope_control::HARDWARE;
    return reply(r.id,last_reason==scope_control::OK?scope_control::APPLIED:scope_control::REJECTED,last_reason,r.config);
}
static bool start() {
    if(!generator_hw::init()) return false;
    k_timer_init(&timer,tick,nullptr);
    if(!apply(scope_gen::defaults())) return false;
    k_timer_start(&timer,K_TICKS(CONFIG_SYS_CLOCK_TICKS_PER_SEC/scope_gen::CONTROL_HZ),
        K_TICKS(CONFIG_SYS_CLOCK_TICKS_PER_SEC/scope_gen::CONTROL_HZ));
    return true;
}
}
