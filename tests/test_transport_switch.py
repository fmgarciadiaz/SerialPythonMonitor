"""Execute the MCU-side C++ contract and decode its replies in Python."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zlib
from transport.unoq_switch import Mode, Phase, Reason, switch_request, switch_reply
from transport.unoq_usb import ProtocolError

ROOT = Path(__file__).resolve().parents[1]


class SwitchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        source = Path(cls.tmp.name)/'switch.cpp'
        cls.exe = Path(cls.tmp.name)/'switch'
        source.write_text(r'''
#include <cassert>
#include <cstdio>
#include "control_protocol.h"
using namespace scope_control;
int main() {
    uint8_t p[BLOCK]; Request r{}; Reply reply{}; Switch state;
    assert(fread(p,1,BLOCK,stdin)==BLOCK);
    if(!decode(p,BLOCK,r)) return 2;
    auto emit=[&](Reply v) { encode(p,0,v); assert(fwrite(p,1,BLOCK,stdout)==BLOCK); };
    emit(state.submit(r));
    emit(state.submit(r)); // same request: no second application
    emit(state.submit({r.id,uint8_t(r.mode^1)})); // ID conflict
    emit(state.submit({r.id+1,SPI})); // busy
    assert(!state.complete(53,true,reply)); // cannot cut an ADC node
    assert(state.complete(2048,true,reply)); emit(reply);
    assert(!state.complete(4096,true,reply));
    emit(state.submit(r)); // cached applied ACK
    emit(state.submit({r.id+1,SPI}));
    assert(state.complete(4096,false,reply)); emit(reply); // keep UART on failure
    emit(state.submit({r.id+2,SPI}));
    assert(state.complete(0,true,reply)); emit(reply); // index wrap is a boundary
    emit(state.submit({r.id+3,99})); // valid frame / unsupported semantic mode
}
''')
        subprocess.run(['c++','-std=c++11','-Wall','-Wextra','-Werror',
                        '-I',str(ROOT/'transport'),str(source),'-o',str(cls.exe)],check=True)

    def run_mcu(self, packet):
        return subprocess.run([str(self.exe)],input=packet,capture_output=True)

    def responses(self):
        result=self.run_mcu(switch_request(0x80000100,Mode.UART))
        self.assertEqual(result.returncode,0,result.stderr)
        return [result.stdout[i:i+512] for i in range(0,len(result.stdout),512)]

    def test_accept_apply_retry_busy_failure_and_return_to_spi(self):
        packets=self.responses()
        expected=[(0,1,Phase.ACCEPTED,Reason.OK,Mode.SPI),
                  (0,1,Phase.ACCEPTED,Reason.OK,Mode.SPI),
                  (0,0,Phase.REJECTED,Reason.ID_CONFLICT,Mode.SPI),
                  (1,0,Phase.REJECTED,Reason.BUSY,Mode.SPI),
                  (0,1,Phase.APPLIED,Reason.OK,Mode.UART),
                  (0,1,Phase.APPLIED,Reason.OK,Mode.UART),
                  (1,0,Phase.ACCEPTED,Reason.OK,Mode.UART),
                  (1,0,Phase.REJECTED,Reason.HARDWARE,Mode.UART),
                  (2,0,Phase.ACCEPTED,Reason.OK,Mode.UART),
                  (2,0,Phase.APPLIED,Reason.OK,Mode.SPI),
                  (3,99,Phase.REJECTED,Reason.UNSUPPORTED,Mode.SPI)]
        self.assertEqual(len(packets),len(expected))
        for packet,(delta,target,phase,reason,active) in zip(packets,expected):
            reply=switch_reply(packet,0x80000100+delta,target)
            self.assertEqual((reply.phase,reply.reason,reply.active),(phase,reason,active))
        self.assertEqual(switch_reply(packets[4],0x80000100,1).boundary,2048)

    def test_mcu_rejects_corrupt_truncated_and_reserved_fields(self):
        original=switch_request(0x80000100,Mode.UART)
        self.assertEqual(self.run_mcu(original[:-1]).returncode != 0,True)
        for offset in (0,4,6,12,17,507,508):
            packet=bytearray(original);packet[offset]^=1
            if offset!=508:
                struct.pack_into('<I',packet,508,zlib.crc32(packet[:508]))
            self.assertNotEqual(self.run_mcu(packet).returncode,0)

    def test_python_requires_matching_ack_crc_and_consistent_state(self):
        original=self.responses()[4]
        with self.assertRaises(ProtocolError):switch_reply(original,0x80000101,1)
        with self.assertRaises(ProtocolError):switch_reply(original,0x80000100,0)
        with self.assertRaises(ProtocolError):switch_reply(original[:-1],0x80000100,1)
        for offset,value in ((21,0),(22,99),(23,1),(24,1),(28,1),(508,0)):
            packet=bytearray(original);packet[offset]=value
            if offset!=508:
                struct.pack_into('<I',packet,508,zlib.crc32(packet[:508]))
            else:packet[509]^=1
            with self.assertRaises(ProtocolError):switch_reply(packet,0x80000100,1)

    def test_invalid_requests_rejected_locally(self):
        for rid,mode in ((0,0),(0xffffffff,0),(0x100000000,0),(0x80000000,2)):
            with self.assertRaises(ValueError):switch_request(rid,mode)
