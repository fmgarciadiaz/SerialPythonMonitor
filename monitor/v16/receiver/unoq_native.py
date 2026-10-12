"""Physically accepted native-clock profiles, shared with firmware generation."""
import json
from pathlib import Path

_path = Path(__file__).with_name('native_profiles.json')
PROFILES = tuple(json.loads(_path.read_text()) if _path.exists() else ())


def profile(bits, rate):
    return next((p for p in PROFILES if p['bits'] == bits and
                 160000000 // p['ticks'] == rate), None)


def wire_profile(bits, encoded):
    return next((p for p in PROFILES if p['bits'] == bits and code(p) == encoded), None)


def code(p):
    return (p['node_pairs'] << 16) | p['ticks'] | (0x80000000 if p['channels'] == 2 else 0)
