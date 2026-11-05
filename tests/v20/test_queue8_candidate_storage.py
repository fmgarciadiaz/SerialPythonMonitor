"""Source contract and deferred native harness for the isolated V20 queue-8 trial."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / 'experiments/v20/queue8_candidates'
BASE = {
    'sketch/acquisition_storage.h': 'arduino/v20/oscilloscope/sketch/acquisition_storage.h',
    'sketch/acquisition.h': 'arduino/v20/oscilloscope/sketch/acquisition.h',
    'sketch/high_rate_profile.h': 'arduino/v20/oscilloscope/sketch/high_rate_profile.h',
    'sketch/native_profiles.h': 'arduino/v20/oscilloscope/sketch/native_profiles.h',
    'relay/high_rate_profile.h': 'arduino/v20/relay/high_rate_profile.h',
    'relay/native_profiles.h': 'arduino/v20/relay/native_profiles.h',
}
QUEUE8 = {(10, 1, 116, 5568), (12, 1, 140, 7488), (14, 1, 158, 5952)}


def profiles(text):
    return [tuple(map(int, match)) for match in
            re.findall(r'\{(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\}', text)]


class Queue8CandidateStorageTests(unittest.TestCase):
    def test_manifest_pins_unchanged_base_and_private_scope(self):
        manifest = json.loads((CANDIDATE / 'manifest.json').read_text())
        self.assertEqual(set(manifest['base_sha256']), set(BASE))
        for overlay, original in BASE.items():
            with self.subTest(overlay=overlay):
                self.assertEqual(hashlib.sha256((ROOT / original).read_bytes()).hexdigest(),
                                 manifest['base_sha256'][overlay])
                self.assertTrue((CANDIDATE / overlay).is_file())
        self.assertTrue(manifest['private'])
        self.assertFalse(manifest['promoted'])
        self.assertEqual({tuple(p) for p in manifest['queue8_profiles']}, QUEUE8)

    def test_catalogs_are_paired_and_only_add_adc14_158(self):
        for side in ('sketch', 'relay'):
            with self.subTest(side=side):
                overlay = (CANDIDATE / side / 'native_profiles.h').read_text()
                original = (ROOT / BASE[f'{side}/native_profiles.h']).read_text()
                self.assertEqual(profiles(overlay),
                                 profiles(original)[:profiles(original).index((14, 1, 170, 5952)) + 1]
                                 + [(14, 1, 158, 5952)]
                                 + profiles(original)[profiles(original).index((14, 1, 170, 5952)) + 1:])
        self.assertEqual((CANDIDATE / 'sketch/native_profiles.h').read_bytes(),
                         (CANDIDATE / 'relay/native_profiles.h').read_bytes())

    def test_only_three_new_queue8_tuples_and_one_high_rate_tuple(self):
        for side in ('sketch', 'relay'):
            with self.subTest(side=side):
                original = (ROOT / BASE[f'{side}/high_rate_profile.h']).read_text()
                overlay = (CANDIDATE / side / 'high_rate_profile.h').read_text()
                high = original.replace(
                    '(bits==14 && ticks==192 && pairs==1984));',
                    '(bits==14 && ticks==192 && pairs==1984) ||\n'
                    '        (bits==14 && ticks==158 && pairs==5952));')
                self.assertIn('(bits==14 && ticks==158 && pairs==5952)', overlay)
                self.assertEqual(overlay.split('static inline unsigned scope_queue_capacity')[0],
                                 high.split('static inline unsigned scope_queue_capacity')[0])
                self.assertIn('if(scope_spi40(bits,channels,ticks,pairs)) return 16U;', overlay)
                capacity = overlay.split('static inline unsigned scope_queue_capacity')[1]
                self.assertEqual(set(tuple(map(int, item)) for item in
                    re.findall(r'bits==(\d+) && ticks==(\d+) && pairs==(\d+)', capacity)),
                    {(10, 116, 5568), (12, 140, 7488), (14, 158, 5952)})
                self.assertIn('return 4U;', capacity)
        self.assertEqual((CANDIDATE / 'sketch/high_rate_profile.h').read_bytes(),
                         (CANDIDATE / 'relay/high_rate_profile.h').read_bytes())

    def test_storage_contract_prevalidates_and_uses_real_stride(self):
        storage = (CANDIDATE / 'sketch/acquisition_storage.h').read_text()
        acquisition = (CANDIDATE / 'sketch/acquisition.h').read_text()
        self.assertIn('SingleSample[compact_slots * 7488U]', storage)
        self.assertIn('Node queue[compact_slots]', storage)
        self.assertIn('active_slots!=slots && active_slots!=compact_slots && active_slots!=max_slots', storage)
        self.assertIn('(active_slots==compact_slots && pairs>7488U)', storage)
        self.assertIn('} else if(active_slots!=slots) return false;', storage)
        self.assertLess(storage.index('if(active_slots!=slots'), storage.index('new (&memory.single)'))
        self.assertIn('new (&m->samples) SingleMemory::Samples', storage)
        self.assertIn('queue[i].single_samples=samples+i*pairs', storage)
        self.assertIn('for(unsigned i=0;i<active_slots;++i)', storage)
        self.assertIn('if(active_slots==max_slots)', storage)
        self.assertIn('return memory.single.fast.nodes[index]', storage)
        self.assertIn('sizeof(scope_storage::Storage) <= 0x60000U', storage)
        self.assertLess(acquisition.index('if(!storage.bind('),
                        acquisition.index('QUEUE_SLOTS=requested_slots;'))
        self.assertIn('requested_slots==scope_storage::slots?\n        SCOPE_NATIVE_MAX_SINGLE:node_pairs()', acquisition)
        self.assertEqual(8 * 7488, 59904)
        self.assertEqual(59904 * 2, 119808)
        self.assertEqual((8 - 1) * 7488 + 7488, 59904)
        self.assertEqual((4 - 1) * 8192 + 8192, 32768)
        self.assertEqual(16 * 3488, 55808)

    @unittest.skipUnless(os.environ.get('QUEUE8_RUN_CPP') == '1',
                         'Native pointer and transition harness deferred until board owner permits compilers')
    def test_native_bind_transitions_rejections_and_last_pointers(self):
        compiler = shutil.which('c++')
        self.assertIsNotNone(compiler)
        harness = r'''
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <initializer_list>
#include "acquisition_storage.h"
int main() {
    scope_storage::Storage storage{};
    using namespace scope_storage;
    assert(storage.bind(true,4,8192));
    auto *four=storage.at(0,4).single_samples;
    assert(storage.at(3,4).single_samples+8192 == four+32768);
    auto *adc=storage.adc;
    assert(!storage.bind(true,8,7489));
    assert(storage.adc==adc && storage.at(3,4).single_samples+8192==four+32768);
    assert(!storage.bind(false,8,7488));
    assert(storage.adc==adc && storage.at(0,4).single_samples==four);
    assert(!storage.bind(true,5,5568));
    assert(storage.adc==adc && storage.at(0,4).single_samples==four);
    for(unsigned pairs: {5568U,7488U,5952U}) {
        assert(storage.bind(true,8,pairs));
        auto *first=storage.at(0,8).single_samples;
        assert(storage.at(7,8).single_samples+ pairs == first+8*pairs);
        assert(reinterpret_cast<uintptr_t>(first)%alignof(SingleSample)==0);
    }
    assert(storage.bind(true,16,3488));
    auto *fast=storage.at(0,16).single_samples;
    assert(storage.at(15,16).single_samples+3488 == fast+16*3488);
    assert(!storage.bind(true,16,3489));
    assert(storage.at(0,16).single_samples==fast);
    assert(storage.bind(false,4,8192));
    auto *dual=storage.at(0,4).samples;
    assert(storage.at(3,4).samples+4176 == dual+4*4176);
    assert(storage.bind(true,8,7488));
    assert(storage.bind(true,4,8192));
    assert(storage.at(3,4).single_samples+8192==storage.at(0,4).single_samples+32768);
}
'''
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            (folder / 'acquisition_storage.h').write_bytes(
                (CANDIDATE / 'sketch/acquisition_storage.h').read_bytes())
            (folder / 'scope_protocol.h').write_text(
                '#pragma once\n#include <cstdint>\nstruct ChannelPair { uint16_t ch1,ch2; };\n'
                'struct Packet { uint8_t bytes[992]; };\n'
                'namespace scope_bench { constexpr unsigned BLOCK_BYTES=992; }\n')
            (folder / 'native_profiles.h').write_text(
                '#pragma once\n#define SCOPE_NATIVE_MAX_SINGLE 8192U\n'
                '#define SCOPE_NATIVE_MAX_DUAL 4176U\n')
            (folder / 'frame_buffer.h').write_text(
                '#pragma once\nstruct alignas(32) SampleFrame { uint8_t bytes[992]; };\n')
            (folder / 'test.cpp').write_text(harness)
            subprocess.run([compiler, '-std=c++17', '-O0', '-Wall', '-Wextra',
                            '-Werror', str(folder / 'test.cpp'), '-o', str(folder / 'test')],
                           check=True, cwd=folder)
            subprocess.run([str(folder / 'test')], check=True, cwd=folder)


if __name__ == '__main__':
    unittest.main()
