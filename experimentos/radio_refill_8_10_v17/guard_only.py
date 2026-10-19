"""Isolated low-risk refill candidate: original pacing, independent loop compute."""
from monitor.v17.radio_output import HighRateRadioDacSource

class GuardOnlySource(HighRateRadioDacSource):
    chunk_burst=8
