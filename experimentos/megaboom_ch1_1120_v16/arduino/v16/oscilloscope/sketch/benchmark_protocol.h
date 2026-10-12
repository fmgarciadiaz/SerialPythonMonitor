#pragma once
#include "crc32_fast.h"
#include <stddef.h>
#include <stdint.h>

// SCP1: campos little-endian explícitos, sin depender de padding de structs.
// Cabecera: magic[4], version u16, tipo u16, secuencia u32, longitud u32.
// CRC-32/ISO-HDLC: poly reflejado EDB88320, init/xorout FFFFFFFF, cabecera+payload.
#if defined(__GNUC__) && !defined(__clang__)
#define SCOPE_FAST_HOT __attribute__((optimize("O2")))
#else
#define SCOPE_FAST_HOT
#endif

namespace scope_bench {
constexpr size_t BLOCK_BYTES = 1120;
constexpr size_t HEADER_BYTES = 16;
constexpr size_t CRC_BYTES = 4;
constexpr size_t PAYLOAD_BYTES = BLOCK_BYTES - HEADER_BYTES - CRC_BYTES;
constexpr size_t STATUS_BYTES = 32;
constexpr uint16_t VERSION = 4;
constexpr uint16_t DATA = 1;
constexpr uint16_t PING = 2;

SCOPE_FAST_HOT inline void put16(uint8_t *p, uint16_t v) { p[0] = v; p[1] = v >> 8; }
SCOPE_FAST_HOT inline void put32(uint8_t *p, uint32_t v) {
    for (unsigned i = 0; i < 4; ++i) p[i] = v >> (8 * i);
}
SCOPE_FAST_HOT inline uint16_t get16(const uint8_t *p) { return uint16_t(p[0]) | (uint16_t(p[1]) << 8); }
SCOPE_FAST_HOT inline uint32_t get32(const uint8_t *p) {
    return uint32_t(p[0]) | (uint32_t(p[1]) << 8) |
           (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}
SCOPE_FAST_HOT inline uint32_t crc32(const uint8_t *p, size_t n) { return scope_crc_fast::compute(p,n); }
inline uint8_t pattern(uint32_t sequence, size_t i) {
    const uint32_t seed = sequence * 0x9E3779B1U;
    return uint8_t((seed >> (8 * (i & 3))) ^ (i * 17 + 0x5A));
}
inline void seal(uint8_t *p) { put32(p + BLOCK_BYTES - CRC_BYTES, crc32(p, BLOCK_BYTES - CRC_BYTES)); }
SCOPE_FAST_HOT inline void frame(uint8_t *p, uint16_t type, uint32_t sequence) {
    p[0]='S'; p[1]='C'; p[2]='P'; p[3]='1';
    put16(p+4, VERSION); put16(p+6, type);
    put32(p+8, sequence); put32(p+12, PAYLOAD_BYTES);
    for (size_t i=0; i<PAYLOAD_BYTES; ++i) p[HEADER_BYTES+i] = pattern(sequence, i);
}
SCOPE_FAST_HOT inline bool valid_ping(const uint8_t *p) {
    if (p[0]!='S' || p[1]!='C' || p[2]!='P' || p[3]!='1' ||
        get16(p+4)!=VERSION || get16(p+6)!=PING || get32(p+12)!=PAYLOAD_BYTES ||
        get32(p+BLOCK_BYTES-CRC_BYTES)!=crc32(p, BLOCK_BYTES-CRC_BYTES)) return false;
    const uint32_t seed = get32(p+8) * 0x9E3779B1U;
    const uint8_t s0 = uint8_t(seed), s1 = uint8_t(seed >> 8);
    const uint8_t s2 = uint8_t(seed >> 16), s3 = uint8_t(seed >> 24);
    static_assert(PAYLOAD_BYTES % 4 == 0, "PING groups require four bytes");
    for (size_t i=0; i<PAYLOAD_BYTES; i+=4) {
        if (p[HEADER_BYTES+i] != uint8_t(s0 ^ (i*17+0x5A)) ||
            p[HEADER_BYTES+i+1] != uint8_t(s1 ^ ((i+1)*17+0x5A)) ||
            p[HEADER_BYTES+i+2] != uint8_t(s2 ^ ((i+2)*17+0x5A)) ||
            p[HEADER_BYTES+i+3] != uint8_t(s3 ^ ((i+3)*17+0x5A))) return false;
    }
    return true;
}
// DATA payload: último PING válido, errores SPI, PING inválidos,
// transferencias cortas, último retorno y error persistente (int32), tiempos
// anteriores de preparación y verificación en us; luego patrón.
SCOPE_FAST_HOT inline void data_frame(uint8_t *p, uint32_t sequence, uint32_t last_ping,
                       uint32_t errors, uint32_t bad_ping, uint32_t short_transfer,
                       int32_t last_result, int32_t last_error = 0,
                       uint32_t prepare_us = 0, uint32_t check_us = 0) {
    // Metadata is filled before sealing once in loop(); no synthetic payload.
    p[0]='S'; p[1]='C'; p[2]='P'; p[3]='1';
    put16(p+4, VERSION); put16(p+6, DATA);
    put32(p+8,sequence); put32(p+12,PAYLOAD_BYTES);
    put32(p+16, last_ping); put32(p+20, errors); put32(p+24, bad_ping);
    put32(p+28, short_transfer); put32(p+32, uint32_t(last_result));
    put32(p+36, uint32_t(last_error));
    put32(p+40, prepare_us); put32(p+44, check_us);
}
} // namespace scope_bench
#undef SCOPE_FAST_HOT
