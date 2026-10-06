#pragma once
#include <stddef.h>
#include <stdint.h>

// SCP1: campos little-endian explícitos, sin depender de padding de structs.
// Cabecera: magic[4], version u16, tipo u16, secuencia u32, longitud u32.
// CRC-32/ISO-HDLC: poly reflejado EDB88320, init/xorout FFFFFFFF, cabecera+payload.
namespace scope_bench {
constexpr size_t BLOCK_BYTES = 512;
constexpr size_t HEADER_BYTES = 16;
constexpr size_t CRC_BYTES = 4;
constexpr size_t PAYLOAD_BYTES = BLOCK_BYTES - HEADER_BYTES - CRC_BYTES;
constexpr size_t STATUS_BYTES = 32;
constexpr uint16_t VERSION = 2;
constexpr uint16_t DATA = 1;
constexpr uint16_t PING = 2;

inline void put16(uint8_t *p, uint16_t v) { p[0] = v; p[1] = v >> 8; }
inline void put32(uint8_t *p, uint32_t v) {
    for (unsigned i = 0; i < 4; ++i) p[i] = v >> (8 * i);
}
inline uint16_t get16(const uint8_t *p) { return uint16_t(p[0]) | (uint16_t(p[1]) << 8); }
inline uint32_t get32(const uint8_t *p) {
    return uint32_t(p[0]) | (uint32_t(p[1]) << 8) |
           (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}
inline uint32_t crc32(const uint8_t *p, size_t n) {
    static const uint32_t table[16] = {
        0x00000000U, 0x1DB71064U, 0x3B6E20C8U, 0x26D930ACU,
        0x76DC4190U, 0x6B6B51F4U, 0x4DB26158U, 0x5005713CU,
        0xEDB88320U, 0xF00F9344U, 0xD6D6A3E8U, 0xCB61B38CU,
        0x9B64C2B0U, 0x86D3D2D4U, 0xA00AE278U, 0xBDBDF21CU
    };
    uint32_t crc = 0xFFFFFFFFU;
    for (size_t i = 0; i < n; ++i) {
        crc ^= p[i];
        crc = (crc >> 4) ^ table[crc & 15];
        crc = (crc >> 4) ^ table[crc & 15];
    }
    return crc ^ 0xFFFFFFFFU;
}
inline uint8_t pattern(uint32_t sequence, size_t i) {
    const uint32_t seed = sequence * 0x9E3779B1U;
    return uint8_t((seed >> (8 * (i & 3))) ^ (i * 17 + 0x5A));
}
inline void seal(uint8_t *p) { put32(p + BLOCK_BYTES - CRC_BYTES, crc32(p, BLOCK_BYTES - CRC_BYTES)); }
inline void frame(uint8_t *p, uint16_t type, uint32_t sequence) {
    p[0]='S'; p[1]='C'; p[2]='P'; p[3]='1';
    put16(p+4, VERSION); put16(p+6, type);
    put32(p+8, sequence); put32(p+12, PAYLOAD_BYTES);
    for (size_t i=0; i<PAYLOAD_BYTES; ++i) p[HEADER_BYTES+i] = pattern(sequence, i);
}
inline bool valid_ping(const uint8_t *p) {
    if (p[0]!='S' || p[1]!='C' || p[2]!='P' || p[3]!='1' ||
        get16(p+4)!=VERSION || get16(p+6)!=PING || get32(p+12)!=PAYLOAD_BYTES ||
        get32(p+BLOCK_BYTES-CRC_BYTES)!=crc32(p, BLOCK_BYTES-CRC_BYTES)) return false;
    const uint32_t sequence = get32(p+8);
    for (size_t i=0; i<PAYLOAD_BYTES; ++i)
        if (p[HEADER_BYTES+i]!=pattern(sequence, i)) return false;
    return true;
}
// DATA payload: último PING válido, errores SPI, PING inválidos,
// transferencias cortas, último retorno y error persistente (int32), tiempos
// anteriores de preparación y verificación en us; luego patrón.
inline void data_frame(uint8_t *p, uint32_t sequence, uint32_t last_ping,
                       uint32_t errors, uint32_t bad_ping, uint32_t short_transfer,
                       int32_t last_result, int32_t last_error = 0,
                       uint32_t prepare_us = 0, uint32_t check_us = 0) {
    frame(p, DATA, sequence);
    put32(p+16, last_ping); put32(p+20, errors); put32(p+24, bad_ping);
    put32(p+28, short_transfer); put32(p+32, uint32_t(last_result));
    put32(p+36, uint32_t(last_error));
    put32(p+40, prepare_us); put32(p+44, check_us);
    seal(p);
}
} // namespace scope_bench
