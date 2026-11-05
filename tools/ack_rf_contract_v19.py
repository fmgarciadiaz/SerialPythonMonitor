"""Unqualified offline ACK/RF prototype; known review gaps in DISENO_ACK_RF_V19_20261031.md. No production factory enables it.

Kinds are provisional and do not extend the accepted receiver whitelist.
The caller must validate the original RF frame (CRC/sequence/profile/samples)
independently; ACK lookup outcomes never determine whether valid RF is kept.
"""
from collections import OrderedDict
from dataclasses import dataclass,fields
from enum import Enum
from monitor.v19.receiver.unoq_wav import Status,State,CHUNK,RATES
from monitor.v19.receiver.unoq_usb import ProtocolError

BUFFERING_KIND=22
PLAYING_KIND=23


@dataclass(frozen=True)
class Context:
    request_id:int
    session:int
    offset:int
    count:int
    total:int
    rate:int
    generation:int
    queue_slots:int=30
    rates_mask:int=7

    def __post_init__(self):
        if any(type(getattr(self,f.name)) is not int for f in fields(self)):
            raise ValueError('Integer ACK/RF context fields required')
        if (not 0x80000000<=self.request_id<0xffffffff or not 1<=self.session<=0xffffffff
                or not 0<=self.generation<=0xffffffff or self.rate not in RATES
                or self.queue_slots!=30 or self.rates_mask!=7
                or not 1<=self.total<=0xffffffff or self.offset<0 or self.offset%CHUNK
                or not 1<=self.count<=CHUNK or self.offset+self.count>self.total
                or (self.count!=CHUNK and self.offset+self.count!=self.total)):
            raise ValueError('Invalid immutable ACK/RF request context')


def reconstruct(context,played,kind):
    """Rebuild only the exact successful new-CHUNK status, never an error ACK."""
    if kind not in (BUFFERING_KIND,PLAYING_KIND):raise ProtocolError('Unknown private ACK/RF kind')
    accepted=context.offset+context.count
    if type(played) is not int or not 0<=played<=accepted or played%CHUNK:
        raise ProtocolError('Contradictory ACK/RF played counter')
    used=(accepted-played+CHUNK-1)//CHUNK
    state=State.BUFFERING if kind==BUFFERING_KIND else State.PLAYING
    if not 1<=used<=context.queue_slots or (state==State.BUFFERING and played) or (state==State.PLAYING and used<3):
        raise ProtocolError('Contradictory ACK/RF queue ownership')
    return Status(context.request_id,context.session,state,0,context.queue_slots-used,
                  accepted,played,context.total,context.rate,context.rates_mask,context.queue_slots)


class Outcome(Enum):
    APPLIED='applied'
    DUPLICATE='duplicate'
    CANCELLED='cancelled'
    UNKNOWN='unknown'


@dataclass(frozen=True)
class Result:
    outcome:Outcome
    status:Status|None=None


@dataclass(frozen=True)
class Retired:
    context:Context
    ordinal:int
    status:Status|None
    cancelled:bool=False


@dataclass(frozen=True)
class Fence:
    request_id:int
    session:int
    ordinal:int
    generation:int


class CapacityError(RuntimeError):pass


class Ledger:
    """Bounded immutable requests and tombstones; no silent in-flight eviction.

    A verified full QUERY/STOP ACK is an explicit FIFO fence. Only that event
    can retire older tombstones. The adapter must correlate that full ACK and
    validate sequence/CRC before calling confirm_fence. No time-based expiry.
    """
    def __init__(self,generation,*,active_limit=32,retired_limit=256):
        if min(active_limit,retired_limit)<1:raise ValueError('Positive ledger bounds required')
        self.generation=generation;self.active_limit=active_limit;self.retired_limit=retired_limit
        self.active={};self.retired=OrderedDict();self.fences={};self.ordinal=0

    def register(self,context):
        if context.generation!=self.generation:raise ProtocolError('ACK/RF generation mismatch')
        rid=context.request_id
        if rid in self.active or rid in self.retired or rid in self.fences:
            raise ProtocolError('ACK/RF request ID still retained')
        if len(self.active)>=self.active_limit:raise CapacityError('ACK/RF active limit')
        self.ordinal+=1;self.active[rid]=(context,self.ordinal)

    def cancel(self):
        if len(self.retired)+len(self.active)>self.retired_limit:
            raise CapacityError('ACK/RF tombstone limit before cancellation')
        for rid,(context,ordinal) in self.active.items():
            self.retired[rid]=Retired(context,ordinal,None,True)
        self.active.clear()

    def _ensure_order(self,ordinal):
        if (any(order<ordinal for _,order in self.active.values())
                or any(old.ordinal<ordinal and old.status is None for old in self.retired.values())
                or any(other.ordinal<ordinal for other in self.fences.values())):
            raise ProtocolError('ACK/RF reply overtook an outstanding WAV reply')

    def receive(self,request_id,played,kind):
        if request_id in self.active:
            context,ordinal=self.active[request_id]
            self._ensure_order(ordinal)
            status=reconstruct(context,played,kind)
            if len(self.retired)>=self.retired_limit:raise CapacityError('ACK/RF tombstone limit before ACK')
            del self.active[request_id]
            self.retired[request_id]=Retired(context,ordinal,status)
            return Result(Outcome.APPLIED,status)
        old=self.retired.get(request_id)
        if old is None:return Result(Outcome.UNKNOWN)
        if old.status is None:self._ensure_order(old.ordinal)
        status=reconstruct(old.context,played,kind)
        if old.status is not None and status!=old.status:
            raise ProtocolError('Conflicting duplicate ACK/RF status')
        if old.status is None:self.retired[request_id]=Retired(old.context,old.ordinal,status,True)
        return Result(Outcome.CANCELLED if old.cancelled else Outcome.DUPLICATE)

    def register_fence(self,request_id,session):
        if not 0x80000000<=request_id<0xffffffff or not 0<=session<=0xffffffff:
            raise ValueError('Invalid FIFO fence')
        if request_id in self.active or request_id in self.retired or request_id in self.fences:
            raise ProtocolError('FIFO fence request ID still retained')
        if len(self.fences)>=self.active_limit:raise CapacityError('ACK/RF fence limit')
        self.ordinal+=1
        self.fences[request_id]=Fence(request_id,session,self.ordinal,self.generation)

    def confirm_fence(self,status):
        fence=self.fences.get(status.request_id)
        if fence is None or status.reason or (fence.session and status.session!=fence.session):
            raise ProtocolError('Unverified FIFO fence ACK')
        self._ensure_order(fence.ordinal)
        self.retired=OrderedDict((rid,old) for rid,old in self.retired.items() if old.ordinal>fence.ordinal)
        del self.fences[status.request_id]
