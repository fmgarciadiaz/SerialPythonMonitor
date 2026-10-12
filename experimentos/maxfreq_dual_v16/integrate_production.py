"""Merge physically accepted dual profiles into the existing CH1 production path."""
import json
import shutil
from dataclasses import asdict
from pathlib import Path
from experimentos.maxfreq_v16.accepted import AcceptedProfile, accepted_profiles, firmware_header

ROOT = Path(__file__).resolve().parents[2]
EXP = Path(__file__).resolve().parent


def main():
    dual = accepted_profiles(json.loads((EXP/'sweep.json').read_text()))
    ch1 = accepted_profiles(json.loads((ROOT/'experimentos/maxfreq_v16/sweep.json').read_text()))
    path = ROOT/'monitor/v16/receiver/native_profiles.json'
    existing = [AcceptedProfile(**p) for p in json.loads(path.read_text())]
    if set(existing) != set(ch1):
        raise RuntimeError('Production whitelist differs from the accepted CH1 baseline')
    profiles = sorted(ch1+dual, key=lambda p: (p.channels, p.bits, p.rate))
    backup = EXP/'production_before_dual'
    if backup.exists():
        raise RuntimeError('Integration backup already exists; inspect before repeating')
    for folder in ('oscilloscope/sketch', 'relay'):
        shutil.copytree(ROOT/'arduino/v16'/folder, backup/folder)
    shutil.copy2(path, backup/'native_profiles.json')
    header = firmware_header(profiles)
    for folder in ('oscilloscope/sketch', 'relay'):
        (ROOT/'arduino/v16'/folder/'native_profiles.h').write_text(header)

    packing = ROOT/'arduino/v16/oscilloscope/sketch/sample_packing.h'
    dual_packing = (EXP/'arduino/v16/oscilloscope/sketch/sample_packing.h').read_text()
    packing.write_text(packing.read_text()+'\n'+dual_packing[dual_packing.index('namespace maxfreq_packing'):].replace('unsigned pack(', 'unsigned pack_dual(', 1))

    sketch = ROOT/'arduino/v16/oscilloscope/sketch/sketch.ino'
    text = sketch.read_text()
    changes = {
        'const unsigned used=(count*acquisition::bits+7U)/8U;':
        'const unsigned channels=acquisition::single()?1U:2U;\n    const unsigned used=count*acquisition::bits*channels/8U;',
        'frame[67]=1;': 'frame[67]=channels;',
        'if (count) maxfreq_packing::pack(frame+116,node->single_samples+offset,count,acquisition::bits);':
        'if(count) {\n        if(acquisition::single()) maxfreq_packing::pack(frame+116,node->single_samples+offset,count,acquisition::bits);\n        else maxfreq_packing::pack_dual(frame+116,node->samples+offset,count,acquisition::bits);\n    }',
        'acquisition::native()?(acquisition::bits==8?864U:acquisition::bits==10?696U:496U)':
        'acquisition::native()?(acquisition::single()?(acquisition::bits==8?864U:acquisition::bits==10?696U:496U):acquisition::bits==8?432U:((872U*8U/(acquisition::bits*2U))&~3U))',
    }
    for old, new in changes.items():
        if text.count(old) != 1:
            raise RuntimeError('Unexpected production builder: '+old)
        text = text.replace(old, new, 1)
    sketch.write_text(text)
    path.write_text(json.dumps([asdict(p) for p in profiles], indent=2)+'\n')
    print(f'Merged {len(ch1)} CH1 and {len(dual)} dual accepted profiles; backup {backup}')


if __name__ == '__main__':
    main()
