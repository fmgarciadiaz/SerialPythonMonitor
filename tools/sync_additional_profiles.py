#!/usr/bin/env python3
"""Synchronize additional ADC profile tables; does not install firmware."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    profiles=json.loads((ROOT/'monitor/v16/receiver/additional_profiles.json').read_text())
    rows=''.join('    {%d, %d, %d, %d},\n'%(p['bits'],p['channels'],p['ticks'],p['node_pairs']) for p in profiles)
    header='// Additional native-clock profiles; see additional_profiles.json for validation status.\n#pragma once\nstatic const ScopeNativeProfile scope_additional_profiles[] = {\n'+rows+'};\n'
    for folder in ('arduino/v16/oscilloscope/sketch','arduino/v16/relay'):
        path=ROOT/folder/'additional_profiles.h'
        if not path.exists() or path.read_text() != header:path.write_text(header)
if __name__=='__main__':main()
