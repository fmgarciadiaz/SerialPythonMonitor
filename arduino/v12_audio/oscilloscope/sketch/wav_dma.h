#pragma once
#include "wav_queue.h"
namespace wav_hw {
static LL_DMA_LinkNodeTypeDef nodes[scope_wav::SLOTS+1] __attribute__((aligned(1024)));
static_assert(sizeof(nodes)<=1024,"DAC linked-list nodes share a 64-KiB base");
static uint32_t data[scope_wav::SLOTS][scope_wav::POINTS] __attribute__((aligned(32)));
static uint32_t neutral __attribute__((aligned(32)))=2048;
constexpr uint32_t updates=LL_DMA_UPDATE_CTR1|LL_DMA_UPDATE_CTR2|LL_DMA_UPDATE_CBR1|
    LL_DMA_UPDATE_CSAR|LL_DMA_UPDATE_CDAR|LL_DMA_UPDATE_CLLR;
static void descriptor(unsigned slot,bool guard,unsigned count=1,bool final=false) {
    auto &r=nodes[slot].LinkRegisters;
    r[0]=LL_DMA_SRC_ALLOCATED_PORT1|(guard?LL_DMA_SRC_FIXED:LL_DMA_SRC_INCREMENT)|LL_DMA_SRC_DATAWIDTH_WORD|
        LL_DMA_DEST_ALLOCATED_PORT0|LL_DMA_DEST_FIXED|LL_DMA_DEST_DATAWIDTH_WORD;
    r[1]=LL_DMA_DIRECTION_MEMORY_TO_PERIPH|LL_DMA_HWREQUEST_SINGLEBURST|
        LL_DMA_TRIG_POLARITY_MASKED|LL_GPDMA1_REQUEST_DAC1_CH1|LL_DMA_TCEM_EACH_LLITEM_TRANSFER;
    r[2]=count*sizeof(uint32_t);
    r[3]=reinterpret_cast<uint32_t>(guard?&neutral:data[slot]);
    r[4]=reinterpret_cast<uint32_t>(&generator_hw::dac()->DHR12R1);
    const unsigned next=final?scope_wav::SLOTS:(slot+1)%scope_wav::SLOTS;
    r[5]=guard?0:updates|(reinterpret_cast<uint32_t>(&nodes[next])&DMA_CLLR_LA);
    r[6]=r[7]=0;
    cache_flush_invalidate(&nodes[slot],sizeof(nodes[slot]));
}
static bool prepare() {
    if(!generator_hw::stop(2048)) return false;
    const uintptr_t first=reinterpret_cast<uintptr_t>(&nodes[0]);
    const uintptr_t last=reinterpret_cast<uintptr_t>(&nodes[scope_wav::SLOTS]);
    // GPDMA linked-list addresses have one shared 64-KiB base.
    if((first&~uintptr_t(0xffff))!=(last&~uintptr_t(0xffff))) return false;
    cache_flush_invalidate(&neutral,sizeof(neutral));
    for(unsigned i=0;i<=scope_wav::SLOTS;++i) descriptor(i,true);
    return true;
}
static void publish(unsigned slot,const uint8_t *p,unsigned count,bool final) {
    for(unsigned i=0;i<count;++i) data[slot][i]=scope_wav::get16(p+2*i);
    cache_flush_invalidate(data[slot],sizeof(data[slot]));
    descriptor(slot,false,count,final);
    __DSB();
}
static bool start(unsigned head) {
    if(!generator_hw::stop(2048)) return false;
    GPDMA1_Channel4->CTR1=0;GPDMA1_Channel4->CTR2=0;GPDMA1_Channel4->CBR1=0;
    GPDMA1_Channel4->CSAR=0;GPDMA1_Channel4->CDAR=0;GPDMA1_Channel4->CLLR=0;
    LL_DMA_ConfigControl(GPDMA1,LL_DMA_CHANNEL_4,
        LL_DMA_LOW_PRIORITY_LOW_WEIGHT|LL_DMA_LINK_ALLOCATED_PORT1|LL_DMA_LSM_FULL_EXECUTION);
    LL_DMA_SetLinkedListBaseAddr(GPDMA1,LL_DMA_CHANNEL_4,reinterpret_cast<uint32_t>(&nodes[0]));
    LL_DMA_ConfigLinkUpdate(GPDMA1,LL_DMA_CHANNEL_4,updates,reinterpret_cast<uint32_t>(&nodes[head]));
    auto *dac=generator_hw::dac();
    TIM6->PSC=0;TIM6->ARR=generator::DAC_TIMER_HZ/scope_wav::active_rate-1;TIM6->CNT=0;
    TIM6->EGR=TIM_EGR_UG;TIM6->SR=0;dac->SR=DAC_SR_DMAUDR1;
    LL_DMA_EnableChannel(GPDMA1,LL_DMA_CHANNEL_4);
    dac->CR|=DAC_CR_DMAEN1|DAC_CR_TEN1;LL_TIM_EnableCounter(TIM6);
    return true;
}
// CSAR plus remaining byte count distinguish an actual transfer from the initial
// linked-list load and prove which buffer is still owned by DMA. Never infer it
// solely from a TC flag (the acquisition driver's shared IRQ may clear flags).
static int current() {
    const uint32_t address=GPDMA1_Channel4->CSAR;
    const uint32_t remaining=GPDMA1_Channel4->CBR1 & DMA_CBR1_BNDT;
    if(address==reinterpret_cast<uint32_t>(&neutral)) return -2;
    for(unsigned i=0;i<scope_wav::SLOTS;++i) {
        const uint32_t begin=reinterpret_cast<uint32_t>(data[i]);
        if(address>=begin && address<begin+sizeof(data[i]) &&
           remaining<=sizeof(data[i]) && (address-begin)%sizeof(uint32_t)==0 &&
           address-begin+remaining==nodes[i].LinkRegisters[2]) return int(i);
    }
    return -1;
}
static void clear_underrun() { generator_hw::dac()->SR=DAC_SR_DMAUDR1; }
static bool errors() {
    return (GPDMA1_Channel4->CSR & (DMA_CSR_DTEF|DMA_CSR_ULEF|DMA_CSR_USEF|DMA_CSR_TOF))!=0;
}
}
