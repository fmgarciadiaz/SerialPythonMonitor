"""Exact, private WAV validation experiment; never edits the accepted sketch."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKETCH = ROOT / 'arduino/v19/oscilloscope/sketch'
ENTRY = '''SCOPE_WAV_FAST static scope_wav::Reply submit(const scope_wav::Request &r) {
    const unsigned key=irq_lock();'''
LOOP = '            for(unsigned i=0;i<r.count;++i) if(scope_wav::get16(r.samples+2*i)>4095) reason=scope_control::UNSUPPORTED;'
PRECHECK = '''SCOPE_WAV_FAST static scope_wav::Reply submit(const scope_wav::Request &r) {
    // rx_batch remains stable until this synchronous submission returns.
    // DMA descriptors and queue ownership still change only under irq_lock.
    bool samples_supported=true;
    if(r.chunk && r.count<=scope_wav::POINTS && r.samples) {
        for(unsigned i=0;i<r.count;++i) if(scope_wav::get16(r.samples+2*i)>4095) samples_supported=false;
    }
    const unsigned key=irq_lock();'''


def candidate_text(original):
    """Fail closed if the reviewed baseline no longer has its exact anchors."""
    if original.count(ENTRY) != 1 or original.count(LOOP) != 1:
        raise ValueError('Expected unique accepted WAV submit and validation loop')
    return original.replace(ENTRY, PRECHECK).replace(
        LOOP, '            if(!samples_supported) reason=scope_control::UNSUPPORTED;')
