import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.wav_copy_candidate_v19 import candidate_text,variants
from tools.wav_timing_candidate_v19 import accepted_sources,SKETCH,SCHEMA
from tools import private_firmware_v19 as binding


def publish(text):
    return text[text.index('SCOPE_WAV_FAST static void publish('):text.index('static bool start(')]


class WavCopyTests(unittest.TestCase):
    def test_actual_publish_full_partial_unaligned_bytes_bounds_cache_and_descriptor(self):
        original=(SKETCH/'wav_dma.h').read_text();candidate=candidate_text(original)
        stub=r'''
static uint16_t storage[scope_wav::SLOTS*scope_wav::POINTS];static uint16_t *data=storage;
static unsigned selected_slot=0,selected_count=0,caches=0,descriptors=0,barriers=0;
static bool selected_final=false;
static void cache_flush_invalidate(uint16_t *p,unsigned bytes){
 assert(p==data+selected_slot*scope_wav::POINTS);assert(bytes==960);++caches;
}
static void descriptor(unsigned slot,bool guard,unsigned count,bool final){
 assert(slot==selected_slot);assert(!guard);assert(count==selected_count);assert(final==selected_final);++descriptors;
}
static void __DSB(){++barriers;}
'''
        source='#include <cassert>\n#include <cstring>\n#include "wav_protocol.h"\n'
        for name,text in [('baseline',original),('candidate',candidate)]:
            source+='namespace '+name+' {\n'+stub+publish(text)+'}\n'
        source+=r'''
int main(){
 uint8_t bytes[962];
 for(unsigned i=0;i<sizeof(bytes);++i)bytes[i]=uint8_t(i*37U+19U);
 for(unsigned count:{1U,2U,37U,478U,479U,480U})for(unsigned slot:{0U,7U,29U})for(unsigned alignment:{0U,1U}){
  for(unsigned i=0;i<scope_wav::SLOTS*scope_wav::POINTS;++i)baseline::storage[i]=candidate::storage[i]=0x5a5a;
  baseline::selected_slot=candidate::selected_slot=slot;
  baseline::selected_count=candidate::selected_count=count;
  baseline::selected_final=candidate::selected_final=bool(count&1);
  baseline::publish(slot,bytes+alignment,count,baseline::selected_final);
  candidate::publish(slot,bytes+alignment,count,candidate::selected_final);
  assert(!memcmp(baseline::storage,candidate::storage,sizeof(baseline::storage)));
  for(unsigned i=0;i<scope_wav::SLOTS*scope_wav::POINTS;++i)
   if(i<slot*480 || i>=slot*480+count)assert(candidate::storage[i]==0x5a5a);
 }
 assert(baseline::caches==candidate::caches);assert(candidate::caches==36);
 assert(baseline::descriptors==candidate::descriptors);assert(candidate::descriptors==36);
 assert(baseline::barriers==candidate::barriers);assert(candidate::barriers==36);
}
'''
        source='#include <initializer_list>\n'+source
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary);(folder/'test.cpp').write_text(source)
            subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(SKETCH),
                            str(folder/'test.cpp'),'-o',str(folder/'test')],check=True)
            subprocess.run([str(folder/'test')],check=True)

    def test_bindings_preserve_validation_and_reject_changes_in_each_candidate(self):
        originals=accepted_sources();generated=variants(originals)
        self.assertEqual(generated['candidate_wav_copy']['wav.h'],originals['wav.h'])
        digest=lambda b:hashlib.sha256(b).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();sketch=root/'arduino/v19/oscilloscope/sketch';sketch.mkdir(parents=True)
            folder=root/'diagnosticos/resultados_v19/copy';folder.mkdir(parents=True)
            builds={}
            for name,files in [('control_os',originals),*generated.items()]:
                target=folder/name;(target/'build').mkdir(parents=True);builds[name]={}
                for filename,text in files.items():(target/filename).write_text(text)
                for kind in ('bin','elf'):
                    data=(name+kind).encode();(target/'build'/('sketch.ino.'+kind)).write_bytes(data)
                    builds[name][kind+'_sha256']=digest(data)
            for name,text in originals.items():(sketch/name).write_text(text)
            accepted=dict(firmware_sha256=builds['control_os']['bin_sha256'],relay_sha256='c'*64)
            for name in generated:
                report=dict(ok=True,restoration=dict(ok=True),artifact=dict(compiled_with_pair_stopped=True,
                    firmware_installed=False,sources={p.name:digest(p.read_bytes()) for p in sketch.iterdir()},
                    variants={k:v for k,v in builds.items() if k in ('control_os',name)}))
                if 'timing' in name:report['artifact']['diagnostic_schema']=SCHEMA
                path=folder/(name+'_report.json');path.write_text(json.dumps(report))
                with patch.object(binding,'ROOT',root),patch.object(binding,'accepted_identity',return_value=accepted):
                    selected=binding.checked_firmware(path)
                    self.assertEqual(bool(selected.get('diagnostic_schema')),'timing' in name)
                    for filename in ('wav_dma.h','wav.h','sketch.ino'):
                        target=folder/name/filename;before=target.read_bytes();target.write_bytes(before+b' ')
                        with self.assertRaises(ValueError):binding.checked_firmware(path)
                        target.write_bytes(before)
                    parent=dict(report,artifact=dict(report['artifact'],variants=builds))
                    parent_path=folder/'report.json';parent_path.write_text(json.dumps(parent))
                    parent_bytes=parent_path.read_bytes()
                    report.update(parent_build_report=str(parent_path),parent_build_sha256=digest(parent_bytes))
                    path.write_text(json.dumps(report));binding.checked_firmware(path)
                    parent_path.write_bytes(parent_bytes+b' ')
                    with self.assertRaisesRegex(ValueError,'parent report changed'):binding.checked_firmware(path)
                    parent_path.write_bytes(parent_bytes)
