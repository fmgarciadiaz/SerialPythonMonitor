import struct
from dataclasses import replace
import unittest
from experimentos.radio_io_process_v17.audio_control import AudioControl
from experimentos.radio_io_process_v17.prototype import Audio
from experimentos.radio_io_process_v17.wire_adapter import ProtocolIngress
from monitor.v17.receiver import unoq_wav as wav
from tests.v17.test_compact_protocol import seal


def reply(packet,state=wav.State.BUFFERING,accepted=0,played=0,free=30,total=4800,rate=40000,session=None,slots=30):
    rid=struct.unpack_from('<I',packet,8)[0]
    session=struct.unpack_from('<I',packet,16)[0] if session is None else session
    p=bytearray(992);struct.pack_into('<4sHHII',p,0,b'SCP1',4,12,0,972)
    struct.pack_into('<IIBBHIIIIII',p,16,rid,session,state,0,free,accepted,played,total,rate,7,slots)
    rows=[];ProtocolIngress(lambda _,value:rows.append(value)).feed(seal(p))
    return rows[0]


class AudioTests(unittest.TestCase):
    def ready(self,**kwargs):
        control=AudioControl(**kwargs)
        query=control.query(0)
        control.acknowledge(reply(query,wav.State.IDLE,total=0),.01)
        self.assertEqual(control.state,'ready')
        return control

    def buffering(self,**kwargs):
        control=self.ready(**kwargs)
        begin=control.begin(1,11,4800,40000,.02)
        control.acknowledge(reply(begin),.03)
        return control

    def chunk(self,control,offset=0,now=.04):
        return control.chunk(Audio(1,11,offset,bytes(960)),now)

    def test_begin_requires_capability_and_supports_16_or_30_slots(self):
        with self.assertRaises(ValueError):AudioControl().begin(1,11,4800,40000,0)
        for slots in (16,30):
            control=self.ready();packet=control.begin(1,11,4800,40000,.02)
            control.acknowledge(reply(packet,slots=slots,free=slots),.03)
            self.assertEqual(control.credits.available,slots)

    def test_commands_serialized_and_only_confirmed_prebuffer_allows_play(self):
        control=self.buffering();first=self.chunk(control)
        with self.assertRaises(ValueError):control.query(.04)
        with self.assertRaises(ValueError):control.play(.04)
        control.acknowledge(reply(first,accepted=480,free=29),.05)
        with self.assertRaises(ValueError):control.play(.05)
        second=self.chunk(control,480,.06)
        control.acknowledge(reply(second,accepted=960,free=28),.07)
        play=control.play(.08)
        control.acknowledge(reply(play,wav.State.PLAYING,accepted=960,free=28),.09)
        self.assertEqual(control.state,'playing')
        query=control.query(.1)
        control.acknowledge(reply(query,wav.State.PLAYING,accepted=960,played=480,free=29),.11)
        self.assertEqual(control.credits.available,29)

    def test_window_bounds_unconfirmed_chunks_without_offset_advance(self):
        control=self.buffering(window=2)
        self.chunk(control);self.chunk(control,480,.05)
        self.assertIsNone(self.chunk(control,960,.06))
        self.assertEqual(control.offset,960)
        self.assertEqual(len(control.pending),2)

    def test_stop_preempts_pending_and_old_reply_cannot_change_stopped_state(self):
        control=self.buffering();chunk=self.chunk(control)
        stop=control.stop(.05)
        self.assertFalse(control.acknowledge(reply(chunk,accepted=480,free=29),.06))
        control.acknowledge(reply(stop,wav.State.IDLE),.07)
        self.assertEqual(control.state,'stopped');self.assertIsNone(control.credits)
        begin=control.begin(2,11,4800,40000,.08)
        self.assertFalse(control.acknowledge(reply(chunk,accepted=480,free=29),.09))
        control.acknowledge(reply(begin),.1)
        self.assertEqual(control.credits.accepted,0)

    def test_timeout_does_not_return_credit_or_allow_late_ack_to_revive_audio(self):
        control=self.buffering();chunk=self.chunk(control)
        available=control.credits.available
        with self.assertRaises(TimeoutError):control.tick(.55)
        self.assertEqual(control.credits.available,available)
        with self.assertRaises(RuntimeError):control.acknowledge(reply(chunk,accepted=480,free=29),.56)
        self.assertEqual(control.state,'fault')
        stop=control.stop(.57)
        control.acknowledge(reply(stop,wav.State.IDLE),.58)
        self.assertEqual(control.state,'stopped')

    def test_wrong_session_and_capacity_change_fail_closed(self):
        for change in ({'session':22},{'slots':16,'free':15}):
            control=self.buffering();packet=self.chunk(control)
            fields=dict(accepted=480,free=29);fields.update(change)
            with self.assertRaises(ValueError):control.acknowledge(reply(packet,**fields),.05)
            self.assertEqual(control.state,'fault')

    def test_underrun_and_device_rejection_remain_failures(self):
        for state,reason in ((wav.State.UNDERRUN,0),(wav.State.BUFFERING,1)):
            control=self.buffering();packet=self.chunk(control)
            status=replace(reply(packet,accepted=480,free=29),state=state,reason=reason)
            with self.assertRaises(RuntimeError):control.acknowledge(status,.05)
            self.assertEqual(control.state,'fault')

    def test_discovery_does_not_take_over_an_existing_radio_session(self):
        control=AudioControl();query=control.query(0)
        control.acknowledge(reply(query,wav.State.PLAYING,session=99),.01)
        self.assertEqual(control.state,'occupied');self.assertEqual(control.session,99)
        with self.assertRaises(ValueError):control.begin(1,11,4800,40000,.02)
        stop=control.stop(.03)
        self.assertEqual(struct.unpack_from('<I',stop,16)[0],99)

    def test_short_wav_can_play_after_its_complete_confirmed_payload(self):
        control=self.ready();begin=control.begin(1,11,480,40000,.02)
        control.acknowledge(reply(begin,total=480),.03)
        packet=self.chunk(control)
        control.acknowledge(reply(packet,total=480,accepted=480,free=29),.05)
        play=control.play(.06)
        control.acknowledge(reply(play,wav.State.DONE,total=480,accepted=480,played=480),.07)
        self.assertEqual(control.state,'done')

    def test_unsupported_rate_is_rejected_without_sending_begin(self):
        control=self.ready();control.status=replace(control.status,rates_mask=1)
        with self.assertRaises(ValueError):control.begin(1,11,4800,40000,.02)
        self.assertEqual(control.pending,{});self.assertEqual(control.state,'ready')
