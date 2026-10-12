"""Continuous first-order DC blocker, independent state for each WAV channel."""
import math
import numpy as np
from scipy.signal import lfilter


class DCBlocker:
    def __init__(self, rate, cutoff=5.0):
        self.alpha = math.exp(-2 * math.pi * cutoff / rate)
        self.state = None

    def process(self, samples):
        samples = np.asarray(samples, dtype=np.float64)
        if not len(samples):
            return samples.copy()
        if self.state is None:
            # Initialize from the first sample to avoid a large DC startup step.
            self.state = -self.alpha * samples[:1].copy()
        result, self.state = lfilter([self.alpha, -self.alpha],
                                    [1, -self.alpha], samples,
                                    axis=0, zi=self.state)
        return result
