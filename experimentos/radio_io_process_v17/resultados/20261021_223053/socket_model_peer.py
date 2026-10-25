"""Observed state for an emulated peer over a real socket, ONLY for local tests.

The baseline is the fixture's known ADC profile, not a snapshot of a real Q.
All audio state comes from strict decoded replies, not direct model access.
"""
from experimentos.radio_io_process_v17.socket_transport import SocketTransport
from monitor.v17.receiver.unoq_acquisition import Configuration


class SocketModelPeer(SocketTransport):
    def __init__(self,connected):
        super().__init__(connected)
        self.pump=None;self.path=None;self.original_config=Configuration(14,125000)

    def bind(self,pump,path):self.pump=pump;self.path=path
    def advance(self,now):pass # Consumption occurs independently in the server.

    @property
    def state(self):return self.pump.control.status.state if self.pump.control.status is not None else None
    @property
    def accepted(self):return self.pump.control.status.accepted if self.pump.control.status is not None else 0
    @property
    def played(self):return self.pump.control.status.played if self.pump.control.status is not None else 0
    @property
    def config(self):return self.path.config if self.path is not None else self.original_config
    @property
    def frame_count(self):return self.received_bytes//992
