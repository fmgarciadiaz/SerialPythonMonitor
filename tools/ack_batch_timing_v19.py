"""Bounded classification of MCU metadata accompanying correlated WAV replies."""
from collections import deque
from tools.spi_batch_timing_v19 import empty,add,report


class AckBatchTiming:
    def __init__(self):
        self.pending={};self.replies=deque(maxlen=3);self.groups={};self.last=None
        self.evicted=0;self.matched=0;self.unmatched=0;self.omitted=0

    def sent(self,request,session,label):
        if len(self.pending)>=64:
            self.pending.pop(next(iter(self.pending)));self.evicted+=1
        self.pending[request]=(session,label)

    def replied(self,sequence,request,session,reason):
        original=self.pending.pop(request,None)
        valid=original is not None and (original[0]==0 or original[0]==session)
        self.matched+=int(valid);self.unmatched+=int(not valid)
        self.replies.append((sequence//2,original[1] if valid else 'unmatched_ack',reason))

    def native(self,epoch,sequence,phase,prepare,check):
        # Sample only half 1: a preceding ACK from half 0 is then available.
        # ACK-only pairs and RF+ACK pairs have no usable native half 1.
        if not sequence&1 or self.last==(epoch,sequence//2):return
        self.last=(epoch,sequence//2)
        paired=next((r for r in reversed(self.replies) if r[0]==sequence//2),None)
        label,reason=(paired[1],paired[2]) if paired else ('no_wav_ack',0)
        key=(phase,label,reason)
        if key not in self.groups:
            if len(self.groups)>=64:self.omitted+=1;return
            self.groups[key]=dict(prepare=empty(),check=empty())
        group=self.groups[key];add(group['prepare'],prepare);add(group['check'],check)

    def report(self):
        return dict(groups=[dict(phase=p,ack_command=c,reason=r,
            prepare=report(g['prepare']),check=report(g['check']))
            for (p,c,r),g in sorted(self.groups.items())],matched_replies=self.matched,
            unmatched_replies=self.unmatched,pending=len(self.pending),evicted=self.evicted,
            omitted_groups=self.omitted,
            note='Native half 1 metadata, categorized by same-batch WAV reply id/session. prepare/check describe prior iteration; check includes decode_pair and command processing, not IRQ-lock duration alone. No WAV ACK does not mean no command. Lifecycle reply counters include non-target profiles; timing groups only target RF. ACK-only and RF+ACK pairs lack coverage.')
