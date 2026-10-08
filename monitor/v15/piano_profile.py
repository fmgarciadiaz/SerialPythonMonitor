"""Broadwood reference parameters in SI; interpolated values are model choices.

Source: https://euphonics.org/12-2-1-parameter-values-for-piano-simulations/
Mass of strings in the table is TOTAL mass for the note, not per string.
"""
from functools import lru_cache
import numpy as np

NOTES = np.arange(24, 109, 12, dtype=float)
LENGTH = np.array([1013,925,830,639,324,181,96,51]) * .001
DIAMETER = np.array([1.21,1.21,1.08,1.,.94,.85,.82,.76]) * .001
MASS = np.array([189,73,30.7,11.7,5.3,2.4,1.15,.54]) * .001
STRINGS = np.array([1,1,2,3,3,3,3,3])
POSITION = np.array([.135,.135,.130,.125,.12,.10,.09,.08])
HAMMER_MASS = np.array([12,11,10,9,8,7,6,5]) * .001
FREQUENCY = np.array([32.7,65.4,131,262,523,1047,2093,4186])
MU = MASS / (STRINGS * LENGTH)
TENSION = (2 * LENGTH * FREQUENCY)**2 * MU
B = np.pi**2 * (210e9 * np.pi * DIAMETER**4 / 64) / (TENSION * LENGTH**2)
CONTACT_Z = 2 * STRINGS * np.sqrt(TENSION * MU)

@lru_cache(maxsize=256)
def piano_profile(frequency):
    """Clamp outside C1..C8; log interpolation for positive derived quantities.

    Felt K/p have only C2/C4/C7 anchors and clamp outside those anchors.
    Interpolating derived B/Z avoids abrupt jumps at unison-count boundaries.
    """
    note = 69 + 12 * np.log2(max(float(frequency), 1.) / 440)
    def linear(values): return float(np.interp(note, NOTES, values))
    def logarithmic(values): return float(np.exp(np.interp(note, NOTES, np.log(values))))
    return dict(mass=linear(HAMMER_MASS), position=linear(POSITION),
                stiffness=logarithmic(B), impedance=logarithmic(CONTACT_Z),
                strings=1 if note < 48 else 2 if note < 60 else 3,
                exponent=float(np.interp(note, [36,60,96], [2.3,2.5,3.])),
                contact_k=float(np.exp(np.interp(note, [36,60,96], np.log([4e8,4.5e9,1e12])))))
