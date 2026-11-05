#pragma once
#include <stdint.h>
#if !defined(__BYTE_ORDER__) || __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "SPI16 direct byte buffers require a little-endian Linux host"
#endif
enum { SCOPE_SPI16_BITS = 16, SCOPE_SPI16_BLOCK_BYTES = 992,
       SCOPE_SPI16_WORDS = SCOPE_SPI16_BLOCK_BYTES / 2 };
_Static_assert(SCOPE_SPI16_BLOCK_BYTES % 4 == 0 && SCOPE_SPI16_WORDS == 496,
               "SCP1 must be exactly one even-length SPI16 transfer");
