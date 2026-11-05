"""Private V20 trial: pace only ADC8/2 MS/s RADIO A0 priming at DAC time."""

from contextlib import contextmanager
from functools import wraps


@contextmanager
def realtime_radio_priming():
    """Temporarily use one 480-point DAC block per 12 ms during priming."""
    from monitor.v20.receiver.unoq_config_receiver import OutputReceiver

    original = OutputReceiver.service_wav

    @wraps(original)
    def service_wav(receiver):
        config = receiver.config
        source = receiver.wav_codes
        if (source is None or receiver.wav_started or receiver.wav_rate != 40000
                or not getattr(source, 'radio_audio', False)
                or (getattr(config, 'bits', None), getattr(config, 'rate', None),
                    getattr(config, 'channels', None), getattr(config, 'period', None),
                    getattr(config, 'node_pairs', None)) != (8, 2000000, 1, 80, 3488)):
            return original(receiver)

        previous = source.chunk_interval
        source.chunk_interval = 480 / receiver.wav_rate
        try:
            return original(receiver)
        finally:
            source.chunk_interval = previous

    OutputReceiver.service_wav = service_wav
    try:
        yield
    finally:
        OutputReceiver.service_wav = original
