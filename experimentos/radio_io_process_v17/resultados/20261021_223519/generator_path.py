"""Serialized generator readback through existing encoder/strict decoder."""
from monitor.v17.receiver.unoq_generator import generator_request
from monitor.v17.receiver.unoq_switch import Phase


class GeneratorPath:
    def __init__(self,pump):self.pump=pump;self.pending=None;self.observed=None

    def query(self,now):
        c=self.pump.control
        if self.pending is not None or self.pump.outgoing is not None or c.pending or c.state not in ('ready','stopped','done'):
            raise ValueError('Generator query requires idle serialized control')
        c._clock(now);rid=c.journal.reserve(c.epoch,c.session)
        self.pump.outgoing=generator_request(rid);self.pump.written=0
        self.pending=(rid,now,c.epoch,c.session)

    def tick(self,now):
        if self.pending is not None and now-self.pending[1]>=self.pump.control.timeout:
            raise TimeoutError('Generator query timeout')

    def event(self,kind,value):
        if kind!='generator':return
        if self.pending is None or value.request_id!=self.pending[0]:raise ValueError('Unrequested generator reply')
        if value.phase==Phase.REJECTED:raise RuntimeError('Generator query rejected')
        if value.phase==Phase.APPLIED:
            rid,_,epoch,session=self.pending
            self.pump.control.journal.acknowledge(rid,session,epoch)
            self.observed=value;self.pending=None
