"""Serialized generator readback/OFF restore through existing strict protocol."""
from monitor.v17.receiver.unoq_generator import generator_request
from monitor.v17.receiver.unoq_switch import Phase


class GeneratorPath:
    def __init__(self,pump):self.pump=pump;self.pending=None;self.observed=None;self.baseline=None

    def query(self,now):return self._request(now,None)

    def set_off(self,config,now):
        if self.baseline is None or config.enabled:raise ValueError('Known OFF baseline required')
        return self._request(now,config)

    def _request(self,now,wanted):
        c=self.pump.control
        if self.pending is not None or self.pump.outgoing is not None or c.pending or c.state not in ('ready','stopped','done'):
            raise ValueError('Generator query requires idle serialized control')
        c._clock(now);rid=c.journal.reserve(c.epoch,c.session)
        self.pump.outgoing=generator_request(rid,wanted);self.pump.written=0
        self.pending=(rid,now,c.epoch,c.session,wanted)

    def tick(self,now):
        if self.pending is not None and now-self.pending[1]>=self.pump.control.timeout:
            raise TimeoutError('Generator query timeout')

    def event(self,kind,value):
        if kind!='generator':return
        if self.pending is None or value.request_id!=self.pending[0]:raise ValueError('Unrequested generator reply')
        if value.phase==Phase.REJECTED:raise RuntimeError('Generator query rejected')
        if value.phase==Phase.APPLIED:
            rid,_,epoch,session,wanted=self.pending
            if wanted is not None and value.active!=wanted:raise ValueError('Generator APPLIED differs from requested configuration')
            if wanted is None and self.baseline is None and not value.active.enabled and not value.running:
                self.baseline=value.active
            self.pump.control.journal.acknowledge(rid,session,epoch)
            self.observed=value;self.pending=None
