"""RF publication/barriers using strict decoder events; no physical transport."""
import queue
from monitor.v18.receiver.unoq_acquisition import acquisition_request
from monitor.v18.receiver.unoq_switch import Phase
from monitor.v18.io.prototype import Rf


class AcquisitionPath:
    def __init__(self,pump,rf,events):
        self.pump=pump;self.rf=rf;self.events=events
        self.publishing=True;self.abandoned_blocks=0
        self.generation=0;self.emitted=0;self.wire_epoch=None;self.config=None;self.pending=None

    def configure(self,config,now):
        c=self.pump.control
        if (self.pending is not None or self.pump.outgoing is not None or c.pending or
                c.state not in ('ready','stopped','done')):
            raise ValueError('Acquisition CONFIG requires confirmed idle output')
        c._clock(now)
        rid=c.journal.reserve(c.epoch,c.session)
        self.pump.outgoing=acquisition_request(rid,config);self.pump.written=0
        self.pending=(rid,config,now,c.epoch,c.session)

    def tick(self,now):
        if self.pending is not None and now-self.pending[2]>=self.pump.control.timeout:
            raise TimeoutError('Acquisition APPLIED timeout')

    def _announce(self,config,wire_epoch,first_index,request_id=0):
        self.generation+=1;self.config=config;self.wire_epoch=wire_epoch
        if not self.publishing:return
        self.events.put_nowait(dict(op='CONFIG_APPLIED',generation=self.generation,
                                   rf_barrier=self.emitted,first_index=first_index,
                                   config=config,wire_epoch=wire_epoch,request_id=request_id))

    def event(self,kind,value):
        if kind=='configuration':
            if self.pending is None or value.request_id!=self.pending[0]:
                raise ValueError('Unrequested acquisition confirmation')
            rid,wanted,_,epoch,session=self.pending
            if value.requested_bits!=wanted.bits or value.requested_period!=wanted.request_period:
                raise ValueError('Wrong requested acquisition profile')
            if value.phase==Phase.REJECTED:raise RuntimeError('Acquisition rejected')
            if value.phase==Phase.APPLIED:
                if value.active!=wanted:raise ValueError('Wrong applied acquisition profile')
                self.pump.control.journal.acknowledge(rid,session,epoch);self.pending=None
                if value.epoch==self.wire_epoch:
                    if value.active!=self.config:raise ValueError('Acquisition changed with same epoch')
                    # No new generation/index reset when firmware retains epoch.
                    if self.publishing:self.events.put_nowait(dict(op='CONFIG_CONFIRMED',request_id=rid))
                else:self._announce(value.active,value.epoch,0,rid)
        elif kind=='samples':
            decoder=self.pump.ingress.decoder
            if self.config is None:self._announce(decoder.config,decoder.epoch,value[0][3])
            if decoder.config!=self.config or decoder.epoch!=self.wire_epoch:
                raise ValueError('RF does not match published configuration')
            if not self.publishing:
                self.abandoned_blocks+=1;return
            # The numeric decoder allocates each frame separately. Transfer that
            # array without materializing Python rows; never mutate it after put.
            rows=value.array;rows.setflags(write=False)
            try:self.rf.put_nowait(Rf(int(rows[0,3]),len(rows),rows,self.generation,self.emitted))
            except queue.Full:raise RuntimeError('RF backpressure; no silent sample loss')
            self.emitted+=1
