"""Private timing schema coherence, identity-independent parser, and MCU semantics."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from tools.wav_timing_candidate_v19 import candidate_sources,accepted_sources,HEADER,FIELDS,MAGIC,SKETCH
from tools.wav_timing_metrics_v19 import WavTimingMetrics
from tests.v19.test_wav_validation_candidate import STUB


def words(serial=1,request=7):
    values=[serial,request,77,480|(2<<16)|(1<<24),160000000]
    return values+[1600,160,320,480,160,160,960,1760,1600,request]


def emit(decoder,values,snapshot=1,phase='playing',epoch=1,skip=()):
    for page,value in enumerate(values):
        if page not in skip:decoder.native(epoch,page*2,phase,MAGIC|(page<<16)|snapshot,value)


class WavTimingTests(unittest.TestCase):
    def test_complete_snapshot_units_and_serial_coverage(self):
        d=WavTimingMetrics();emit(d,words());emit(d,words(),2);emit(d,words(4,10),3)
        r=d.report();self.assertEqual(len(r['records']),2)
        self.assertEqual(r['skipped_serials'],2);self.assertEqual(r['repeated'],1)
        self.assertEqual(r['groups'][0]['timing_us']['irq']['selected_mean'],10)
        self.assertEqual(r['records'][0]['request'],7)

    def test_missing_page_epoch_or_snapshot_never_mixes_data(self):
        for mutation in ('missing','epoch','snapshot'):
            d=WavTimingMetrics()
            for page,value in enumerate(words()):
                if mutation=='missing' and page==5:continue
                d.native(2 if mutation=='epoch' and page==5 else 1,page,'playing',
                         MAGIC|(page<<16)|(2 if mutation=='snapshot' and page==5 else 1),value)
            self.assertEqual(d.report()['records'],[])
            emit(d,words(2),3);self.assertEqual(len(d.report()['records']),1)

    def test_phase_crossing_and_uninitialized_snapshots_are_explicit(self):
        d=WavTimingMetrics();emit(d,[0]*len(FIELDS))
        for page,value in enumerate(words()):
            d.native(1,page,'preparing' if page<7 else 'playing',MAGIC|(page<<16)|2,value)
        self.assertEqual(d.report()['invalid'],1)
        self.assertEqual(d.report()['records'][0]['phase'],'mixed')
        with self.assertRaises(ValueError):d.native(1,0,'playing',0,0)
        with self.assertRaises(ValueError):d.native(1,0,'playing',MAGIC|(255<<16),0)

    def test_detail_cap_preserves_final_sample_and_cumulative_irq_max(self):
        d=WavTimingMetrics()
        for serial in range(1,4098):
            values=words(serial,serial+10);values[-2]=serial*10
            emit(d,values,serial)
        r=d.report();self.assertEqual(len(r['records']),4096)
        self.assertEqual(r['omitted'],1)
        self.assertEqual(r['last_seen_serial'],4097)
        self.assertEqual(r['first_seen_serial'],1)
        self.assertEqual(r['last_completed_sample']['serial'],4097)
        self.assertEqual(r['max_irq_since_boot']['cycles'],40970)

    def test_frozen_snapshot_survives_new_chunk_and_same_state_machine_trace(self):
        generated=candidate_sources(accepted_sources())
        source=('#include "benchmark_protocol.h"\n'+STUB).replace('#include "wav_queue.h"','#include "wav_queue.h"\n'
                           'static uint32_t clock_value=0;\n'
                           'static uint32_t k_cycle_get_32(){return ++clock_value;}\n'
                           'static uint32_t sys_clock_hw_cycles_per_sec(){return 160000000;}\n'+HEADER)
        # The host harness substitutes only hardware, not the V19 WAV state machine.
        source=source.replace('++publications;',
                              'scope_wav_timing::copy_cycles=1;scope_wav_timing::cache_cycles=2;'
                              'scope_wav_timing::descriptor_cycles=3;++publications;')
        checks=r'''
 assert(scope_wav_timing::latest.serial==45);
 assert(scope_wav_timing::latest.max_irq>0);
 assert(scope_wav_timing::latest.clock_hz==160000000);
 uint8_t packet[992]{};
 scope_wav_timing::page=0;
 scope_wav_timing::emit(packet);
 const uint32_t first=scope_bench::get32(packet+40);
 assert(scope_bench::get32(packet+44)==45);
 scope_wav_timing::latest.request=12345;
 scope_wav_timing::emit(packet);
 assert((scope_bench::get32(packet+40)&65535)==(first&65535));
 assert(scope_bench::get32(packet+44)!=12345);
'''
        source=source.rstrip()[:-1]+checks+'}\n'
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary);shutil.copytree(SKETCH,folder/'sketch')
            (folder/'sketch/wav.h').write_text(generated['wav.h'])
            (folder/'sketch/test.cpp').write_text(source)
            executable=folder/'test'
            subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(folder/'sketch'),
                            str(folder/'sketch/test.cpp'),'-o',str(executable)],check=True)
            subprocess.run([str(executable)],check=True,stdout=subprocess.PIPE)

    def test_source_transform_fails_closed_and_emits_after_last_copy_before_crc(self):
        originals=accepted_sources();generated=candidate_sources(originals)
        self.assertEqual(set(generated),set(originals))
        ino=generated['sketch.ino'];hook=ino.index('scope_wav_timing::emit(packet);')
        self.assertGreater(hook,ino.index('data_frame(packet,seq'))
        self.assertGreater(hook,ino.index('memcpy(packet+48,ordinary_frame.bytes+48'))
        self.assertLess(hook,ino.index('seal(packet);',hook))
        originals['wav.h']+='\n'+originals['wav.h']
        with self.assertRaises(ValueError):candidate_sources(originals)
