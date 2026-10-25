"""Generate the private two-SCP-per-physical-SPI16-transfer experiment."""
import json
import shutil
from pathlib import Path

EXP = Path(__file__).resolve().parent
OUT = EXP / 'batch2'


def replace_once(path,old,new):
    source=path.read_text()
    if source.count(old)!=1:
        raise ValueError(f'{path}: expected one occurrence of {old!r}')
    path.write_text(source.replace(old,new))


def prepare():
    for name in ('oscilloscope', 'relay'):
        shutil.copytree(EXP / 'spi16' / name, OUT / name, dirs_exist_ok=True)
    shutil.copyfile(EXP / 'spi16/candidate_profiles.json', OUT / 'candidate_profiles.json')
    sketch = OUT / 'oscilloscope/sketch/sketch.ino'
    geometry = sketch.parent / 'spi16_geometry.h'
    replace_once(geometry, 'constexpr uint32_t transfer_words(size_t bytes) { return uint32_t(bytes / 2U); }',
                 'constexpr size_t physical_bytes = 2U * 992U;\n'
                 'constexpr int logical_result(int physical_result) {\n'
                 '    return physical_result == int(physical_bytes) ? 992 : physical_result;\n'
                 '}\n'
                 'constexpr uint32_t transfer_words(size_t bytes) { return uint32_t(bytes / 2U); }')
    replace_once(geometry, 'static_assert(transfer_words(992U) == 496U && transfer_words(992U) <= 1023U,\n'
                 '              "One SCP frame must fit SPI3 TSIZE");',
                 'static_assert(transfer_words(physical_bytes) == 992U && transfer_words(physical_bytes) <= 1023U,\n'
                 '              "Two SCP frames must fit SPI3 TSIZE");')
    replace_once(sketch, '#include "spi16_geometry.h"',
                 '#include "spi16_geometry.h"\n#include "batch2_ownership.h"')
    replace_once(sketch, 'static_assert(BLOCK_BYTES % 32 == 0, "DMA frame alignment");',
                 'static_assert(scope_spi16::physical_bytes % 32 == 0, "DMA batch alignment");')
    replace_once(sketch, 'scope_spi16::transfer_words(BLOCK_BYTES) <= 1023',
                 'scope_spi16::transfer_words(scope_spi16::physical_bytes) <= 1023')
    replace_once(sketch, 'static_assert(BLOCK_BYTES % CONFIG_DCACHE_LINE_SIZE == 0, "DMA cache alignment");',
                 'static_assert(scope_spi16::physical_bytes % CONFIG_DCACHE_LINE_SIZE == 0, "DMA cache alignment");')
    replace_once(sketch, 'static uint8_t *tx;\nstatic uint8_t *active_tx;',
                 'static uint8_t *active_tx;\nstatic uint8_t *physical_rx;\n'
                 'static bool batch_dma_word=false, batch_dma_high=false;')
    replace_once(sketch, 'const uint8_t *tx_buffer=high_rate_transport()?active_tx:tx;',
                 'const uint8_t *tx_buffer=active_tx;')
    replace_once(sketch, 'const unsigned bytes = scope_spi16::dma_bytes(word_transport());',
                 'const unsigned bytes = scope_spi16::dma_bytes(batch_dma_word);')
    replace_once(sketch, 'if (high_rate_transport() && saved.initialized && saved.bytes==bytes)',
                 'if (batch_dma_high && saved.initialized && saved.bytes==bytes)')
    replace_once(sketch, 'channel->CBR1 = BLOCK_BYTES;',
                 'channel->CBR1 = scope_spi16::physical_bytes;')
    replace_once(sketch, 'block.block_size = BLOCK_BYTES;',
                 'block.block_size = scope_spi16::physical_bytes;')
    replace_once(sketch, 'saved.initialized = high_rate_transport();',
                 'saved.initialized = batch_dma_high;')
    replace_once(sketch, 'cache_flush_invalidate(high_rate_transport()?active_tx:tx, BLOCK_BYTES);',
                 'cache_flush_invalidate(active_tx, scope_spi16::physical_bytes);')
    replace_once(sketch, 'cache_flush_invalidate(rx, BLOCK_BYTES);',
                 'cache_flush_invalidate(physical_rx, scope_spi16::physical_bytes);')
    replace_once(sketch, 'SPI3->CR2 = scope_spi16::transfer_words(BLOCK_BYTES);',
                 'SPI3->CR2 = scope_spi16::transfer_words(scope_spi16::physical_bytes);')
    replace_once(sketch, 'scope_spi16::fifo_threshold_field(word_transport()) << SPI_CFG1_FTHLV_Pos',
                 'scope_spi16::fifo_threshold_field(batch_dma_word) << SPI_CFG1_FTHLV_Pos')
    replace_once(sketch, '? int(BLOCK_BYTES) : -EMSGSIZE);',
                 '? int(scope_spi16::physical_bytes) : -EMSGSIZE);')
    replace_once(sketch, 'rx_dma->CBR1 != BLOCK_BYTES;',
                 'rx_dma->CBR1 != scope_spi16::physical_bytes;')
    replace_once(sketch, 'cache_invalidate(rx, BLOCK_BYTES);',
                 'cache_invalidate(physical_rx, scope_spi16::physical_bytes);')
    replace_once(sketch, 'channel->CDAR = transmit ? reinterpret_cast<uint32_t>(&SPI3->TXDR)\n'
                 '                                : reinterpret_cast<uint32_t>(rx);',
                 'channel->CDAR = transmit ? reinterpret_cast<uint32_t>(&SPI3->TXDR)\n'
                 '                                : reinterpret_cast<uint32_t>(physical_rx);')
    replace_once(sketch, 'reinterpret_cast<uint32_t>(rx);\n    block.source_addr_adj',
                 'reinterpret_cast<uint32_t>(physical_rx);\n    block.source_addr_adj')
    # Replace the old single-frame loop with real two-half preparation and
    # commit-after-physical-success ownership. The queue producer remains intact.
    source = sketch.read_text()
    start = source.index('void loop() {')
    source = source[:start] + (EXP / 'batch2_loop.inc').read_text()
    sketch.write_text(source)
    (sketch.parent / 'batch2_ownership.h').write_text((EXP / 'batch2_ownership.inc').read_text())

    relay = OUT / 'relay/unoq_config_stream.c'
    source = relay.read_text()
    source = source.replace('#include "spi16_contract.h"',
                            '#include "spi16_contract.h"\n#include "batch2_relay.h"')
    source = source.replace('uint8_t tx[BLOCK],rx[BLOCK];',
                            'uint8_t tx[SCOPE_BATCH2_BYTES],rx[SCOPE_BATCH2_BYTES];')
    source = source.replace('.len=BLOCK,.speed_hz=hz,.bits_per_word=SCOPE_SPI16_BITS',
                            '.len=SCOPE_BATCH2_BYTES,.speed_hz=hz,.bits_per_word=SCOPE_SPI16_BITS')
    source = source.replace('    while (running) {\n        if (pending) { memcpy(tx,pc_command,BLOCK); pending=false; }\n'
                            '        else ping(tx,command & UINT32_C(0x7fffffff)); // Upper half reserved for PC requests.',
                            '    while (running) {\n'
                            '        scope_batch2_prepare_tx(tx,command,pc_command,pending); pending=false;')
    source = source.replace('if(get16(tx+6)==6)', 'if(get16(tx+BLOCK+6)==6)')
    source = source.replace('tx[16],get32(tx+20)', 'tx[BLOCK+16],get32(tx+BLOCK+20)')
    source = source.replace('get16(tx+6)==6?scope_native_find',
                            'get16(tx+BLOCK+6)==6?scope_native_find')
    source = source.replace('if (ioctl(fd,SPI_IOC_MESSAGE(1),&transfer)!=BLOCK)',
                            'if (ioctl(fd,SPI_IOC_MESSAGE(1),&transfer)!=SCOPE_BATCH2_BYTES)')
    first = source.index('        DualChecker before=checker;')
    end = source.index('        const ScopeNativeProfile *profile=', first)
    source = source[:first] + '''        DualChecker before=checker;
        unsigned bad_half=scope_batch2_validate(&checker,rx);
        if (bad_half) {
            const uint8_t *bad=rx+(bad_half-1U)*BLOCK;
            fprintf(stderr,"Batch2 integrity failure half=%u seq=%" PRIu32
                    " kind=%u crc_received=%08" PRIx32 " crc_calculated=%08" PRIx32
                    " previous_seq=%" PRIu32 "\\n",bad_half,get32(bad+8),
                    get16(bad+6),get32(bad+988),crc32(bad,988),before.sequence);
            fprintf(stderr,"Batch2 rejected frame (hex): ");
            for(unsigned i=0;i<BLOCK;++i)fprintf(stderr,"%02x",bad[i]);
            fputc('\\n',stderr);
            goto done;
        }
''' + source[end:]
    source = source.replace('if(get16(rx+6)==7 && (rx[22]==2 || rx[22]==3)) {spi40_pending=false;cpu_pending=false;}',
                            'for (unsigned half=0;half<2;++half) {\n'
                            '            const uint8_t *frame=rx+half*BLOCK;\n'
                            '            if(get16(frame+6)==7 && (frame[22]==2 || frame[22]==3))\n'
                            '                {spi40_pending=false;cpu_pending=false;}\n'
                            '        }')
    source = source.replace('previous_tx=get32(tx+8);\n        ++command;',
                            'previous_tx=get32(tx+BLOCK+8);\n        command+=2;')
    source = source.replace('if (client<0 && (pending || (previous_tx & UINT32_C(0x80000000)) ||\n'
                            '                         (get32(rx+16) & UINT32_C(0x80000000)))) continue;',
                            'if (client<0 && scope_batch2_reconnect_guard(pending,previous_tx,rx)) continue;')
    start = source.index('        if (client>=0) {\n            // Bound backpressure:')
    end = source.index('        if (now()-progress>=10)',start)
    source = source[:start] + '''        if (client>=0) {
            // Validation of both halves already committed before either is sent.
            for (unsigned half=0;half<2;++half) {
                const uint8_t *frame=rx+half*BLOCK;
                ssize_t sent;
                if(cpu || send_queue.count) {
                    if(scope_send_frame(&send_queue,client,frame,send)<0)sent=-1;
                    else sent=BLOCK;
                } else sent=send(client,frame,BLOCK,MSG_DONTWAIT|MSG_NOSIGNAL);
                if (sent!=BLOCK) {
                    fprintf(stderr,"PC disconnected or too slow; close session (sent=%zd)\\n",sent);
                    close(client); client=-1; break;
                }
            }
        }
''' + source[end:]
    relay.write_text(source)
    (relay.parent / 'batch2_relay.h').write_text((EXP / 'batch2_relay.inc').read_text())
    verifier = OUT / 'relay/base_verifier.c'
    replace_once(verifier,
                 '    if (seconds<=0 || gap<0 || gap>1e9 || minimum<=0 || (ready_chip && (gap!=0 || replay))) return 2;',
                 '    if (seconds<=0 || gap<0 || gap>1e9 || minimum<=0 || (ready_chip && (gap!=0 || replay))) return 2;\n'
                 '    if (!replay) { fprintf(stderr,"Batch2: benchmark físico standalone deshabilitado; usar relay batch2.\\n"); return 2; }')
    app = OUT / 'oscilloscope/app.yaml'
    replace_once(app, 'name: Scope V18 Rate Probe SPI16', 'name: Scope V18 Rate Probe Batch2')
    main = OUT / 'oscilloscope/python/main.py'
    replace_once(main, 'Scope V18 Rate Probe SPI16: SCP1 V4/992, app experimental privada.',
                 'Scope V18 Rate Probe Batch2: 2 x SCP1 V4/992, app experimental privada.')
    (OUT / 'recipe.json').write_text(json.dumps(dict(name='batch2',base='spi16',
        app='Scope V18 Rate Probe Batch2',logical_block_bytes=992,
        physical_bytes=1984,spi_bits=16,transfer_words=992,
        transfers_per_batch=1,frames_per_batch=2,validation='unmeasured'),indent=2)+'\n')


if __name__ == '__main__':
    prepare()
