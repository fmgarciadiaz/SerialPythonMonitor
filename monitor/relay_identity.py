"""Shared native relay cache identity for installation and monitor startup."""
import hashlib
from pathlib import Path


def relay_sources(folder):
    folder=Path(folder)
    paths=[folder/name for name in ('unoq_config_stream.c','base_verifier.c','config_relay_protocol.h')]
    return paths+[p for p in sorted(folder.glob('*.h')) if p not in paths]


def relay_digest(folder):
    return hashlib.sha256(b''.join(p.read_bytes() for p in relay_sources(folder))).hexdigest()[:20]
