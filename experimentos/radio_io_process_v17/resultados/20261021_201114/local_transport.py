"""Bounded local SCP1 peer for offline tests; never opens a connection."""
import struct
import time
import zlib
from monitor.v17.receiver import unoq_wav as wav
from monitor.v17.receiver.unoq_acquisition import Configuration


def seal(packet):
    struct.pack_into('<I',packet,988,zlib.crc32(packet[:988]));return bytes(packet)


class LocalTransport:
    """Deterministic SCP1 peer; no DAC clock, socket, hardware or Qt."""
    def __init__(self,write_limit=992,read_limit=32*992,realtime=False,rf_enabled=False):
        self.write_limit=write_limit;self.read_limit=read_limit
        self.sent=bytearray();self.incoming=bytearray();self.frames=[];self.close_calls=0
        self.session=0;self.total=0;self.accepted=self.played=0;self.state=wav.State.IDLE
        self.realtime=realtime;self.last=time.monotonic();self.fraction=0.;self.frame_count=0
        self.rf_enabled=rf_enabled;self.original_config=Configuration(14,125000)
        self.config=self.original_config;self.config_epoch=1;self.sample_index=0;self.next_rf=time.monotonic()
        self.sequence=0;self.eof=False;self.fail_send=False;self.block_send=False;self.drop=False

    def advance(self,now):
        if self.realtime and self.state==wav.State.PLAYING:
            due=(now-self.last)*40000+self.fraction;points=int(due);self.fraction=due-points
            available=self.accepted-self.played
            self.played+=min(points,available)
            if self.played==self.total:self.state=wav.State.DONE
            elif points>available:self.state=wav.State.UNDERRUN
        self.last=now
        burst=0
        while self.rf_enabled and now>=self.next_rf and burst<16:
            count=min(226,2048-self.sample_index%2048)
            p=bytearray(992)
            struct.pack_into('<4sHHII',p,0,b'SCP1',4,3,self.sequence,972);self.sequence+=1
            struct.pack_into('<i',p,32,992)
            struct.pack_into('<IIIIHBBIII',p,48,self.config.rate,self.sample_index,0,0,count,
                             14,2,self.config.period,self.sample_index//2048,self.config_epoch<<1)
            struct.pack_into('<I',p,80,(self.sample_index*self.config.period)&0xffffffff)
            for i in range(count):struct.pack_into('<HH',p,84+4*i,123,456)
            self._append(seal(p));self.sample_index=(self.sample_index+count)&0xffffffff
            self.next_rf+=count/self.config.rate;burst+=1

    def _append(self,packet):
        if len(self.incoming)+len(packet)>64*992:raise RuntimeError('Local reply queue full')
        self.incoming.extend(packet)

    def send(self,data):
        if self.fail_send:raise OSError('injected write error')
        if self.block_send:raise BlockingIOError()
        count=min(len(data),self.write_limit,992-len(self.sent));self.sent.extend(data[:count])
        if len(self.sent)==992:
            frame=bytes(self.sent);self.sent.clear();self.frames.append(frame);self.frame_count+=1
            if len(self.frames)>128:self.frames.pop(0)
            if (struct.unpack_from('<4sHH',frame)[:2]!=(b'SCP1',4) or
                    struct.unpack_from('<I',frame,12)[0]!=972 or
                    zlib.crc32(frame[:988])!=struct.unpack_from('<I',frame,988)[0]):
                raise AssertionError('Malformed local request')
            kind=struct.unpack_from('<H',frame,6)[0];rid=struct.unpack_from('<I',frame,8)[0]
            if kind==6:
                wanted=Configuration.from_wire(frame[16],struct.unpack_from('<I',frame,20)[0])
                if wanted.bits!=14 or wanted.rate not in (40000,125000):raise ValueError('Unsupported local RF model profile')
                self.config=wanted;self.config_epoch+=1;self.sample_index=0;self.next_rf=time.monotonic()
                response=bytearray(992)
                struct.pack_into('<4sHHII',response,0,b'SCP1',4,7,self.sequence,972);self.sequence+=1
                struct.pack_into('<IBBBBIII',response,16,rid,14,14,2,0,wanted.request_period,
                                 wanted.request_period,self.config_epoch)
                self._append(seal(response));return count
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
                self._append(seal(response))
        return count

    def recv(self,limit):
        if self.incoming:
            count=min(limit,self.read_limit,len(self.incoming))
            result=bytes(self.incoming[:count]);del self.incoming[:count];return result
        if self.eof:return b''
        raise BlockingIOError()

    def close(self):self.close_calls+=1

