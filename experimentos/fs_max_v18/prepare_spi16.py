"""Generate the isolated, always-SPI16 single-SCP-frame probe from wordping."""
import json
import shutil
from pathlib import Path

EXP = Path(__file__).resolve().parent
OUT = EXP / 'spi16'


def replace_once(path, old, new):
    source = path.read_text()
    if source.count(old) != 1:
        raise ValueError(f'{path}: expected one occurrence of {old!r}')
    path.write_text(source.replace(old, new))


def prepare():
    for name in ('oscilloscope', 'relay'):
        shutil.copytree(EXP / 'wordping' / name, OUT / name, dirs_exist_ok=True)
    shutil.copyfile(EXP / 'wordping' / 'candidate_profiles.json', OUT / 'candidate_profiles.json')

    sketch = OUT / 'oscilloscope/sketch/sketch.ino'
    replace_once(sketch, '#include "frame_buffer.h"', '#include "frame_buffer.h"\n#include "spi16_geometry.h"')
    replace_once(sketch, 'static_assert(BLOCK_BYTES <= 1023, "SPI3 tiene TSIZE limitado a 10 bits");',
                 'static_assert(scope_spi16::transfer_words(BLOCK_BYTES) <= 1023, "SPI3 TSIZE de 10 bits");')
    replace_once(sketch, 'const unsigned bytes = word_transport()?4U:1U;',
                 'const unsigned bytes = scope_spi16::dma_bytes(word_transport());')
    replace_once(sketch, 'channel->CTR1 = (bytes==4 ? (2U << DMA_CTR1_SDW_LOG2_Pos) | (2U << DMA_CTR1_DDW_LOG2_Pos) : 0U) |',
                 'channel->CTR1 = ((bytes==4 ? 2U : 1U) << DMA_CTR1_SDW_LOG2_Pos) |\n'
                 '        ((bytes==4 ? 2U : 1U) << DMA_CTR1_DDW_LOG2_Pos) |')
    replace_once(sketch, '// Mantener los puertos RAM/SPI del ensayo anterior, transferencias de byte.',
                 '// Mantener puertos RAM/SPI; accesos de 2 o 4 bytes para tramas SPI16.')
    replace_once(sketch, 'SPI3->CR2 = BLOCK_BYTES;',
                 'SPI3->CR2 = scope_spi16::transfer_words(BLOCK_BYTES);')
    replace_once(sketch, 'SPI3->CFG1 = 7U | (7U << SPI_CFG1_CRCSIZE_Pos) |\n'
                 '        ((word_transport()?3U:0U) << SPI_CFG1_FTHLV_Pos) | SPI_CFG1_RXDMAEN | SPI_CFG1_TXDMAEN;',
                 'SPI3->CFG1 = scope_spi16::data_size_field |\n'
                 '        (scope_spi16::crc_size_field << SPI_CFG1_CRCSIZE_Pos) |\n'
                 '        (scope_spi16::fifo_threshold_field(word_transport()) << SPI_CFG1_FTHLV_Pos) |\n'
                 '        SPI_CFG1_RXDMAEN | SPI_CFG1_TXDMAEN;')
    replace_once(sketch, 'SPI3->CFG1 = 7U; // DSIZE=8 bits, FTHLV=1 byte, CRC y DMA deshabilitados.',
                 'SPI3->CFG1 = scope_spi16::data_size_field |\n'
                 '        (scope_spi16::crc_size_field << SPI_CFG1_CRCSIZE_Pos); // SPI16 desde el arranque.')
    (sketch.parent / 'spi16_geometry.h').write_text('''#pragma once
#include <cstddef>
#include <cstdint>

#if !defined(__BYTE_ORDER__) || __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "SPI16 direct byte buffers require a little-endian MCU"
#endif

namespace scope_spi16 {
constexpr uint32_t data_size_field = 15U; // DSIZE=16 bits.
constexpr uint32_t crc_size_field = 15U;  // Valid even while CRC is disabled.
constexpr uint32_t transfer_words(size_t bytes) { return uint32_t(bytes / 2U); }
constexpr unsigned dma_bytes(bool high_rate_word) { return high_rate_word ? 4U : 2U; }
constexpr uint32_t fifo_threshold_field(bool high_rate_word) {
    return high_rate_word ? 1U : 0U; // FTHLV: two or one 16-bit frames.
}
static_assert(992U % 4U == 0U, "SCP frame must suit both DMA access widths");
static_assert(transfer_words(992U) == 496U && transfer_words(992U) <= 1023U,
              "One SCP frame must fit SPI3 TSIZE");
static_assert(dma_bytes(false) == 2U && dma_bytes(true) == 4U,
              "Normal and high-rate GPDMA access widths");
static_assert(fifo_threshold_field(false) == 0U && fifo_threshold_field(true) == 1U,
              "FIFO thresholds match one and two halfwords");
}
''')

    relay = OUT / 'relay/unoq_config_stream.c'
    replace_once(relay, '#include "transport_policy.h"', '#include "transport_policy.h"\n#include "spi16_contract.h"')
    replace_once(relay, 'uint8_t mode=0,bits=8; uint32_t hz=32000000;',
                 'uint8_t mode=0,bits=SCOPE_SPI16_BITS,read_bits=0; uint32_t hz=32000000;')
    replace_once(relay, 'ioctl(fd,SPI_IOC_WR_BITS_PER_WORD,&bits)<0 || ioctl(fd,SPI_IOC_WR_MAX_SPEED_HZ,&hz)<0)',
                 'ioctl(fd,SPI_IOC_WR_BITS_PER_WORD,&bits)<0 ||\n'
                 '        ioctl(fd,SPI_IOC_RD_BITS_PER_WORD,&read_bits)<0 ||\n'
                 '        ioctl(fd,SPI_IOC_WR_MAX_SPEED_HZ,&hz)<0)')
    replace_once(relay, '        perror("SPI"); goto done;\n    }',
                 '        perror("SPI"); goto done;\n    }\n'
                 '    if (read_bits!=SCOPE_SPI16_BITS) {\n'
                 '        fprintf(stderr,"SPI bits readback=%u, expected 16\\n",read_bits); goto done;\n'
                 '    }')
    replace_once(relay, '.len=BLOCK,.speed_hz=hz,.bits_per_word=8};',
                 '.len=BLOCK,.speed_hz=hz,.bits_per_word=SCOPE_SPI16_BITS};')
    replace_once(relay, 'SPI 32 MHz, SCP1 dual ADC/control', 'SPI16 32 MHz, SCP1 dual ADC/control')
    (relay.parent / 'spi16_contract.h').write_text('''#pragma once
#include <stdint.h>
#if !defined(__BYTE_ORDER__) || __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "SPI16 direct byte buffers require a little-endian Linux host"
#endif
enum { SCOPE_SPI16_BITS = 16, SCOPE_SPI16_BLOCK_BYTES = 992,
       SCOPE_SPI16_WORDS = SCOPE_SPI16_BLOCK_BYTES / 2 };
_Static_assert(SCOPE_SPI16_BLOCK_BYTES % 4 == 0 && SCOPE_SPI16_WORDS == 496,
               "SCP1 must be exactly one even-length SPI16 transfer");
''')

    verifier = OUT / 'relay/base_verifier.c'
    replace_once(verifier, '#include <time.h>', '#include <time.h>\n#include "spi16_contract.h"')
    replace_once(verifier, 'uint8_t mode=0, bits=8;',
                 'uint8_t mode=0, bits=SCOPE_SPI16_BITS, read_bits=0;')
    replace_once(verifier, 'ioctl(fd,SPI_IOC_WR_BITS_PER_WORD,&bits)<0 || ioctl(fd,SPI_IOC_WR_MAX_SPEED_HZ,&hz)<0 ||',
                 'ioctl(fd,SPI_IOC_WR_BITS_PER_WORD,&bits)<0 ||\n'
                 '            ioctl(fd,SPI_IOC_RD_BITS_PER_WORD,&read_bits)<0 ||\n'
                 '            ioctl(fd,SPI_IOC_WR_MAX_SPEED_HZ,&hz)<0 ||')
    replace_once(verifier, 'perror("configure SPI"); close(fd); return 2; }',
                 'perror("configure SPI"); close(fd); return 2; }\n'
                 '        if (read_bits!=SCOPE_SPI16_BITS) {\n'
                 '            fprintf(stderr,"SPI bits readback=%u, expected 16\\n",read_bits);\n'
                 '            close(fd); return 2;\n'
                 '        }')
    replace_once(verifier, 'transfer.len=BLOCK; transfer.speed_hz=hz; transfer.bits_per_word=8;',
                 'transfer.len=BLOCK; transfer.speed_hz=hz; transfer.bits_per_word=SCOPE_SPI16_BITS;')

    app = OUT / 'oscilloscope/app.yaml'
    replace_once(app, 'name: Scope V17', 'name: Scope V18 Rate Probe SPI16')
    main = OUT / 'oscilloscope/python/main.py'
    replace_once(main, 'Scope V17: usar Monitor V17 y relay V16 SCP1 V4/992.',
                 'Scope V18 Rate Probe SPI16: SCP1 V4/992, app experimental privada.')
    (OUT / 'recipe.json').write_text(json.dumps(dict(name='spi16', base='wordping',
        app='Scope V18 Rate Probe SPI16', block_bytes=992, spi_bits=16,
        transfer_words=496, transfers_per_frame=1, validation='unmeasured'), indent=2) + '\n')


if __name__ == '__main__':
    prepare()
