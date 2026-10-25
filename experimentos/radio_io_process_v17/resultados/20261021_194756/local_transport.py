"""Bounded local SCP1 peer for offline tests; never opens a connection."""
import struct
import time
import zlib
from monitor.v17.receiver import unoq_wav as wav


def seal(packet):
    struct.pack_into('<I',packet,988,zlib.crc32(packet[:988]));return bytes(packet)


class LocalTransport:
    """Deterministic SCP1 peer; no DAC clock, socket, hardware or Qt."""
    def __init__(self,write_limit=992,read_limit=32*992,realtime=False):
        self.write_limit=write_limit;self.read_limit=read_limit
        self.sent=bytearray();self.incoming=bytearray();self.frames=[];self.close_calls=0
        self.session=0;self.total=0;self.accepted=self.played=0;self.state=wav.State.IDLE
        self.realtime=realtime;self.last=time.monotonic();self.fraction=0.;self.frame_count=0
        self.sequence=0;self.eof=False;self.fail_send=False;self.block_send=False;self.drop=False

    def advance(self,now):
        if self.realtime and self.state==wav.State.PLAYING:
            due=(now-self.last)*40000+self.fraction;points=int(due);self.fraction=due-points
            available=self.accepted-self.played
            self.played+=min(points,available)
            if self.played==self.total:self.state=wav.State.DONE
            elif points>available:self.state=wav.State.UNDERRUN
        self.last=now

    def send(self,data):
        if self.fail_send:raise OSError('injected write error')
        if self.block_send:raise BlockingIOError()
        count=min(len(data),self.write_limit);self.sent.extend(data[:count])
        if len(self.sent)==992:
            frame=bytes(self.sent);self.sent.clear();self.frames.append(frame);self.frame_count+=1
            if len(self.frames)>128:self.frames.pop(0)
            if (struct.unpack_from('<4sHH',frame)[:2]!=(b'SCP1',4) or
                    struct.unpack_from('<I',frame,12)[0]!=972 or
                    zlib.crc32(frame[:988])!=struct.unpack_from('<I',frame,988)[0]):
                raise AssertionError('Malformed local request')
            kind=struct.unpack_from('<H',frame,6)[0];rid=struct.unpack_from('<I',frame,8)[0]
            session=struct.unpack_from('<I',frame,16)[0]
            if kind==13:
                offset,points=struct.unpack_from('<IH',frame,20)
                if session!=self.session or offset!=self.accepted:raise AssertionError('Invalid peer chunk')
                self.accepted+=points
            else:
                op=frame[20]
                if op==1:
                    self.session=session;self.total=struct.unpack_from('<I',frame,24)[0]
                    self.accepted=self.played=0;self.state=wav.State.BUFFERING
                elif op==2:self.state=wav.State.PLAYING;self.last=time.monotonic();self.fraction=0.
                elif op==3:self.state=wav.State.IDLE
            response=bytearray(992)
            struct.pack_into('<4sHHII',response,0,b'SCP1',4,12,self.sequence,972);self.sequence+=1
            free=30-(self.accepted-self.played+479)//480
            struct.pack_into('<IIBBHIIIIII',response,16,rid,self.session,self.state,0,free,
                             self.accepted,self.played,self.total,40000,7,30)
            if not self.drop:
                if len(self.incoming)+992>64*992:raise RuntimeError('Local reply queue full')
                self.incoming.extend(seal(response))
        return count

    def recv(self,limit):
        if self.incoming:
            count=min(limit,self.read_limit,len(self.incoming))
            result=bytes(self.incoming[:count]);del self.incoming[:count];return result
        if self.eof:return b''
        raise BlockingIOError()

    def close(self):self.close_calls+=1

