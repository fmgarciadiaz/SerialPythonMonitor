"""Embedded SVG paths: Qt never opens cloud-backed icon files during acquisition.

Regenerate assets_rc.py with pyside6-rcc after editing assets.qrc or its SVGs.
"""
from monitor.v19 import assets_rc  # Registers the immutable Qt resource bundle.


def asset(name):
    return ":/arduscopio/" + name
