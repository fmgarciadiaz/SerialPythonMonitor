"""System-locale formatting for visible numbers; storage formats stay unchanged."""
import importlib
import sys


def number(value, spec='g'):
    binding = 'PySide6'
    locale = importlib.import_module(binding + '.QtCore').QLocale()
    if spec == ',' or spec.endswith('d'):
        return locale.toString(int(value))
    match = __import__('re').search(r'\.(\d+)', spec)
    precision = int(match.group(1)) if match else 6
    kind = spec[-1] if spec[-1:] in ('f', 'g', 'e') else 'g'
    return locale.toString(float(value), kind, precision)

class Formats:
    pass

formats = Formats()
formats.n_ = ','
formats.ng = 'g'
formats.n_2f = '.2f'
formats.n_1f = '.1f'
formats.n04_1f = '04.1f'
formats.n__0f = ',.0f'
formats.n_4g = '.4g'
