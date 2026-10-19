"""Serve confirmed audio credits between ADC frames, not just ACK/read turns."""
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver

original_events=OutputReceiver._process_decoder_events


def service_each_frame(self):
    original_events(self)
    # Keep QUERY/PLAY/STOP serialization and all free-slot reservations.
    # Existing token bucket still controls pacing and maximum burst.
    if getattr(self.wav_codes,'radio_audio',False):self.service_wav()
