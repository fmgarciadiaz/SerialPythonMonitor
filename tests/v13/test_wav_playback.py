import os
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scipy.io import wavfile
from monitor.historico.v13.wav_source import prepare_wav
from monitor.historico.v13.receiver import unoq_wav as wav
from monitor.historico.v13.receiver.unoq_config_receiver import OutputReceiver


def reply(rid, session=0, state=0, free=16, accepted=0, played=0, total=0):
    p=bytearray(992)
    struct.pack_into('<4sHHII',p,0,b'SCP1',3,12,0,972)
    struct.pack_into('<IIBBHIIII',p,16,rid,session,state,0,free,accepted,played,total,20000)
    struct.pack_into('<I',p,988,zlib.crc32(p[:988]))
    return wav.status(p)

class WavConversionTests(unittest.TestCase):
    def write(self, data, rate=48000):
        directory=tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path=Path(directory.name)/'source.wav'
        wavfile.write(path,rate,data)
        return path
    def test_channels_bias_codes_and_duration(self):
        t=np.arange(48000)/48000
        stereo=np.column_stack((.3*np.sin(2*np.pi*1000*t)+.2,.2*np.sin(2*np.pi*2000*t)-.1)).astype(np.float32)
        path=self.write(stereo)
        for channel, frequency in [('L',1000),('R',2000)]:
            source=prepare_wav(path,channel)
            self.assertEqual(len(source.codes),20000)
            self.assertAlmostEqual(source.codes.mean(),2047.5,delta=1)
            self.assertGreater(source.codes.min(),0)
            self.assertLess(source.codes.max(),4095)
            peak=np.argmax(abs(np.fft.rfft(source.codes.astype(float)-source.codes.mean())))
            self.assertEqual(peak,frequency)
        self.assertEqual(prepare_wav(path,'Mix').channels,2)
    def test_antialias_filter(self):
        t=np.arange(48000)/48000
        data=(.5*np.sin(2*np.pi*1000*t)+.5*np.sin(2*np.pi*15000*t)).astype(np.float32)
        source=prepare_wav(self.write(data))
        spectrum=abs(np.fft.rfft(source.codes.astype(float)-source.codes.mean()))
        self.assertLess(spectrum[5000]/spectrum[1000],.01)
    def test_unsigned_silence_and_nonfinite(self):
        self.assertTrue(np.all(prepare_wav(self.write(np.full(1000,128,dtype=np.uint8))).codes==2048))
        with self.assertRaises(ValueError): prepare_wav(self.write(np.array([np.nan],dtype=np.float32)))
    def test_frames_and_status(self):
        p=wav.chunk(0x80000001,123,0,np.arange(480,dtype=np.uint16))
        self.assertEqual(len(p),992)
        self.assertEqual(struct.unpack_from('<IIHH',p,16),(123,0,480,0))
        self.assertEqual(zlib.crc32(p[:988]),struct.unpack_from('<I',p,988)[0])
        with self.assertRaises(ValueError): wav.chunk(0x80000001,1,0,[4096])
        self.assertEqual(reply(0x80000001).rate,20000)
    def test_decoder_interleaves_wav_without_changing_adc(self):
        from monitor.historico.v13.receiver.unoq_config_decoder import ConfigurationDecoder
        decoder=ConfigurationDecoder()
        p=bytearray(992)
        struct.pack_into('<4sHHII',p,0,b'SCP1',3,12,10,972)
        struct.pack_into('<IIBBHIIII',p,16,0x80000001,123,1,0,16,0,0,1000,20000)
        struct.pack_into('<I',p,988,zlib.crc32(p[:988]))
        self.assertEqual(decoder.feed(p[:400]),[])
        self.assertEqual(decoder.feed(p[400:]),[])
        self.assertEqual(decoder.events[0][0],'wav')
        self.assertEqual(decoder.events[0][1].session,123)
        self.assertIsNone(decoder.config)
        p[28] ^= 1
        from monitor.historico.v13.receiver.unoq_usb import ProtocolError
        with self.assertRaises(ProtocolError): decoder.feed(p)

    def test_candidate_gate_and_credit(self):
        class Socket:
            def __init__(self): self.frames=[]
            def sendall(self,p): self.frames.append(p)
        class Connection:
            socket=Socket()
        with patch.dict(os.environ,{},clear=True):
            receiver=OutputReceiver(Connection(),lambda samples:None)
            with self.assertRaises(ValueError): receiver.wav_request()
        detected=Connection()
        detected.wav_firmware=True
        with patch.dict(os.environ,{},clear=True):
            self.assertTrue(OutputReceiver(detected,lambda samples:None).wav_candidate)
        receiver.wav_candidate=True
        receiver.wav_request(1,np.arange(1000,dtype=np.uint16))
        rid=struct.unpack_from('<I',receiver.connection.socket.frames[-1],8)[0]
        receiver.wav_status=reply(rid,receiver.wav_session,1,total=1000)
        receiver.wav_pending=None
        receiver.service_wav()
        self.assertEqual(struct.unpack_from('<H',receiver.connection.socket.frames[-1],6)[0],13)
        count=len(receiver.connection.socket.frames)
        receiver.service_wav()
        self.assertEqual(len(receiver.connection.socket.frames),count)
        receiver.wav_status=reply(rid,receiver.wav_session,1,0,480,0,1000)
        receiver.wav_pending=None
        receiver.service_wav()
        self.assertEqual(receiver.connection.socket.frames[-1][20],2)

    def test_stale_status_does_not_end_current_stream(self):
        import time
        from unittest.mock import MagicMock
        connection=MagicMock();connection.read.return_value=b''
        receiver=OutputReceiver(connection,lambda samples:None)
        receiver.wav_codes=np.zeros(1000,dtype=np.uint16)
        receiver.wav_session=123
        receiver.wav_pending=(0x80000001,time.monotonic())
        receiver.decoder.feed=MagicMock()
        receiver.decoder.events=[('wav',reply(0x80000002,123,3,total=1000))]
        receiver.pump()
        self.assertIsNotNone(receiver.wav_codes)
        self.assertEqual(receiver.wav_pending[0],0x80000001)

    def test_invalid_credit_is_rejected(self):
        from monitor.historico.v13.receiver.unoq_usb import ProtocolError
        with self.assertRaises(ProtocolError):reply(0x80000001,free=17)


    def test_resampling_higher_rates_preserves_duration_and_tone(self):
        t=np.arange(96000)/96000
        path=self.write(np.sin(2*np.pi*12000*t).astype(np.float32),96000)
        for rate in (40000,50000):
            source=prepare_wav(path,rate_out=rate)
            self.assertEqual(source.output_rate,rate)
            self.assertEqual(len(source.codes),rate)
            self.assertEqual(source.duration,1)
            peak=np.argmax(abs(np.fft.rfft(source.codes.astype(float)-source.codes.mean())))
            self.assertEqual(peak,12000)
            frame=wav.command(0x80000001,77,1,len(source.codes),rate)
            self.assertEqual(struct.unpack_from('<I',frame,28)[0],rate)

    def test_higher_rate_requires_advertised_capability(self):
        from unittest.mock import MagicMock
        connection=MagicMock()
        receiver=OutputReceiver(connection,lambda samples:None)
        receiver.wav_candidate=True
        receiver.wav_status=reply(0x80000001)
        with self.assertRaises(ValueError):receiver.wav_request(1,np.zeros(1000,dtype=np.uint16),40000)
        self.assertIsNone(receiver.wav_codes)
        from dataclasses import replace
        receiver.wav_status=replace(receiver.wav_status,rates_mask=7)
        receiver.wav_request(1,np.zeros(1000,dtype=np.uint16),50000)
        self.assertEqual(receiver.wav_rate,50000)
        self.assertEqual(struct.unpack_from('<I',connection.socket.sendall.call_args.args[0],28)[0],50000)

if __name__=='__main__': unittest.main()
