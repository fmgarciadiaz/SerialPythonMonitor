import subprocess
import tempfile
import unittest
from dataclasses import FrozenInstanceError,replace
from pathlib import Path
from tools.ack_rf_contract_v19 import Context,Ledger,Outcome,CapacityError,reconstruct,BUFFERING_KIND,PLAYING_KIND
from monitor.v19.receiver.unoq_wav import Status,State
from monitor.v19.receiver.unoq_usb import ProtocolError

ROOT=Path(__file__).resolve().parents[2]
SKETCH=ROOT/'arduino/v19/oscilloscope/sketch'


def context(index=0,*,total=480*100,session=77,generation=1,count=480):
    return Context(0x80000001+index,session,index*480,count,total,40000,generation)


def fence_status(rid,session=77):
    return Status(rid,session,State.BUFFERING,0,26,1920,0,480*100,40000,7,30)


class AckRFContractTests(unittest.TestCase):
    def test_reconstruction_matches_actual_v19_queue_cpp_trace(self):
        source=r'''
#include <cstdio>
#include <cassert>
#include "generator_protocol.h"
#include "ack_rf_contract_v19.h"
int main(){
 using namespace scope_ack_rf_private;
 for(unsigned tail:{1U,37U,479U,480U}){
  wav::Queue q;q.begin(77,480*40+tail);unsigned id=0x80000001;
  for(unsigned i=0;i<30;++i){assert(q.accepts(q.accepted,480));unsigned offset=q.accepted;q.publish(480);
   scope_wav::Request r{id++,77,offset,0,0,480,0,true,nullptr,0};
   scope_wav::Reply s{r.id,77,q.state,0,uint16_t(q.free()),q.accepted,q.played,q.total};
   assert(eligible(r,s,false));assert(!eligible(r,s,true));
   printf("%u %u %u %u %u %u %u %u\n",r.id,r.offset,r.count,q.total,q.played,q.state,s.free,s.accepted);
  }
  assert(q.ready());q.state=scope_wav::PLAYING;
  for(unsigned i=0;i<11;++i){q.release();unsigned n=i==10?tail:480;assert(q.accepts(q.accepted,n));
   unsigned offset=q.accepted;q.publish(n);scope_wav::Request r{id++,77,offset,0,0,uint16_t(n),0,true,nullptr,0};
   scope_wav::Reply s{r.id,77,q.state,0,uint16_t(q.free()),q.accepted,q.played,q.total};assert(eligible(r,s,false));
   printf("%u %u %u %u %u %u %u %u\n",r.id,r.offset,r.count,q.total,q.played,q.state,s.free,s.accepted);
  }
 }
}
'''
        source='#include <initializer_list>\n'+source
        with tempfile.TemporaryDirectory() as temporary:
            p=Path(temporary);(p/'trace.cpp').write_text(source)
            subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(SKETCH),'-I',str(ROOT/'tools'),
                            str(p/'trace.cpp'),'-o',str(p/'trace')],check=True)
            lines=subprocess.check_output([str(p/'trace')],text=True).splitlines()
        self.assertEqual(len(lines),164)
        for line in lines:
            rid,offset,count,total,played,state,free,accepted=map(int,line.split())
            value=reconstruct(Context(rid,77,offset,count,total,40000,1),played,
                              BUFFERING_KIND if state==1 else PLAYING_KIND)
            self.assertEqual(value,Status(rid,77,State(state),0,free,accepted,played,total,40000,7,30))

    def test_context_is_immutable_and_rejects_impossible_geometry(self):
        with self.assertRaises(FrozenInstanceError):context().count=1
        for fields in (dict(request_id=3),dict(session=0),dict(offset=1),dict(count=0),dict(count=481),
                       dict(count=479),dict(queue_slots=16),dict(rates_mask=0),dict(rate=48000),
                       dict(total=2**32),dict(offset=2**32),dict(count=True),dict(generation=-1)):
            with self.subTest(fields=fields),self.assertRaises(ValueError):replace(context(),**fields)

    def test_played_state_and_uint32_boundaries(self):
        for played,kind in [(1,BUFFERING_KIND),(480,BUFFERING_KIND),(0,PLAYING_KIND),
                            (481,PLAYING_KIND),(1920,PLAYING_KIND),(-1,PLAYING_KIND),
                            (2**32,PLAYING_KIND),(False,BUFFERING_KIND),(0,20)]:
            with self.subTest(played=played,kind=kind),self.assertRaises(ProtocolError):
                reconstruct(context(),played,kind)
        offset=((2**32-1)//480)*480;count=2**32-1-offset
        c=Context(0xfffffffe,77,offset,count,2**32-1,50000,1)
        value=reconstruct(c,offset-960,PLAYING_KIND)
        self.assertEqual(value.accepted,0xffffffff);self.assertEqual(value.free_blocks,27)

    def test_ack_applied_once_and_unknown_never_grants_credit(self):
        ledger=Ledger(1);c=context();ledger.register(c)
        first=ledger.receive(c.request_id,0,BUFFERING_KIND)
        self.assertEqual(first.outcome,Outcome.APPLIED);self.assertEqual(first.status.accepted,480)
        self.assertEqual(ledger.receive(c.request_id,0,BUFFERING_KIND).outcome,Outcome.DUPLICATE)
        self.assertEqual(ledger.receive(0x80001000,0,BUFFERING_KIND).outcome,Outcome.UNKNOWN)
        self.assertEqual(len(ledger.retired),1);self.assertFalse(ledger.active)
        with self.assertRaises(ProtocolError):ledger.receive(c.request_id,0,PLAYING_KIND)
        with self.assertRaises(ProtocolError):ledger.register(c)

    def test_late_cancelled_ack_uses_original_context_without_credit(self):
        ledger=Ledger(1);old=context();ledger.register(old);ledger.cancel()
        new=context(1,session=88);ledger.register(new)
        self.assertEqual(ledger.receive(old.request_id,0,BUFFERING_KIND).outcome,Outcome.CANCELLED)
        self.assertEqual(ledger.retired[old.request_id].context.session,77)
        self.assertEqual(ledger.receive(new.request_id,0,BUFFERING_KIND).status.session,88)
        self.assertEqual(ledger.receive(old.request_id,0,BUFFERING_KIND).outcome,Outcome.CANCELLED)

    def test_reply_order_checked_before_mutation_and_failed_status_cannot_advance(self):
        ledger=Ledger(1);a,b=context(),context(1);ledger.register(a);ledger.register(b)
        with self.assertRaises(ProtocolError):ledger.receive(b.request_id,0,BUFFERING_KIND)
        self.assertEqual(len(ledger.active),2)
        with self.assertRaises(ProtocolError):ledger.receive(a.request_id,1,BUFFERING_KIND)
        self.assertEqual(len(ledger.active),2)
        ledger.receive(a.request_id,0,BUFFERING_KIND);ledger.receive(b.request_id,0,BUFFERING_KIND)

    def test_fifo_fence_never_discards_pending_context(self):
        ledger=Ledger(1);c=context();ledger.register(c);ledger.cancel()
        rid=0x80001000;ledger.register_fence(rid,77)
        with self.assertRaises(ProtocolError):ledger.confirm_fence(fence_status(rid))
        self.assertIn(c.request_id,ledger.retired)
        ledger.receive(c.request_id,0,BUFFERING_KIND)
        with self.assertRaises(ProtocolError):ledger.confirm_fence(fence_status(rid,88))
        ledger.confirm_fence(fence_status(rid));self.assertFalse(ledger.retired)
        self.assertFalse(ledger.fences)

    def test_capacity_failure_is_atomic_and_explicit(self):
        ledger=Ledger(1,active_limit=2,retired_limit=1)
        a,b=context(),context(1);ledger.register(a);ledger.register(b)
        with self.assertRaises(CapacityError):ledger.register(context(2))
        with self.assertRaises(CapacityError):ledger.cancel()
        self.assertEqual(len(ledger.active),2);self.assertFalse(ledger.retired)
        ledger.receive(a.request_id,0,BUFFERING_KIND)
        with self.assertRaises(CapacityError):ledger.receive(b.request_id,0,BUFFERING_KIND)
        self.assertIn(b.request_id,ledger.active);self.assertEqual(len(ledger.retired),1)

    def test_generation_and_full_reply_order(self):
        ledger=Ledger(2)
        with self.assertRaises(ProtocolError):ledger.register(context())
        first,second=0x80001000,0x80001001
        ledger.register_fence(first,77);ledger.register_fence(second,77)
        with self.assertRaises(ProtocolError):ledger.confirm_fence(fence_status(second))
        ledger.confirm_fence(fence_status(first));ledger.confirm_fence(fence_status(second))

    def test_sustained_bounded_history_with_explicit_fifo_fences(self):
        ledger=Ledger(1,retired_limit=8)
        for group in range(100):
            for index in range(4):
                c=context(group*4+index,total=480*1000);ledger.register(c)
                ledger.receive(c.request_id,0 if group==0 else c.offset-960,
                               BUFFERING_KIND if group==0 else PLAYING_KIND)
            rid=0x80010000+group;ledger.register_fence(rid,77);ledger.confirm_fence(fence_status(rid))
            self.assertFalse(ledger.retired);self.assertFalse(ledger.active)

    def test_cpp_selection_consumes_rf_once_and_preserves_eot_credits(self):
        source=r'''
#include <cassert>
#include "generator_protocol.h"
#include "ack_rf_contract_v19.h"
int main(){
 using namespace scope_ack_rf_private;
 for(unsigned mask=0;mask<128;++mask){
  bool wav=mask&1,ok=mask&2,other=mask&4,rf=mask&8,word=mask&16,pipeline=mask&32,last=mask&64;
  auto p=select(wav,ok,other,rf,word,pipeline,last);
  assert(p.fused==(wav&&ok&&rf));assert(p.take_wav==wav);
  bool take=rf && !(wav?!ok:other);assert(p.take_rf==take);
  if(p.fused)assert(p.half.source!=scope_batch2::Source::Reply);
  scope_batch2::Half pair[2]={p.half,p.half};
  auto failed=scope_batch2::credits_after_physical(pair,false);assert(!failed.frames&&!failed.nodes);
  auto good=scope_batch2::credits_after_physical(pair,true);
  assert(good.frames==unsigned(take&&!word)*2);
  assert(good.nodes==unsigned(take&&word&&last)*2);
 }
 scope_wav::Request r{0x80000001,77,0,0,1,480,0,true,nullptr,0};
 scope_wav::Reply s{r.id,77,scope_wav::BUFFERING,0,29,480,0,4800};
 assert(eligible(r,s,false));s.reason=1;assert(!eligible(r,s,false));s.reason=0;
 r.chunk=false;assert(!eligible(r,s,false));r.chunk=true;s.free=30;assert(!eligible(r,s,false));
}
'''
        with tempfile.TemporaryDirectory() as temporary:
            p=Path(temporary);(p/'test.cpp').write_text(source)
            subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(SKETCH),'-I',str(ROOT/'tools'),
                            str(p/'test.cpp'),'-o',str(p/'test')],check=True)
            subprocess.run([str(p/'test')],check=True)
