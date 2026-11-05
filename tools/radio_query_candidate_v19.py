"""Replay private/historical ACK/QUERY arms without double-renewing inline."""
from contextlib import contextmanager
import time


@contextmanager
def refresh_query_after_chunk_ack(enabled=True,burst_limit=None):
    from monitor.v19.receiver.unoq_config_receiver import OutputReceiver
    from monitor.v19.receiver.unoq_wav import State
    original=OutputReceiver._process_decoder_events
    inline=OutputReceiver._radio_chunk_ack_refresh
    if burst_limit not in (None,2):raise ValueError('Private burst limit must be 2')
    sources={};missing=object()
    def process(receiver):
        source=receiver.wav_codes
        if (burst_limit is not None and source is not None and
                getattr(source,'radio_audio',False) and receiver.wav_rate==40000):
            if id(source) not in sources:
                if len(sources)>=32:raise RuntimeError('Too many private RADIO sources')
                sources[id(source)]=(source,vars(source).get('chunk_burst',missing))
            source.chunk_burst=burst_limit
        callback=receiver.on_wav
        sent=dict(receiver.wav_inflight)
        def acknowledged(status):
            source=receiver.wav_codes
            entry=sent.get(status.request_id)
            # The original decoder handler reaches this callback only after
            # correlation/session/rate checks. It has already removed this ACK.
            if (enabled and entry is not None and entry[1]==13 and source is not None
                    and getattr(source,'radio_audio',False)
                    and receiver.wav_started and receiver.wav_rate==40000
                    and not status.reason and status.state==State.PLAYING):
                interval=max(.004,min(.1,float(getattr(source,'poll_interval',.04))))
                receiver.wav_poll_at=time.monotonic()+interval
            return callback(status)
        receiver.on_wav=acknowledged
        try:return original(receiver)
        finally:receiver.on_wav=callback
    # Keep the recorded private/sham arms single-renewal after the inline fix.
    OutputReceiver._radio_chunk_ack_refresh=False
    OutputReceiver._process_decoder_events=process
    try:yield
    finally:
        OutputReceiver._process_decoder_events=original
        OutputReceiver._radio_chunk_ack_refresh=inline
        for source,value in sources.values():
            if value is missing:delattr(source,'chunk_burst')
            else:source.chunk_burst=value


@contextmanager
def candidate_metrics_connection(serial):
    from tools.relay_wire_metrics_v19 import accepted_metrics_connection
    with refresh_query_after_chunk_ack():
        with accepted_metrics_connection(serial) as connection:yield connection


@contextmanager
def sham_metrics_connection(serial):
    from tools.relay_wire_metrics_v19 import accepted_metrics_connection
    with refresh_query_after_chunk_ack(enabled=False):
        with accepted_metrics_connection(serial) as connection:yield connection


@contextmanager
def burst2_metrics_connection(serial):
    from tools.relay_wire_metrics_v19 import accepted_metrics_connection
    with refresh_query_after_chunk_ack(burst_limit=2):
        with accepted_metrics_connection(serial) as connection:yield connection
