#include <Arduino.h>
#include <zephyr/kernel.h>
#include <zephyr/cache.h>
#include <string.h>

extern "C" {
#include "stm32u5xx.h"
#include "stm32u5xx_ll_adc.h"
#include "stm32u5xx_ll_dma.h"
#include "stm32u5xx_ll_tim.h"
#include "stm32u5xx_ll_gpio.h"
#include "stm32u5xx_ll_pwr.h"
}



// -----------------------------------------------------------------------------
// Compatibility implementations for Arduino Core Zephyr 0.90.0
//
// The UNO Q core ships the STM32U5 LL headers, but the corresponding non-inline
// LL implementation objects are not linked into an Arduino sketch.  The same
// core configuration also exposes Zephyr cache-management declarations without
// providing the cache backend symbols to the sketch link.
//
// These small implementations cover exactly the LL calls used below and are
// intentionally self-contained so the sketch does not depend on linking the
// STM32Cube LL .c files.
// -----------------------------------------------------------------------------

#ifdef cache_data_invd_range
#undef cache_data_invd_range
#endif
#ifdef cache_data_flush_and_invd_range
#undef cache_data_flush_and_invd_range
#endif

// STM32U585 = Cortex-M33.  The CMSIS build shipped with Arduino Core
// 0.90.0 does not declare SCB_*DCache_by_Addr(), but the Cortex-M33
// System Control Space exposes the standard MVA cache-maintenance registers.
// D-cache line size on this core is 32 bytes.
static inline void dcache_dsb(void)
{
    __asm__ volatile ("dsb sy" ::: "memory");
}

static inline void dcache_isb(void)
{
    __asm__ volatile ("isb sy" ::: "memory");
}

static inline void dcache_mva(uintptr_t addr, bool cleanInvalidate)
{
    // Cortex-M33 SCB cache maintenance registers:
    //   DCIMVAC  = 0xE000EF5C  invalidate by MVA
    //   DCCIMVAC = 0xE000EF70  clean + invalidate by MVA
    volatile uint32_t *reg = reinterpret_cast<volatile uint32_t *>(
        cleanInvalidate ? 0xE000EF70UL : 0xE000EF5CUL);
    *reg = static_cast<uint32_t>(addr);
}

extern "C" __attribute__((weak)) int cache_data_invd_range(void *addr, size_t size)
{
    if (addr == nullptr || size == 0U) {
        return 0;
    }

    uintptr_t start = reinterpret_cast<uintptr_t>(addr) & ~uintptr_t(31U);
    uintptr_t end = (reinterpret_cast<uintptr_t>(addr) + size + 31U) & ~uintptr_t(31U);

    dcache_dsb();
    for (uintptr_t p = start; p < end; p += 32U) {
        dcache_mva(p, false);
    }
    dcache_dsb();
    dcache_isb();
    return 0;
}

extern "C" __attribute__((weak)) int cache_data_flush_and_invd_range(void *addr, size_t size)
{
    if (addr == nullptr || size == 0U) {
        return 0;
    }

    uintptr_t start = reinterpret_cast<uintptr_t>(addr) & ~uintptr_t(31U);
    uintptr_t end = (reinterpret_cast<uintptr_t>(addr) + size + 31U) & ~uintptr_t(31U);

    dcache_dsb();
    for (uintptr_t p = start; p < end; p += 32U) {
        dcache_mva(p, true);
    }
    dcache_dsb();
    dcache_isb();
    return 0;
}

extern "C" __attribute__((weak)) ErrorStatus LL_ADC_CommonInit(
    ADC_Common_TypeDef *pADCxy_COMMON,
    LL_ADC_CommonInitTypeDef *pADC_CommonInitStruct)
{
    // ADC1 is configured disabled at this point, so only the common clock
    // field is needed for the configuration used by this sketch.
    LL_ADC_SetCommonClock(
        pADCxy_COMMON,
        pADC_CommonInitStruct->CommonClock);

    return SUCCESS;
}

extern "C" __attribute__((weak)) ErrorStatus LL_ADC_Init(
    ADC_TypeDef *pADCx,
    LL_ADC_InitTypeDef *pADC_InitStruct)
{
    if (LL_ADC_IsEnabled(pADCx) != 0UL) {
        return ERROR;
    }

    if (pADCx != ADC4) {
        MODIFY_REG(
            pADCx->CFGR1,
            ADC_CFGR1_RES | ADC4_CFGR1_WAIT,
            pADC_InitStruct->Resolution | pADC_InitStruct->LowPowerMode);

        MODIFY_REG(
            pADCx->CFGR2,
            ADC_CFGR2_LSHIFT,
            pADC_InitStruct->LeftBitShift);
    } else {
        MODIFY_REG(
            pADCx->CFGR1,
            ADC4_CFGR1_ALIGN | ADC4_CFGR1_WAIT,
            pADC_InitStruct->DataAlignment | pADC_InitStruct->LowPowerMode);

        LL_ADC_SetResolution(
            pADCx,
            pADC_InitStruct->Resolution);
    }

    return SUCCESS;
}

extern "C" __attribute__((weak)) ErrorStatus LL_ADC_REG_Init(
    ADC_TypeDef *pADCx,
    LL_ADC_REG_InitTypeDef *pADC_RegInitStruct)
{
    if (LL_ADC_IsEnabled(pADCx) != 0UL) {
        return ERROR;
    }

    if (pADC_RegInitStruct->SequencerLength != LL_ADC_REG_SEQ_SCAN_DISABLE) {
        MODIFY_REG(
            pADCx->CFGR1,
            ADC_CFGR1_EXTSEL |
            ADC_CFGR1_EXTEN |
            ADC_CFGR1_DISCEN |
            ADC_CFGR1_DISCNUM |
            ADC_CFGR1_CONT |
            ADC_CFGR1_DMNGT |
            ADC_CFGR1_OVRMOD,
            pADC_RegInitStruct->TriggerSource |
            pADC_RegInitStruct->SequencerDiscont |
            pADC_RegInitStruct->ContinuousMode |
            pADC_RegInitStruct->DataTransferMode |
            pADC_RegInitStruct->Overrun);
    } else {
        MODIFY_REG(
            pADCx->CFGR1,
            ADC_CFGR1_EXTSEL |
            ADC_CFGR1_EXTEN |
            ADC_CFGR1_DISCEN |
            ADC_CFGR1_DISCNUM |
            ADC_CFGR1_CONT |
            ADC_CFGR1_DMNGT |
            ADC_CFGR1_OVRMOD,
            pADC_RegInitStruct->TriggerSource |
            LL_ADC_REG_SEQ_DISCONT_DISABLE |
            pADC_RegInitStruct->ContinuousMode |
            pADC_RegInitStruct->DataTransferMode |
            pADC_RegInitStruct->Overrun);
    }

    LL_ADC_REG_SetSequencerLength(
        pADCx,
        pADC_RegInitStruct->SequencerLength);

    return SUCCESS;
}

extern "C" __attribute__((weak)) ErrorStatus LL_TIM_Init(
    TIM_TypeDef *TIMx,
    const LL_TIM_InitTypeDef *TIM_InitStruct)
{
    uint32_t tmpcr1 = LL_TIM_ReadReg(TIMx, CR1);

    if (IS_TIM_COUNTER_MODE_SELECT_INSTANCE(TIMx)) {
        MODIFY_REG(
            tmpcr1,
            TIM_CR1_DIR | TIM_CR1_CMS,
            TIM_InitStruct->CounterMode);
    }

    if (IS_TIM_CLOCK_DIVISION_INSTANCE(TIMx)) {
        MODIFY_REG(
            tmpcr1,
            TIM_CR1_CKD,
            TIM_InitStruct->ClockDivision);
    }

    LL_TIM_WriteReg(TIMx, CR1, tmpcr1);
    LL_TIM_SetAutoReload(TIMx, TIM_InitStruct->Autoreload);
    LL_TIM_SetPrescaler(TIMx, TIM_InitStruct->Prescaler);

    LL_TIM_GenerateEvent_UPDATE(TIMx);
    return SUCCESS;
}

extern "C" __attribute__((weak)) uint32_t LL_DMA_List_Init(
    DMA_TypeDef *DMAx,
    uint32_t Channel,
    LL_DMA_InitLinkedListTypeDef *DMA_InitLinkedListStruct)
{
    LL_DMA_ConfigControl(
        DMAx,
        Channel,
        DMA_InitLinkedListStruct->Priority |
        DMA_InitLinkedListStruct->LinkAllocatedPort |
        DMA_InitLinkedListStruct->LinkStepMode);

    LL_DMA_SetTransferEventMode(
        DMAx,
        Channel,
        DMA_InitLinkedListStruct->TransferEventMode);

    return static_cast<uint32_t>(SUCCESS);
}

// Compatibilidad con la firma mutable de 0.90.0 y const de 1.0.0.
template <typename T> struct DmaFirstArgument;
template <typename R, typename A, typename B>
struct DmaFirstArgument<R (*)(A, B)> { using Type = A; };
using DmaNodeInitPointer = DmaFirstArgument<decltype(&LL_DMA_CreateLinkNode)>::Type;

extern "C" __attribute__((weak)) uint32_t LL_DMA_CreateLinkNode(
    DmaNodeInitPointer DMA_InitNodeStruct,
    LL_DMA_LinkNodeTypeDef *pNode)
{
    uint32_t reg = 0U;

    if ((DMA_InitNodeStruct->UpdateRegisters & LL_DMA_UPDATE_CTR1) != 0U) {
        pNode->LinkRegisters[reg++] =
            DMA_InitNodeStruct->DestIncMode |
            DMA_InitNodeStruct->DestDataWidth |
            DMA_InitNodeStruct->DataAlignment |
            DMA_InitNodeStruct->SrcIncMode |
            DMA_InitNodeStruct->SrcDataWidth;

        if (DMA_InitNodeStruct->NodeType != LL_DMA_LPDMA_LINEAR_NODE) {
            pNode->LinkRegisters[reg - 1U] |=
                DMA_InitNodeStruct->DestAllocatedPort |
                DMA_InitNodeStruct->DestHWordExchange |
                DMA_InitNodeStruct->DestByteExchange |
                ((DMA_InitNodeStruct->DestBurstLength - 1U) << DMA_CTR1_DBL_1_Pos) |
                DMA_InitNodeStruct->SrcAllocatedPort |
                DMA_InitNodeStruct->SrcByteExchange |
                ((DMA_InitNodeStruct->SrcBurstLength - 1U) << DMA_CTR1_SBL_1_Pos);
        }
    }

    if ((DMA_InitNodeStruct->UpdateRegisters & LL_DMA_UPDATE_CTR2) != 0U) {
        pNode->LinkRegisters[reg++] =
            DMA_InitNodeStruct->TransferEventMode |
            DMA_InitNodeStruct->TriggerPolarity |
            DMA_InitNodeStruct->BlkHWRequest |
            DMA_InitNodeStruct->Direction;

        if (DMA_InitNodeStruct->Direction != LL_DMA_DIRECTION_MEMORY_TO_MEMORY) {
            pNode->LinkRegisters[reg - 1U] |=
                DMA_InitNodeStruct->Request & DMA_CTR2_REQSEL;
        }

        if (DMA_InitNodeStruct->TriggerPolarity != LL_DMA_TRIG_POLARITY_MASKED) {
            pNode->LinkRegisters[reg - 1U] |=
                (((DMA_InitNodeStruct->TriggerSelection << DMA_CTR2_TRIGSEL_Pos) &
                  DMA_CTR2_TRIGSEL) |
                 DMA_InitNodeStruct->TriggerMode);
        }
    }

    if ((DMA_InitNodeStruct->UpdateRegisters & LL_DMA_UPDATE_CBR1) != 0U) {
        pNode->LinkRegisters[reg++] = DMA_InitNodeStruct->BlkDataLength;
    }

    if ((DMA_InitNodeStruct->UpdateRegisters & LL_DMA_UPDATE_CSAR) != 0U) {
        pNode->LinkRegisters[reg++] = DMA_InitNodeStruct->SrcAddress;
    }

    if ((DMA_InitNodeStruct->UpdateRegisters & LL_DMA_UPDATE_CDAR) != 0U) {
        pNode->LinkRegisters[reg++] = DMA_InitNodeStruct->DestAddress;
    }

    if ((DMA_InitNodeStruct->UpdateRegisters & LL_DMA_UPDATE_CLLR) != 0U) {
        pNode->LinkRegisters[reg++] =
            DMA_InitNodeStruct->UpdateRegisters &
            (DMA_CLLR_UT1 |
             DMA_CLLR_UT2 |
             DMA_CLLR_UB1 |
             DMA_CLLR_USA |
             DMA_CLLR_UDA |
             DMA_CLLR_ULL);
    } else {
        pNode->LinkRegisters[reg++] = 0U;
    }

    // Clear unused descriptor words. This also makes the descriptor deterministic
    // if a future configuration changes the update mask.
    for (; reg < (sizeof(pNode->LinkRegisters) / sizeof(pNode->LinkRegisters[0])); ++reg) {
        pNode->LinkRegisters[reg] = 0U;
    }

    return static_cast<uint32_t>(SUCCESS);
}

extern "C" __attribute__((weak)) void LL_DMA_ConnectLinkNode(
    LL_DMA_LinkNodeTypeDef *pPrevLinkNode,
    uint32_t PrevNodeCLLRIdx,
    LL_DMA_LinkNodeTypeDef *pNewLinkNode,
    uint32_t NewNodeCLLRIdx)
{
    pPrevLinkNode->LinkRegisters[PrevNodeCLLRIdx] =
        (((uint32_t)pNewLinkNode & DMA_CLLR_LA) |
         (pNewLinkNode->LinkRegisters[NewNodeCLLRIdx] &
          (DMA_CLLR_UT1 |
           DMA_CLLR_UT2 |
           DMA_CLLR_UB1 |
           DMA_CLLR_USA |
           DMA_CLLR_UDA |
           DMA_CLLR_UT3 |
           DMA_CLLR_UB2 |
           DMA_CLLR_ULL)));
}

// ============================================================
// Arduino UNO Q / STM32U585
//
// A0 = PA4 = ADC1_IN9
// A1 = PA5 = ADC1_IN10
// A2 = PA6 = digital output; externally connected A2 -> A1
//
// Acquisition path (entirely hardware timed):
//
//   TIM2 TRGO 5 kHz
//          |
//          v
//       ADC1 sequence
//       rank 1 = A0
//       rank 2 = A1
//          |
//          v
//        GPDMA1
//     ping-pong linked list
//          |
//          v
//          RAM
//          |
//       Serial 2 Mbps
//
// The CPU never calls analogRead() while acquiring.
// ============================================================

#define WRITE_PIN           A2
#define ADC_IN_PIN          A0
#define ADC_OUT_PIN         A1

#define SAMPLE_RATE_HZ      10000U
#define SAMPLE_PERIOD_US    100U
#define TOGGLE_PERIOD_MS    200U
#define SERIAL_BAUD         1000000U

// Each DMA node contains this many A0/A1 pairs.
// 2048 pairs = 409.6 ms at 5 kHz.
#define DMA_NODE_PAIRS      2048U
#define DMA_NODE_RESULTS    (DMA_NODE_PAIRS * 2U)   // uint16 results
#define DMA_NODE_BYTES      (DMA_NODE_RESULTS * sizeof(uint16_t))
#define DMA_NODE_COUNT      2U
#define DMA_BUFFER_RESULTS  (DMA_NODE_RESULTS * DMA_NODE_COUNT)

// Binary packets sent over Serial.
#define SERIAL_BLOCK_PAIRS  512U

#define PRIORITY_TOGGLE     6
#define PRIORITY_SERIAL     7

// UNO Q Zephyr build uses a 160 MHz system clock.
// TIM2 is configured for 160 MHz / (159 + 1) / (199 + 1) = 5 kHz.
#define TIM2_PRESCALER      159U
#define TIM2_AUTORELOAD     99U

struct __attribute__((packed)) Sample
{
    uint32_t timestamp;
    uint16_t adc_in;
    uint16_t adc_out;
};

// ------------------------------------------------------------
// DMA RAM
// ------------------------------------------------------------

static uint16_t dmaBuffer[DMA_BUFFER_RESULTS]
    __attribute__((aligned(CONFIG_DCACHE_LINE_SIZE)));

// Hardware timestamps captured on every TIM2 update.
// TIM5 is a free-running 1 MHz counter, so one tick = 1 us.
static uint32_t timestampBuffer[DMA_NODE_PAIRS * DMA_NODE_COUNT]
    __attribute__((aligned(CONFIG_DCACHE_LINE_SIZE)));

static LL_DMA_LinkNodeTypeDef dmaNode[DMA_NODE_COUNT]
    __attribute__((aligned(CONFIG_DCACHE_LINE_SIZE)));

static LL_DMA_LinkNodeTypeDef timestampNode[DMA_NODE_COUNT]
    __attribute__((aligned(CONFIG_DCACHE_LINE_SIZE)));

static struct k_thread toggle_thread_data;
static struct k_thread serial_thread_data;

K_THREAD_STACK_DEFINE(toggle_stack, 1024);
K_THREAD_STACK_DEFINE(serial_stack, 4096);

static volatile uint32_t dmaErrorCount = 0;

static inline void cache_flush_invalidate(void *addr, size_t len)
{
    (void)sys_cache_data_flush_and_invd_range(addr, len);
}

static inline void cache_invalidate(void *addr, size_t len)
{
    (void)sys_cache_data_invd_range(addr, len);
}

// ------------------------------------------------------------
// ADC1
// ------------------------------------------------------------

static void adc_init(void)
{
    LL_ADC_CommonInitTypeDef common = {0};
    LL_ADC_InitTypeDef adc = {0};
    LL_ADC_REG_InitTypeDef reg = {0};

    // These are the actual STM32U585 RCC gates. The LL clock aliases
    // used by the STM32 bare-metal examples are not exposed by the
    // Arduino UNO Q Zephyr build, so use the CMSIS register definitions.
    RCC->AHB2ENR1 |= RCC_AHB2ENR1_GPIOAEN;
    RCC->AHB2ENR1 |= RCC_AHB2ENR1_ADC12EN;
    (void)RCC->AHB2ENR1;

    LL_PWR_EnableVDDA();

    // A0 = PA4 = ADC1_IN9
    LL_GPIO_SetPinMode(GPIOA, LL_GPIO_PIN_4, LL_GPIO_MODE_ANALOG);
    LL_GPIO_SetPinPull(GPIOA, LL_GPIO_PIN_4, LL_GPIO_PULL_NO);

    // A1 = PA5 = ADC1_IN10
    LL_GPIO_SetPinMode(GPIOA, LL_GPIO_PIN_5, LL_GPIO_MODE_ANALOG);
    LL_GPIO_SetPinPull(GPIOA, LL_GPIO_PIN_5, LL_GPIO_PULL_NO);

    // ADC clock = existing ADC kernel clock divided by 4.
    common.CommonClock = LL_ADC_CLOCK_ASYNC_DIV4;
    LL_ADC_CommonInit(__LL_ADC_COMMON_INSTANCE(ADC1), &common);

    adc.Resolution = LL_ADC_RESOLUTION_14B;
    adc.LowPowerMode = LL_ADC_LP_MODE_NONE;
    adc.LeftBitShift = LL_ADC_LEFT_BIT_SHIFT_NONE;
    LL_ADC_Init(ADC1, &adc);

    LL_ADC_SetGainCompensation(ADC1, 0);
    LL_ADC_SetTriggerFrequencyMode(ADC1, LL_ADC_TRIGGER_FREQ_HIGH);

    // One TIM2 trigger starts exactly one two-channel conversion sequence.
    reg.TriggerSource = LL_ADC_REG_TRIG_EXT_TIM2_TRGO;
    reg.SequencerLength = LL_ADC_REG_SEQ_SCAN_ENABLE_2RANKS;
    reg.SequencerDiscont = LL_ADC_REG_SEQ_DISCONT_DISABLE;
    reg.ContinuousMode = LL_ADC_REG_CONV_SINGLE;
    reg.Overrun = LL_ADC_REG_OVR_DATA_OVERWRITTEN;
    reg.DataTransferMode = LL_ADC_REG_DMA_TRANSFER_UNLIMITED;
    LL_ADC_REG_Init(ADC1, &reg);

    LL_ADC_REG_SetTriggerEdge(ADC1, LL_ADC_REG_TRIG_EXT_RISING);
    LL_ADC_SetOverSamplingScope(ADC1, LL_ADC_OVS_DISABLE);

    LL_ADC_SetChannelSingleDiff(ADC1, LL_ADC_CHANNEL_9, LL_ADC_SINGLE_ENDED);
    LL_ADC_SetChannelSingleDiff(ADC1, LL_ADC_CHANNEL_10, LL_ADC_SINGLE_ENDED);

    LL_ADC_REG_SetSequencerRanks(
        ADC1, LL_ADC_REG_RANK_1, LL_ADC_CHANNEL_9);
    LL_ADC_REG_SetSequencerRanks(
        ADC1, LL_ADC_REG_RANK_2, LL_ADC_CHANNEL_10);

    // At the UNO Q ADC clock this is easily fast enough for 10 kHz,
    // while giving comfortable acquisition time for normal source impedance.
    LL_ADC_SetChannelSamplingTime(
        ADC1, LL_ADC_CHANNEL_9, LL_ADC_SAMPLINGTIME_391CYCLES_5);
    LL_ADC_SetChannelSamplingTime(
        ADC1, LL_ADC_CHANNEL_10, LL_ADC_SAMPLINGTIME_391CYCLES_5);

    LL_ADC_SetChannelPreselection(ADC1, LL_ADC_CHANNEL_9);
    LL_ADC_SetChannelPreselection(ADC1, LL_ADC_CHANNEL_10);

    // STM32U5 ADC activation procedure.
    LL_ADC_DisableDeepPowerDown(ADC1);
    LL_ADC_EnableInternalRegulator(ADC1);
    k_busy_wait(100);

    LL_ADC_StartCalibration(ADC1, LL_ADC_SINGLE_ENDED);
    while (LL_ADC_IsCalibrationOnGoing(ADC1))
    {
    }

    k_busy_wait(100);

    LL_ADC_Enable(ADC1);
    while (!LL_ADC_IsActiveFlag_ADRDY(ADC1))
    {
    }
    LL_ADC_ClearFlag_ADRDY(ADC1);
}

// ------------------------------------------------------------
// GPDMA1
//
// Two linked-list nodes form a ping-pong buffer:
//
//   node 0 -> node 1 -> node 0 -> ...
//
// Every node completes after DMA_NODE_PAIRS ADC trigger frames.
// The TC event is generated for EACH linked-list item.
//
// No DMA interrupt is used. The serial thread polls the TC flag.
// This avoids IRQ_CONNECT entirely inside the Arduino sketch.
// ------------------------------------------------------------

static void timestamp_timer_init(void)
{
    // TIM5 is a free-running 32-bit counter.  Use the same prescaler as TIM2
    // so that, with the UNO Q 160 MHz timer clock, TIM5 runs at exactly 1 MHz.
    RCC->APB1ENR1 |= RCC_APB1ENR1_TIM5EN;
    (void)RCC->APB1ENR1;

    TIM5->CR1 = 0;
    TIM5->PSC = TIM2_PRESCALER;
    TIM5->ARR = 0xFFFFFFFFU;
    TIM5->CNT = 0;
    TIM5->EGR = TIM_EGR_UG;
    TIM5->SR = 0;
    TIM5->CR1 = TIM_CR1_CEN;
}

static void dma_init(void)
{
    LL_DMA_InitNodeTypeDef node = {0};
    LL_DMA_InitLinkedListTypeDef list = {0};

    RCC->AHB1ENR |= RCC_AHB1ENR_GPDMA1EN;
    (void)RCC->AHB1ENR;

    node.NodeType = LL_DMA_GPDMA_LINEAR_NODE;
    node.Request = LL_GPDMA1_REQUEST_ADC1;
    node.BlkHWRequest = LL_DMA_HWREQUEST_SINGLEBURST;
    node.Direction = LL_DMA_DIRECTION_PERIPH_TO_MEMORY;

    node.DestAllocatedPort = LL_DMA_DEST_ALLOCATED_PORT1;
    node.DestBurstLength = 1U;
    node.DestIncMode = LL_DMA_DEST_INCREMENT;
    node.DestDataWidth = LL_DMA_DEST_DATAWIDTH_HALFWORD;

    node.SrcAllocatedPort = LL_DMA_SRC_ALLOCATED_PORT0;
    node.SrcBurstLength = 1U;
    node.SrcIncMode = LL_DMA_SRC_FIXED;
    node.SrcDataWidth = LL_DMA_SRC_DATAWIDTH_WORD;

    // Data-alignment mode used by ST's official STM32U5 ADC+GPDMA example.
    node.DataAlignment = LL_DMA_DATA_ALIGN_ZEROPADD;
    node.DestHWordExchange = LL_DMA_DEST_HALFWORD_PRESERVE;
    node.DestByteExchange = LL_DMA_DEST_BYTE_PRESERVE;
    node.SrcByteExchange = LL_DMA_SRC_BYTE_PRESERVE;

    node.TriggerPolarity = LL_DMA_TRIG_POLARITY_MASKED;

    node.UpdateRegisters =
        LL_DMA_UPDATE_CTR1 |
        LL_DMA_UPDATE_CTR2 |
        LL_DMA_UPDATE_CBR1 |
        LL_DMA_UPDATE_CSAR |
        LL_DMA_UPDATE_CDAR |
        LL_DMA_UPDATE_CLLR;

    node.SrcAddress =
        (uint32_t)LL_ADC_DMA_GetRegAddr(
            ADC1, LL_ADC_DMA_REG_REGULAR_DATA);

    // IMPORTANT:
    // GPDMA source width is WORD (32 bit), so the STM32U5 LL example
    // expresses block length as number_of_results * 4 bytes.
    node.BlkDataLength = DMA_NODE_RESULTS * 4U;

    for (uint32_t n = 0; n < DMA_NODE_COUNT; n++)
    {
        node.DestAddress =
            (uint32_t)&dmaBuffer[n * DMA_NODE_RESULTS];

        LL_DMA_CreateLinkNode(&node, &dmaNode[n]);
    }

    // --------------------------------------------------------
    // Second DMA channel: on the SAME TIM2 update that triggers ADC,
    // copy TIM5->CNT (hardware time) into timestampBuffer.
    // --------------------------------------------------------
    LL_DMA_InitNodeTypeDef ts = {0};

    ts.NodeType = LL_DMA_GPDMA_LINEAR_NODE;
    ts.Request = LL_GPDMA1_REQUEST_TIM2_UP;
    ts.BlkHWRequest = LL_DMA_HWREQUEST_SINGLEBURST;
    ts.Direction = LL_DMA_DIRECTION_PERIPH_TO_MEMORY;

    ts.DestAllocatedPort = LL_DMA_DEST_ALLOCATED_PORT1;
    ts.DestBurstLength = 1U;
    ts.DestIncMode = LL_DMA_DEST_INCREMENT;
    ts.DestDataWidth = LL_DMA_DEST_DATAWIDTH_WORD;

    ts.SrcAllocatedPort = LL_DMA_SRC_ALLOCATED_PORT0;
    ts.SrcBurstLength = 1U;
    ts.SrcIncMode = LL_DMA_SRC_FIXED;
    ts.SrcDataWidth = LL_DMA_SRC_DATAWIDTH_WORD;

    ts.DataAlignment = LL_DMA_DATA_ALIGN_ZEROPADD;
    ts.DestHWordExchange = LL_DMA_DEST_HALFWORD_PRESERVE;
    ts.DestByteExchange = LL_DMA_DEST_BYTE_PRESERVE;
    ts.SrcByteExchange = LL_DMA_SRC_BYTE_PRESERVE;
    ts.TriggerPolarity = LL_DMA_TRIG_POLARITY_MASKED;

    ts.UpdateRegisters =
        LL_DMA_UPDATE_CTR1 |
        LL_DMA_UPDATE_CTR2 |
        LL_DMA_UPDATE_CBR1 |
        LL_DMA_UPDATE_CSAR |
        LL_DMA_UPDATE_CDAR |
        LL_DMA_UPDATE_CLLR;

    ts.SrcAddress = (uint32_t)&TIM5->CNT;
    ts.BlkDataLength = DMA_NODE_PAIRS * sizeof(uint32_t);

    for (uint32_t n = 0; n < DMA_NODE_COUNT; n++)
    {
        ts.DestAddress =
            (uint32_t)&timestampBuffer[n * DMA_NODE_PAIRS];

        LL_DMA_CreateLinkNode(&ts, &timestampNode[n]);
    }

    // Timestamp DMA ping-pong list.
    LL_DMA_ConnectLinkNode(
        &timestampNode[0], LL_DMA_CLLR_OFFSET5,
        &timestampNode[1], LL_DMA_CLLR_OFFSET5);

    LL_DMA_ConnectLinkNode(
        &timestampNode[1], LL_DMA_CLLR_OFFSET5,
        &timestampNode[0], LL_DMA_CLLR_OFFSET5);

    LL_DMA_InitLinkedListTypeDef tsList = {0};
    tsList.Priority = LL_DMA_HIGH_PRIORITY;
    tsList.TransferEventMode = LL_DMA_TCEM_EACH_LLITEM_TRANSFER;
    tsList.LinkStepMode = LL_DMA_LSM_FULL_EXECUTION;
    tsList.LinkAllocatedPort = LL_DMA_LINK_ALLOCATED_PORT1;

    LL_DMA_List_Init(GPDMA1, LL_DMA_CHANNEL_0, &tsList);
    LL_DMA_SetLinkedListBaseAddr(
        GPDMA1, LL_DMA_CHANNEL_0, (uint32_t)&timestampNode[0]);
    LL_DMA_ConfigLinkUpdate(
        GPDMA1,
        LL_DMA_CHANNEL_0,
        LL_DMA_UPDATE_CTR1 |
        LL_DMA_UPDATE_CTR2 |
        LL_DMA_UPDATE_CBR1 |
        LL_DMA_UPDATE_CSAR |
        LL_DMA_UPDATE_CDAR |
        LL_DMA_UPDATE_CLLR,
        (uint32_t)&timestampNode[0]);

    // Circular ping-pong list.
    LL_DMA_ConnectLinkNode(
        &dmaNode[0],
        LL_DMA_CLLR_OFFSET5,
        &dmaNode[1],
        LL_DMA_CLLR_OFFSET5);

    LL_DMA_ConnectLinkNode(
        &dmaNode[1],
        LL_DMA_CLLR_OFFSET5,
        &dmaNode[0],
        LL_DMA_CLLR_OFFSET5);

    list.Priority = LL_DMA_HIGH_PRIORITY;

    // Generate TC at the end of EACH linked-list item.
    list.TransferEventMode = LL_DMA_TCEM_EACH_LLITEM_TRANSFER;
    list.LinkStepMode = LL_DMA_LSM_FULL_EXECUTION;
    list.LinkAllocatedPort = LL_DMA_LINK_ALLOCATED_PORT1;

    LL_DMA_List_Init(
        GPDMA1,
        LL_DMA_CHANNEL_1,
        &list);

    LL_DMA_SetLinkedListBaseAddr(
        GPDMA1,
        LL_DMA_CHANNEL_1,
        (uint32_t)&dmaNode[0]);

    LL_DMA_ConfigLinkUpdate(
        GPDMA1,
        LL_DMA_CHANNEL_1,
        LL_DMA_UPDATE_CTR1 |
        LL_DMA_UPDATE_CTR2 |
        LL_DMA_UPDATE_CBR1 |
        LL_DMA_UPDATE_CSAR |
        LL_DMA_UPDATE_CDAR |
        LL_DMA_UPDATE_CLLR,
        (uint32_t)&dmaNode[0]);

    LL_DMA_ClearFlag_TC(GPDMA1, LL_DMA_CHANNEL_0);
    LL_DMA_ClearFlag_DTE(GPDMA1, LL_DMA_CHANNEL_0);
    LL_DMA_ClearFlag_TC(GPDMA1, LL_DMA_CHANNEL_1);
    LL_DMA_ClearFlag_DTE(GPDMA1, LL_DMA_CHANNEL_1);

    memset(dmaBuffer, 0, sizeof(dmaBuffer));
    memset(timestampBuffer, 0, sizeof(timestampBuffer));

    // DMA reads the linked-list descriptors directly from RAM.
    cache_flush_invalidate(dmaNode, sizeof(dmaNode));
    cache_flush_invalidate(timestampNode, sizeof(timestampNode));
    cache_flush_invalidate(dmaBuffer, sizeof(dmaBuffer));
    cache_flush_invalidate(timestampBuffer, sizeof(timestampBuffer));
}

// ------------------------------------------------------------
// TIM2 -> TRGO @ 10 kHz
// ------------------------------------------------------------

static void timer_init(void)
{
    LL_TIM_InitTypeDef tim = {0};

    RCC->APB1ENR1 |= RCC_APB1ENR1_TIM2EN;
    (void)RCC->APB1ENR1;

    tim.Prescaler = TIM2_PRESCALER;
    tim.CounterMode = LL_TIM_COUNTERMODE_UP;
    tim.Autoreload = TIM2_AUTORELOAD;
    tim.ClockDivision = LL_TIM_CLOCKDIVISION_DIV1;

    LL_TIM_Init(TIM2, &tim);
    LL_TIM_DisableARRPreload(TIM2);
    LL_TIM_SetClockSource(TIM2, LL_TIM_CLOCKSOURCE_INTERNAL);
    LL_TIM_SetTriggerOutput(TIM2, LL_TIM_TRGO_UPDATE);
    LL_TIM_DisableMasterSlaveMode(TIM2);

    // TIM2 UPDATE must also generate a GPDMA request for the hardware
    // timestamp channel.  Without UDE, the timestamp DMA never advances.
    LL_TIM_EnableDMAReq_UPDATE(TIM2);

    LL_TIM_SetCounter(TIM2, 0);
}

// ------------------------------------------------------------
// Toggle thread
// ------------------------------------------------------------

static void toggle_thread(void *, void *, void *)
{
    bool state = false;

    while (1)
    {
        state = !state;
        digitalWrite(WRITE_PIN, state ? HIGH : LOW);
        k_sleep(K_MSEC(TOGGLE_PERIOD_MS));
    }
}

// ------------------------------------------------------------
// Serial consumer
//
// IMPORTANT: this thread is completely outside the acquisition timing path.
// Serial.write() may block; ADC + TIM2 + GPDMA continue in hardware.
// ------------------------------------------------------------

Sample tx[SERIAL_BLOCK_PAIRS];
  
// Validar el destino y el contador, no solo las banderas TC de arranque.
static bool dma_in_node(uint32_t channel, uint32_t bufferStart,
                        uint32_t node, uint32_t maxSourceBytes)
{
    uint32_t dest = LL_DMA_GetDestAddress(GPDMA1, channel);
    uint32_t remaining = LL_DMA_GetBlkDataLength(GPDMA1, channel);
    uint32_t start = bufferStart + node * DMA_NODE_BYTES;
    return dest >= start && dest < start + DMA_NODE_BYTES &&
           remaining > 0U && remaining <= maxSourceBytes;
}

static bool both_dma_in_node(uint32_t node)
{
    return dma_in_node(LL_DMA_CHANNEL_1, (uint32_t)dmaBuffer,
                       node, DMA_NODE_RESULTS * 4U) &&
           dma_in_node(LL_DMA_CHANNEL_0, (uint32_t)timestampBuffer,
                       node, DMA_NODE_PAIRS * sizeof(uint32_t));
}

static void serial_thread(void *, void *, void *)
{


    uint32_t completedNode = 0;

    // Primero observar ambos canales adquiriendo el nodo 0. Las TC iniciales
    // pueden estar activas antes de haber adquirido un nodo completo.
    while (!both_dma_in_node(0U)) {
        k_sleep(K_USEC(50));
    }
    LL_DMA_ClearFlag_TC(GPDMA1, LL_DMA_CHANNEL_1);
    LL_DMA_ClearFlag_TC(GPDMA1, LL_DMA_CHANNEL_0);

    // La primera entrega solo es valida cuando ambos DMA pasaron al nodo 1.
    // Dejar las nuevas TC pendientes para el consumidor normal.
    while (!(both_dma_in_node(1U) &&
             LL_DMA_IsActiveFlag_TC(GPDMA1, LL_DMA_CHANNEL_1) &&
             LL_DMA_IsActiveFlag_TC(GPDMA1, LL_DMA_CHANNEL_0))) {
        k_sleep(K_USEC(50));
    }

    while (1)
    {
        // Wait until BOTH DMA streams have completed the same ping-pong node:
        // ADC data + hardware timestamps.
        while (!(LL_DMA_IsActiveFlag_TC(GPDMA1, LL_DMA_CHANNEL_1) &&
                 LL_DMA_IsActiveFlag_TC(GPDMA1, LL_DMA_CHANNEL_0)))
        {
            if (LL_DMA_IsActiveFlag_DTE(GPDMA1, LL_DMA_CHANNEL_1))
            {
                LL_DMA_ClearFlag_DTE(GPDMA1, LL_DMA_CHANNEL_1);
                dmaErrorCount++;
            }
            if (LL_DMA_IsActiveFlag_DTE(GPDMA1, LL_DMA_CHANNEL_0))
            {
                LL_DMA_ClearFlag_DTE(GPDMA1, LL_DMA_CHANNEL_0);
                dmaErrorCount++;
            }

            k_sleep(K_USEC(50));
        }

        LL_DMA_ClearFlag_TC(GPDMA1, LL_DMA_CHANNEL_1);
        LL_DMA_ClearFlag_TC(GPDMA1, LL_DMA_CHANNEL_0);

        uint16_t *src =
            &dmaBuffer[completedNode * DMA_NODE_RESULTS];
        uint32_t *tsrc =
            &timestampBuffer[completedNode * DMA_NODE_PAIRS];

        // These nodes are complete and the DMA is now filling the other nodes.
        cache_invalidate(src, DMA_NODE_BYTES);
        cache_invalidate(tsrc, DMA_NODE_PAIRS * sizeof(uint32_t));

        for (uint32_t base = 0;
             base < DMA_NODE_PAIRS;
             base += SERIAL_BLOCK_PAIRS)
        {
            for (uint32_t i = 0; i < SERIAL_BLOCK_PAIRS; i++)
            {
                const uint32_t pair = base + i;

                // REAL acquisition timestamp: copied by GPDMA from TIM5->CNT
                // on the same TIM2 update that triggered this ADC sample.
                tx[i].timestamp = tsrc[pair];

                tx[i].adc_in = src[2U * pair];
                tx[i].adc_out = src[2U * pair + 1U];

            }

            // Protocol kept identical to the previous acquisition software:
            //   DATA (4 bytes)
            //   state (1 byte)
            //   count (uint16 LE)
            //   count * Sample, where Sample is 8 bytes
            Serial1.write((const uint8_t *)"DATA", 4);

            uint8_t state = 1;
            Serial1.write(&state, 1);

            uint16_t count = SERIAL_BLOCK_PAIRS;
            Serial1.write(
                (uint8_t *)&count,
                sizeof(count));

            Serial1.write(
                (const uint8_t *)tx,
                sizeof(tx));
        }

        completedNode ^= 1U;
    }
}

// ------------------------------------------------------------
// Arduino setup / loop
// ------------------------------------------------------------

void setup()
{
    pinMode(ADC_IN_PIN, INPUT);
    pinMode(ADC_OUT_PIN, INPUT);

    pinMode(WRITE_PIN, OUTPUT);
    digitalWrite(WRITE_PIN, LOW);

    Serial1.begin(SERIAL_BAUD);

    // Configure the hardware path before starting the trigger.
    timer_init();
    timestamp_timer_init();
    adc_init();
    dma_init();

    k_thread_create(
        &serial_thread_data,
        serial_stack,
        K_THREAD_STACK_SIZEOF(serial_stack),
        serial_thread,
        NULL, NULL, NULL,
        PRIORITY_SERIAL,
        0,
        K_NO_WAIT);

    k_thread_create(
        &toggle_thread_data,
        toggle_stack,
        K_THREAD_STACK_SIZEOF(toggle_stack),
        toggle_thread,
        NULL, NULL, NULL,
        PRIORITY_TOGGLE,
        0,
        K_NO_WAIT);

    // TIM5 timestamp counter is already running. Start both DMAs, then ADC and TIM2.
    LL_DMA_EnableChannel(GPDMA1, LL_DMA_CHANNEL_0);
    LL_DMA_EnableChannel(GPDMA1, LL_DMA_CHANNEL_1);
    LL_ADC_REG_StartConversion(ADC1);
    LL_TIM_EnableCounter(TIM2);
}

void loop()
{
    k_sleep(K_SECONDS(1));
}