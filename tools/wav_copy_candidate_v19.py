"""Exact private PCM copy replacement, independent of timing instrumentation."""
LOOP='    for(unsigned i=0;i<count;++i) data[slot*scope_wav::POINTS+i]=scope_wav::get16(p+2*i);'
REPLACEMENT='''    static_assert(__BYTE_ORDER__==__ORDER_LITTLE_ENDIAN__,"PCM wire copy requires little endian MCU");
    memcpy(data+slot*scope_wav::POINTS,p,count*sizeof(uint16_t));'''


def candidate_text(original):
    if original.count(LOOP)!=1:raise ValueError('Unique accepted PCM copy loop required')
    return original.replace(LOOP,REPLACEMENT)


def variants(originals):
    from tools.wav_timing_candidate_v19 import candidate_sources
    plain=dict(originals);plain['wav_dma.h']=candidate_text(originals['wav_dma.h'])
    timed=candidate_sources(originals);timed['wav_dma.h']=candidate_text(timed['wav_dma.h'])
    return {'candidate_wav_copy':plain,'candidate_wav_timing_copy':timed}
