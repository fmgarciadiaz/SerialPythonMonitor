"""Offline bridge to the existing strict V18 protocol. No transport or Qt.

This is not yet an owner backend. The caller must service each ordered event
synchronously, preserving refill/configuration/sample ordering.
"""
import numpy as np
from monitor.v18.receiver.unoq_config_decoder import ConfigurationDecoder
from monitor.v18.receiver.unoq_usb import ProtocolError
from monitor.v18.receiver import unoq_wav as wav
from monitor.v18.io.prototype import RequestJournal


class ProtocolIngress:
    """At most one partial frame retained; exceptions permanently close ingress."""
    def __init__(self,on_event):
        self.decoder=ConfigurationDecoder();self.on_event=on_event;self.closed=False
        self.decoder.numeric=True

    def feed(self,data):
        if self.closed:raise RuntimeError('Ingress closed')
        if not isinstance(data,bytes) or len(data)>32*992:
            raise ValueError('Ingress requires bounded immutable bytes')
        try:
            # Do not let a concatenated read defer a WAV ACK behind conversion
            # of subsequent RF frames. Use the production decoder frame by frame.
            cursor=0
            while cursor<len(data):
                take=min(992-len(self.decoder.buffer),len(data)-cursor)
                self.decoder.feed(data[cursor:cursor+take]);cursor+=take
                for kind,value in self.decoder.events:self.on_event(kind,value)
                self.decoder.events=[]
        except BaseException:
            self.closed=True;raise

    def eof(self):
        if self.closed:raise RuntimeError('Ingress closed')
        self.closed=True
        if self.decoder.buffer:raise ProtocolError('Truncated SCP1 frame at EOF')
        # Clean framing EOF still means transport ended, not successful audio.
        return 'transport_eof'


class ChunkRequests:
    """Encoding/correlation only: no BEGIN/PLAY/QUERY scheduler or credit policy."""
    def __init__(self,limit=256):
        # The real WAV namespace excludes 0xffffffff and all low RID values.
        self.journal=RequestJournal(limit,first=0x80000000,last=0xfffffffe)

    def encode(self,audio):
        audio.validate()
        rid=self.journal.reserve(audio.epoch,audio.session)
        packet=wav.chunk(rid,audio.session,audio.offset,np.frombuffer(audio.pcm,dtype='<u2'))
        return rid,packet

    def cancel(self):self.journal.cancel()

    def acknowledge(self,status,epoch):
        return self.journal.acknowledge(status.request_id,status.session,epoch)
