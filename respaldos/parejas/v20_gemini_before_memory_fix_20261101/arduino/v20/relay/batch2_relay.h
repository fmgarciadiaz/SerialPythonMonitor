#pragma once
#include <stdint.h>
#include <string.h>

enum { SCOPE_BATCH2_BYTES = 2 * BLOCK };
_Static_assert(SCOPE_BATCH2_BYTES == 1984 && SCOPE_BATCH2_BYTES / 2 == 992,
               "Two SCP1 frames fit the SPI3 10-bit TSIZE in SPI16 mode");

// Half zero always carries a fresh internal PING. A PC command, if present,
// occupies half one and therefore wins the MCU's last_ping echo.
static void scope_batch2_prepare_tx(uint8_t *tx,uint32_t command,
                                    const uint8_t *pc_command,bool pending) {
    ping(tx,command & UINT32_C(0x7fffffff));
    if(pending) memcpy(tx+BLOCK,pc_command,BLOCK);
    else ping(tx+BLOCK,(command+1U) & UINT32_C(0x7fffffff));
}

// dual_feed mutates acquisition state, so stage the entire physical batch.
// Failure in half two must publish neither a new checker state nor TCP bytes.
static unsigned scope_batch2_validate(DualChecker *checker,const uint8_t *rx) {
    DualChecker staged=*checker;
    for(unsigned half=0;half<2;++half)
        if(!dual_feed(&staged,rx+half*BLOCK)) return half+1U;
    *checker=staged;
    return 0;
}

static bool scope_batch2_reconnect_guard(bool pending,uint32_t previous_tx,
                                         const uint8_t *rx) {
    return pending || (previous_tx & UINT32_C(0x80000000)) ||
           (get32(rx+16) & UINT32_C(0x80000000)) ||
           (get32(rx+BLOCK+16) & UINT32_C(0x80000000));
}
