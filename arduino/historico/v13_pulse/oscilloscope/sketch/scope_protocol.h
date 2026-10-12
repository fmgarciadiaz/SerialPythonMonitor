#pragma once
#include <stddef.h>
#include <stdint.h>

struct __attribute__((packed)) Sample {
    uint32_t timestamp;
    uint16_t adc_in;
    uint16_t adc_out;
};

struct __attribute__((packed)) Packet {
    char magic[4];
    uint8_t state;
    uint16_t count;
    Sample samples[SERIAL_BLOCK_PAIRS];
};

static_assert(sizeof(Sample) == 8U, "Contrato binario del monitor y del puente R4");
static_assert(offsetof(Packet, samples) == 7U, "Cabecera DATA de 7 bytes");
static_assert(sizeof(Packet) == 7U + SERIAL_BLOCK_PAIRS * 8U, "Sin padding en el paquete");
#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "El protocolo requiere little-endian"
#endif
