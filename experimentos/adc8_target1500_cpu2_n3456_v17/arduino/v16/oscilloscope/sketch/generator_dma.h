#pragma once
#include <stm32u5xx_ll_tim.h>
// A0: DAC1 CH1, TIM6 TRGO, GPDMA1 channel 4. ADC/SPI channels 0..3 stay owned by acquisition.
namespace generator_hw {
static LL_DMA_LinkNodeTypeDef node __attribute__((aligned(CONFIG_DCACHE_LINE_SIZE)));
static bool initialized=false;
static DAC_TypeDef *dac() { return reinterpret_cast<DAC_TypeDef *>(DAC1_BASE); }
static bool healthy() {
    return !(dac()->SR & DAC_SR_DMAUDR1) &&
        !(GPDMA1_Channel4->CSR & (DMA_CSR_DTEF|DMA_CSR_ULEF|DMA_CSR_USEF|DMA_CSR_TOF));
}
static bool stop(uint16_t level) {
    LL_TIM_DisableCounter(TIM6);
    TIM6->CR1 &= ~TIM_CR1_OPM;
    dac()->CR &= ~DAC_CR_DMAEN1;
    dac()->CR &= ~DAC_CR_TEN1;
    // Flush any in-flight request before changing the holding register or waveform RAM.
    // This also runs at a one-shot end in IRQ context: never wait a 50-ms SPI timeout.
    const bool ok=reset_dma(GPDMA1_Channel4,100U);
    dac()->DHR12R1=level;
    return ok;
}
static void set_timing(generator::Timing t) {
    if(TIM6->PSC!=t.prescaler) {
        dac()->CR &= ~DAC_CR_TEN1;
        TIM6->PSC=t.prescaler;TIM6->ARR=t.reload;
        TIM6->EGR=TIM_EGR_UG;TIM6->SR=0;
        dac()->CR |= DAC_CR_TEN1;
    } else {
        TIM6->ARR=t.reload;
        if(TIM6->CNT>t.reload) TIM6->CNT=0;
    }
}
static bool init() {
    if((GPDMA1_Channel4->CCR & DMA_CCR_EN) || (TIM6->CR1 & TIM_CR1_CEN)) return false;
    RCC->APB1ENR1 |= RCC_APB1ENR1_TIM6EN;
    RCC->AHB1ENR |= RCC_AHB1ENR_GPDMA1EN;
    (void)RCC->AHB1ENR;
    irq_disable(GPDMA1_Channel4_IRQn);
    analogWriteResolution(12);analogWrite(DAC_OUTPUT,0);
    dac()->MCR = (dac()->MCR & ~DAC_MCR_HFSEL) | DAC_MCR_HFSEL_0;
    TIM6->CR1=0;TIM6->CR2=LL_TIM_TRGO_UPDATE;TIM6->DIER=0;
    dac()->CR = (dac()->CR & ~DAC_CR_TSEL1) | DAC_CR_TSEL1_2 | DAC_CR_TSEL1_0;
    initialized=true;
    return stop(0);
}
static bool pulse(uint16_t high,uint16_t low,uint32_t width_us) {
    if(!initialized || width_us<100 || width_us>65535 || !stop(low)) return false;
    TIM6->CR1=TIM_CR1_OPM;
    TIM6->PSC=159;TIM6->ARR=width_us-1;TIM6->CNT=0;
    TIM6->EGR=TIM_EGR_UG;TIM6->SR=0;
    dac()->SR=DAC_SR_DMAUDR1;
    // Initial update transfers high to DOR; preload low for the one-shot end.
    dac()->DHR12R1=high;dac()->CR |= DAC_CR_TEN1;
    TIM6->EGR=TIM_EGR_UG;TIM6->SR=0;
    dac()->DHR12R1=low;
    LL_TIM_EnableCounter(TIM6);
    return true;
}
static bool pulse_finished() { return !(TIM6->CR1 & TIM_CR1_CEN); }
static bool start(uint32_t *samples,unsigned points,generator::Timing t) {
    if(!initialized || !stop(samples[0])) return false;
    const uint32_t updates=LL_DMA_UPDATE_CTR1|LL_DMA_UPDATE_CTR2|LL_DMA_UPDATE_CBR1|
        LL_DMA_UPDATE_CSAR|LL_DMA_UPDATE_CDAR|LL_DMA_UPDATE_CLLR;
    auto &r=node.LinkRegisters;
    // Word-aligned 32-bit bus accesses: the halfword prototype raised DTEF
    // and a subsequent DAC underrun on this Q. Output values remain 12-bit.
    r[0]=LL_DMA_SRC_ALLOCATED_PORT1|LL_DMA_SRC_INCREMENT|LL_DMA_SRC_DATAWIDTH_WORD|
        LL_DMA_DEST_ALLOCATED_PORT0|LL_DMA_DEST_FIXED|LL_DMA_DEST_DATAWIDTH_WORD;
    r[1]=LL_DMA_DIRECTION_MEMORY_TO_PERIPH|LL_DMA_HWREQUEST_SINGLEBURST|
        LL_DMA_TRIG_POLARITY_MASKED|LL_GPDMA1_REQUEST_DAC1_CH1;
    r[2]=points*sizeof(uint32_t);
    r[3]=reinterpret_cast<uint32_t>(samples);
    r[4]=reinterpret_cast<uint32_t>(&dac()->DHR12R1);
    r[5]=updates|(reinterpret_cast<uint32_t>(&node)&DMA_CLLR_LA);
    r[6]=r[7]=0;
    GPDMA1_Channel4->CTR1=0;GPDMA1_Channel4->CTR2=0;GPDMA1_Channel4->CBR1=0;
    GPDMA1_Channel4->CSAR=0;GPDMA1_Channel4->CDAR=0;GPDMA1_Channel4->CLLR=0;
    cache_flush_invalidate(samples,256*sizeof(uint32_t));
    cache_flush_invalidate(&node,sizeof(node));
    LL_DMA_ConfigControl(GPDMA1,LL_DMA_CHANNEL_4,
        LL_DMA_LOW_PRIORITY_LOW_WEIGHT|LL_DMA_LINK_ALLOCATED_PORT1|LL_DMA_LSM_FULL_EXECUTION);
    LL_DMA_SetLinkedListBaseAddr(GPDMA1,LL_DMA_CHANNEL_4,reinterpret_cast<uint32_t>(&node));
    LL_DMA_ConfigLinkUpdate(GPDMA1,LL_DMA_CHANNEL_4,updates,reinterpret_cast<uint32_t>(&node));
    // UG latches PSC/ARR while DAC trigger is disabled: no extra output or DMA request.
    TIM6->PSC=t.prescaler;TIM6->ARR=t.reload;TIM6->CNT=0;
    TIM6->EGR=TIM_EGR_UG;TIM6->SR=0;
    dac()->SR = DAC_SR_DMAUDR1;
    LL_DMA_EnableChannel(GPDMA1,LL_DMA_CHANNEL_4);
    dac()->CR |= DAC_CR_DMAEN1;
    dac()->CR |= DAC_CR_TEN1;
    LL_TIM_EnableCounter(TIM6);
    return true;
}
}
