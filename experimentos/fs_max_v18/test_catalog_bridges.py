import json,subprocess,tempfile,unittest
from pathlib import Path
from experimentos.fs_max_v18.prepare_catalog_bridges import ROOT,OUT,PROFILES
from experimentos.fs_max_v18.probe_journal import source_manifest

class CatalogBridgeTests(unittest.TestCase):
 def test_only_whitelists_change(self):
  for name,allowed in (('oscilloscope',{'sketch/native_profiles.h','sketch/high_rate_profile.h'}),('relay',{'native_profiles.h','high_rate_profile.h','cpu_profile.h'})):
   recorded=json.loads((OUT/'source_manifest.json').read_text())
   before={key[len(name)+1:]:value for key,value in recorded.items() if key.startswith(name+'/')}
   after=source_manifest(OUT/name)
   self.assertEqual(set(before),set(after))
   self.assertEqual({key for key in before if before[key]!=after[key]},allowed)
 def test_existing_c_policies_unchanged_and_new_targets_inherit_geometry(self):
  profiles=json.loads((OUT/'public_profiles.before.json').read_text())
  recorded=json.loads((OUT/'source_manifest.json').read_text())
  for name in ('high_rate_profile.h','cpu_profile.h'):
   self.assertEqual(source_manifest(OUT/'baseline_relay')[name],recorded['relay/'+name])
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory);source=path/'policy.c';binary=path/'policy'
   macros=['scope_high_rate','scope_spi40','scope_queue_capacity','scope_cpu_profile']
   program='#include <stdint.h>\n'
   program+=''.join(f'#define {name} old_{name}\n' for name in macros)
   program+=f'#include {json.dumps(str(OUT/"baseline_relay/cpu_profile.h"))}\n'
   program+=''.join(f'#undef {name}\n' for name in macros)
   program+=f'#include {json.dumps(str(OUT/"relay/cpu_profile.h"))}\nint main(void) {{\n'
   for p in profiles:
    args=f'{p["bits"]},{p.get("channels",1)},{p["ticks"]},{p["node_pairs"]}'
    for name in macros:program+=f' if ({name}({args}) != old_{name}({args})) return 1;\n'
   for p in PROFILES:
    args=f'{p["bits"]},1,{p["ticks"]},{p["node_pairs"]}'
    program+=f' if (scope_high_rate({args}) != {int(p['bits']!=16)} || scope_cpu_profile({args}) != {int(p['bits']!=16)} || scope_queue_capacity({args}) != {p["queue_slots"]}) return 2;\n'
   source.write_text(program+' return 0;\n}\n')
   subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],check=True,capture_output=True)
   subprocess.run([str(binary)],check=True)
 def test_native_profile_entries_are_unique(self):
  import re
  for path in (OUT/'oscilloscope/sketch/native_profiles.h',OUT/'relay/native_profiles.h'):
   rows=re.findall(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}',path.read_text())
   self.assertEqual(len(rows),len(set(rows)))
