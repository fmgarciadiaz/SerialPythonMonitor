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
constexpr size_t BLOCK_BYTES = 992;
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
    static_assert(PAYLOAD_BYTES % 4 == 0, "PING groups require four bytes");
    static const uint32_t masks[PAYLOAD_BYTES/4]={
        0x8d7c6b5aU,0xd1c0af9eU,0x1504f3e2U,0x59483726U,0x9d8c7b6aU,0xe1d0bfaeU,0x251403f2U,0x69584736U,
        0xad9c8b7aU,0xf1e0cfbeU,0x35241302U,0x79685746U,0xbdac9b8aU,0x01f0dfceU,0x45342312U,0x89786756U,
        0xcdbcab9aU,0x1100efdeU,0x55443322U,0x99887766U,0xddccbbaaU,0x2110ffeeU,0x65544332U,0xa9988776U,
        0xeddccbbaU,0x31200ffeU,0x75645342U,0xb9a89786U,0xfdecdbcaU,0x41301f0eU,0x85746352U,0xc9b8a796U,
        0x0dfcebdaU,0x51402f1eU,0x95847362U,0xd9c8b7a6U,0x1d0cfbeaU,0x61503f2eU,0xa5948372U,0xe9d8c7b6U,
        0x2d1c0bfaU,0x71604f3eU,0xb5a49382U,0xf9e8d7c6U,0x3d2c1b0aU,0x81705f4eU,0xc5b4a392U,0x09f8e7d6U,
        0x4d3c2b1aU,0x91806f5eU,0xd5c4b3a2U,0x1908f7e6U,0x5d4c3b2aU,0xa1907f6eU,0xe5d4c3b2U,0x291807f6U,
        0x6d5c4b3aU,0xb1a08f7eU,0xf5e4d3c2U,0x39281706U,0x7d6c5b4aU,0xc1b09f8eU,0x05f4e3d2U,0x49382716U,
        0x8d7c6b5aU,0xd1c0af9eU,0x1504f3e2U,0x59483726U,0x9d8c7b6aU,0xe1d0bfaeU,0x251403f2U,0x69584736U,
        0xad9c8b7aU,0xf1e0cfbeU,0x35241302U,0x79685746U,0xbdac9b8aU,0x01f0dfceU,0x45342312U,0x89786756U,
        0xcdbcab9aU,0x1100efdeU,0x55443322U,0x99887766U,0xddccbbaaU,0x2110ffeeU,0x65544332U,0xa9988776U,
        0xeddccbbaU,0x31200ffeU,0x75645342U,0xb9a89786U,0xfdecdbcaU,0x41301f0eU,0x85746352U,0xc9b8a796U,
        0x0dfcebdaU,0x51402f1eU,0x95847362U,0xd9c8b7a6U,0x1d0cfbeaU,0x61503f2eU,0xa5948372U,0xe9d8c7b6U,
        0x2d1c0bfaU,0x71604f3eU,0xb5a49382U,0xf9e8d7c6U,0x3d2c1b0aU,0x81705f4eU,0xc5b4a392U,0x09f8e7d6U,
        0x4d3c2b1aU,0x91806f5eU,0xd5c4b3a2U,0x1908f7e6U,0x5d4c3b2aU,0xa1907f6eU,0xe5d4c3b2U,0x291807f6U,
        0x6d5c4b3aU,0xb1a08f7eU,0xf5e4d3c2U,0x39281706U,0x7d6c5b4aU,0xc1b09f8eU,0x05f4e3d2U,0x49382716U,
        0x8d7c6b5aU,0xd1c0af9eU,0x1504f3e2U,0x59483726U,0x9d8c7b6aU,0xe1d0bfaeU,0x251403f2U,0x69584736U,
        0xad9c8b7aU,0xf1e0cfbeU,0x35241302U,0x79685746U,0xbdac9b8aU,0x01f0dfceU,0x45342312U,0x89786756U,
        0xcdbcab9aU,0x1100efdeU,0x55443322U,0x99887766U,0xddccbbaaU,0x2110ffeeU,0x65544332U,0xa9988776U,
        0xeddccbbaU,0x31200ffeU,0x75645342U,0xb9a89786U,0xfdecdbcaU,0x41301f0eU,0x85746352U,0xc9b8a796U,
        0x0dfcebdaU,0x51402f1eU,0x95847362U,0xd9c8b7a6U,0x1d0cfbeaU,0x61503f2eU,0xa5948372U,0xe9d8c7b6U,
        0x2d1c0bfaU,0x71604f3eU,0xb5a49382U,0xf9e8d7c6U,0x3d2c1b0aU,0x81705f4eU,0xc5b4a392U,0x09f8e7d6U,
        0x4d3c2b1aU,0x91806f5eU,0xd5c4b3a2U,0x1908f7e6U,0x5d4c3b2aU,0xa1907f6eU,0xe5d4c3b2U,0x291807f6U,
        0x6d5c4b3aU,0xb1a08f7eU,0xf5e4d3c2U,0x39281706U,0x7d6c5b4aU,0xc1b09f8eU,0x05f4e3d2U,0x49382716U,
        0x8d7c6b5aU,0xd1c0af9eU,0x1504f3e2U,0x59483726U,0x9d8c7b6aU,0xe1d0bfaeU,0x251403f2U,0x69584736U,
        0xad9c8b7aU,0xf1e0cfbeU,0x35241302U,0x79685746U,0xbdac9b8aU,0x01f0dfceU,0x45342312U,0x89786756U,
        0xcdbcab9aU,0x1100efdeU,0x55443322U,0x99887766U,0xddccbbaaU,0x2110ffeeU,0x65544332U,0xa9988776U,
        0xeddccbbaU,0x31200ffeU,0x75645342U,0xb9a89786U,0xfdecdbcaU,0x41301f0eU,0x85746352U,0xc9b8a796U,
        0x0dfcebdaU,0x51402f1eU,0x95847362U,0xd9c8b7a6U,0x1d0cfbeaU,0x61503f2eU,0xa5948372U,0xe9d8c7b6U,
        0x2d1c0bfaU,0x71604f3eU,0xb5a49382U,0xf9e8d7c6U,0x3d2c1b0aU,0x81705f4eU,0xc5b4a392U,0x09f8e7d6U,
        0x4d3c2b1aU,0x91806f5eU,0xd5c4b3a2U,
    };
    for(size_t i=0;i<PAYLOAD_BYTES/4;++i) {
        uint32_t actual;
        __builtin_memcpy(&actual,p+HEADER_BYTES+i*4,4);
        // SCP1 and the STM32 are little endian; host contract checks this too.
#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
        actual=__builtin_bswap32(actual);
#endif
        if(actual!=(seed^masks[i]))return false;
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
