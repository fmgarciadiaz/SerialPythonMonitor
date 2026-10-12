"""Publish only complete controlled physical acceptances into V16 contracts."""
import json
import shutil
from dataclasses import asdict
from pathlib import Path
from experimentos.maxfreq_v16.accepted import accepted_profiles, firmware_header

ROOT = Path(__file__).resolve().parents[2]
EXP = Path(__file__).resolve().parent


def main():
    report = json.loads((EXP/'sweep.json').read_text())
    profiles = accepted_profiles(report)
    header = firmware_header(profiles)
    for folder in ('arduino/v16/oscilloscope/sketch', 'arduino/v16/relay'):
        (ROOT/folder/'native_profiles.h').write_text(header)
    (ROOT/'monitor/v16/receiver/native_profiles.json').write_text(
        json.dumps([asdict(p) for p in profiles], indent=2)+'\n')
    shutil.copy2(EXP/'arduino/v16/oscilloscope/sketch/sample_packing.h',
                 ROOT/'arduino/v16/oscilloscope/sketch/sample_packing.h')
    print(json.dumps([asdict(p) | {'rate':p.rate} for p in profiles], indent=2))


if __name__ == '__main__':
    main()
