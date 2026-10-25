"""Serialized generator readback/OFF restore through existing strict protocol."""
from monitor.v18.receiver.unoq_generator import GeneratorConfig,generator_request
from monitor.v18.receiver.unoq_switch import Phase


class GeneratorPath:
    def __init__(self,pump):self.pump=pump;self.pending=None;self.observed=None;self.baseline=None

    def query(self,now):return self._request(now,None)

    def require_off(self):
        """Admission requires an observed OFF reference and no unresolved query."""
        if self.observed is not None and (self.observed.active.enabled or self.observed.running):
            raise ValueError('Known active generator; no experiment takeover')
        if self.baseline is None or self.observed is None or self.pending is not None:
            raise ValueError('Confirmed OFF generator baseline required')

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


class GeneratorReadbackGate:
    """RF-consumption gate for one owner lifetime; no event/RF buffer.

    Caller retains pending confirmations in a bounded FIFO and retries its
    oldest item. It must still service CONFIG events while RF catches up.
    A true result permits publication only at the RF-consumed watermark:
    future GUI/DSP integration also needs a DSP-completed watermark.
    RF generation is historical context, never a CONFIG/index reset.
    """
    def __init__(self):
        self.last_request_id=0x7fffffff;self.last_barrier=0;self.last_consumed=0

    def release(self,event,consumed):
        fields={'op','request_id','config','running','rf_barrier','rf_generation','epoch','session'}
        if (not isinstance(event,dict) or set(event)!=fields or event['op']!='GENERATOR_READBACK' or
                not isinstance(event['config'],GeneratorConfig) or type(event['running']) is not bool or
                any(type(event[key]) is not int for key in ('request_id','rf_barrier','rf_generation','epoch','session')) or
                not self.last_request_id<event['request_id']<0xffffffff or
                event['rf_barrier']<self.last_barrier or event['rf_generation']<0 or
                (event['rf_generation']==0 and event['rf_barrier']!=0) or
                not 0<=event['epoch']<2**63 or not 0<=event['session']<2**32 or
                type(consumed) is not int or consumed<self.last_consumed):
            raise ValueError('Invalid, duplicate or reordered generator readback barrier')
        self.last_consumed=consumed
        if consumed<event['rf_barrier']:return False
        self.last_request_id=event['request_id'];self.last_barrier=event['rf_barrier']
        return True
