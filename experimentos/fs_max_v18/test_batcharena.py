"""BatchArena source isolation and real union geometry under ASan/UBSan.

These host tests do not establish physical timing, transport, or rate acceptance.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

from experimentos.fs_max_v18.prepare_batcharena import EXP, prepare


SIZE = r'''
#include <cstdint>
#include <cstdio>
constexpr unsigned SERIAL_BLOCK_PAIRS=512;
#include "acquisition_storage.h"
int main() { std::printf("%zu\n", sizeof(scope_storage::Storage)); }
'''

GEOMETRY = r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <new>
constexpr unsigned SERIAL_BLOCK_PAIRS=512;
#include "acquisition_storage.h"
using namespace scope_storage;
static_assert(sizeof(DualMemory)==135616U, "Expected dual tail geometry");
static_assert(sizeof(SingleMemory)==163840U, "Preserve single arena geometry");
static_assert(sizeof(Memory)==163840U, "No new arena BSS");
static_assert(offsetof(DualMemory,timestamps)==33408U, "Timestamp DMA unchanged");
static_assert(offsetof(DualMemory,samples)==66816U, "Sample nodes unchanged");
static_assert(offsetof(DualMemory,spi_scratch)==133632U, "Scratch is final member");
struct alignas(32) Guarded {
    uint8_t before[64];
    Storage storage;
    uint8_t after[64];
};
void bytes_are(const void *p,size_t n,uint8_t wanted) {
    auto *bytes=static_cast<const uint8_t *>(p);
    for(size_t i=0;i<n;++i) assert(bytes[i]==wanted);
}
void guards(const Guarded &g) {
    bytes_are(g.before,sizeof(g.before),0x5a);
    bytes_are(g.after,sizeof(g.after),0xa5);
}
void disjoint(const void *a,size_t an,const void *b,size_t bn) {
    const auto av=reinterpret_cast<uintptr_t>(a),bv=reinterpret_cast<uintptr_t>(b);
    assert(av+an<=bv || bv+bn<=av);
}
void dual(Guarded &g,unsigned bits,unsigned pairs) {
    auto &s=g.storage;
    s.bind(false,slots,pairs);
    auto &m=s.memory.dual;
    assert(s.adc==m.adc && s.timestamps==m.timestamps);
    std::memset(m.adc,0x12,sizeof(m.adc));
    std::memset(m.timestamps,0x34,sizeof(m.timestamps));
    std::memset(m.samples,0x56,sizeof(m.samples));
    const unsigned mask=(1U<<bits)-1U;
    for(unsigned node=0;node<slots;++node) {
        assert(s.at(node).samples==m.samples[node]);
        assert(s.at(node).single_samples==nullptr);
        for(unsigned j=0;j<pairs;++j) {
            m.samples[node][j].ch1=(node*31U+j)&mask;
            m.samples[node][j].ch2=(node*43U+j*7U)&mask;
        }
    }
    for(unsigned slot=0;slot<2;++slot) {
        auto *frame=&m.spi_scratch[slot];
        assert(reinterpret_cast<uintptr_t>(frame)%alignof(SampleFrame)==0U);
        disjoint(frame,sizeof(*frame),m.adc,sizeof(m.adc));
        disjoint(frame,sizeof(*frame),m.timestamps,sizeof(m.timestamps));
        disjoint(frame,sizeof(*frame),m.samples,sizeof(m.samples));
        std::memset(frame->bytes,0xc0+slot,sizeof(frame->bytes));
    }
    disjoint(&m.spi_scratch[0],sizeof(SampleFrame),&m.spi_scratch[1],sizeof(SampleFrame));
    bytes_are(m.adc,sizeof(m.adc),0x12);
    bytes_are(m.timestamps,sizeof(m.timestamps),0x34);
    for(unsigned node=0;node<slots;++node) {
        for(unsigned j=0;j<pairs;++j) {
            assert(m.samples[node][j].ch1==((node*31U+j)&mask));
            assert(m.samples[node][j].ch2==((node*43U+j*7U)&mask));
        }
        bytes_are(m.samples[node]+pairs,(SCOPE_NATIVE_MAX_DUAL-pairs)*sizeof(ChannelPair),0x56);
    }
    // DMA writes at both ends must also leave the two scratch frames intact.
    m.adc[0]=0x7777;m.adc[SCOPE_NATIVE_MAX_DUAL*4U-1U]=0x8888;
    m.timestamps[0]=0x99999999;m.timestamps[SCOPE_NATIVE_MAX_DUAL*2U-1U]=0xaaaaaaaa;
    for(unsigned slot=0;slot<2;++slot)
        bytes_are(m.spi_scratch[slot].bytes,sizeof(SampleFrame),0xc0+slot);
    guards(g);
}
void single(Guarded &g) {
    auto &s=g.storage;
    constexpr unsigned pairs=3488;
    s.bind(true,max_slots,pairs);
    auto &m=s.memory.single;
    assert(s.adc==m.adc && s.timestamps==m.timestamps);
    std::memset(m.adc,0x21,sizeof(m.adc));
    std::memset(m.timestamps,0x43,sizeof(m.timestamps));
    for(unsigned node=0;node<max_slots;++node) {
        auto &n=s.at(node,max_slots);
        assert(n.single_samples==m.fast.samples[node] && n.samples==nullptr);
        n.index=node*100U;n.timestamp=node*200U;
        for(unsigned j=0;j<pairs;++j)n.single_samples[j].ch1=(node*17U+j)&255U;
    }
    // Match existing CH1 frame_slot: two frames at the timestamp arena tail.
    auto *end=reinterpret_cast<uint8_t *>(m.timestamps)+sizeof(m.timestamps);
    for(unsigned slot=0;slot<2;++slot) {
        auto *frame=new (end-(2U-slot)*sizeof(SampleFrame)) SampleFrame;
        assert(reinterpret_cast<uintptr_t>(frame)%alignof(SampleFrame)==0U);
        disjoint(frame,sizeof(*frame),m.timestamps,pairs*2U*sizeof(uint32_t));
        disjoint(frame,sizeof(*frame),m.adc,sizeof(m.adc));
        disjoint(frame,sizeof(*frame),&m.fast,sizeof(m.fast));
        std::memset(frame->bytes,0xd0+slot,sizeof(frame->bytes));
    }
    bytes_are(m.adc,sizeof(m.adc),0x21);
    bytes_are(m.timestamps,pairs*2U*sizeof(uint32_t),0x43);
    for(unsigned node=0;node<max_slots;++node) {
        auto &n=s.at(node,max_slots);
        assert(n.single_samples==m.fast.samples[node] && n.samples==nullptr);
        assert(n.index==node*100U && n.timestamp==node*200U);
        for(unsigned j=0;j<pairs;++j)assert(n.single_samples[j].ch1==((node*17U+j)&255U));
    }
    for(unsigned slot=0;slot<2;++slot)
        bytes_are(end-(2U-slot)*sizeof(SampleFrame),sizeof(SampleFrame),0xd0+slot);
    guards(g);
}
int main() {
    Guarded g;
    std::memset(g.before,0x5a,sizeof(g.before));
    std::memset(g.after,0xa5,sizeof(g.after));
    for(unsigned cycle=0;cycle<3;++cycle) {
        single(g);           // CH1 ADC8/88, eight nodes, Word path scratch.
        dual(g,8,3888);       // Native dual ADC8/253.
        dual(g,10,4176);      // Native dual ADC10/308.
        dual(g,14,2048);      // Normal ADC14/31250.
        single(g);           // Rebind the compact single member again.
    }
    std::printf("%zu\n",sizeof(Storage));
}
'''


def sources(folder):
    return {p.relative_to(folder).as_posix(): p.read_bytes()
            for p in sorted(folder.rglob('*')) if p.is_file()
            and '.cache' not in p.parts and '__pycache__' not in p.parts}


class BatchArenaTests(unittest.TestCase):
    def test_generator_is_deterministic_and_preserves_ancestors(self):
        parent = EXP / 'batchnative'
        before = sources(parent)
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'batcharena'
            prepare(out)
            first = sources(out)
            prepare(out)
            self.assertEqual(first, sources(out))
            self.assertEqual(first, sources(EXP / 'batcharena'))
            changed = {name for name in before if before[name] != first[name]}
            self.assertEqual(set(before), set(first))
            self.assertEqual(changed, {'oscilloscope/sketch/acquisition_storage.h',
                'oscilloscope/sketch/sketch.ino', 'oscilloscope/app.yaml', 'oscilloscope/python/main.py'})
        self.assertEqual(before, sources(parent))

    def test_only_frame_backing_store_changes_in_sketch(self):
        native = (EXP / 'batchnative/oscilloscope/sketch/sketch.ino').read_text()
        arena = (EXP / 'batcharena/oscilloscope/sketch/sketch.ino').read_text()
        expected = native.replace(
            '// Native dual DMA uses its timestamp arena: never place scratch there.\n'
            'static SampleFrame dual_pipeline_frames[FRAME_SLOTS-1U];',
            '// Native dual scratch lives after DMA and samples, inside the existing union arena.\n'
            'static_assert(FRAME_SLOTS-1U == 2U, "Dual arena scratch frame count");').replace(
            'return &dual_pipeline_frames[slot-1U];',
            'return &acquisition::storage.memory.dual.spi_scratch[slot-1U];')
        self.assertEqual(arena, expected)
        self.assertNotIn('dual_pipeline_frames', arena)
        self.assertNotIn('dual_scratch', arena)

    def test_sanitized_union_rebinding_canaries_and_batchfast_storage_size(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            sizes = []
            for variant, program in (('batchfast', SIZE), ('batcharena', GEOMETRY)):
                source = folder / (variant + '.cpp')
                binary = folder / variant
                source.write_text(program)
                subprocess.run(['c++', '-std=c++17', '-O1', '-g',
                    '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                    '-DCONFIG_DCACHE_LINE_SIZE=32', '-I', str(EXP / variant / 'oscilloscope/sketch'),
                    str(source), '-o', str(binary)], check=True)
                sizes.append(int(subprocess.check_output([str(binary)], text=True)))
            self.assertEqual(sizes[0], sizes[1])


if __name__ == '__main__':
    unittest.main()
