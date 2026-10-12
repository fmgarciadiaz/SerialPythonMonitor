import unittest,time
from dataclasses import replace
import numpy as np
from monitor.v16.fm_source import FMSource,FMParameters
from monitor.v16.synth_process import SynthProcess

class SynthProcessTests(unittest.TestCase):
    def test_receiver_does_not_reserve_or_advance_unready_worker(self):
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        from monitor.v16.receiver.unoq_config_receiver import OutputReceiver
        source=FMSource(20000,FMParameters())
        source.try_codes=MagicMock(side_effect=[None,np.full(480,2048,dtype='<u2')])
        socket=MagicMock();r=OutputReceiver(SimpleNamespace(socket=socket),lambda batch:None)
        r.wav_codes=source;r.wav_session=123;r.wav_status=SimpleNamespace(session=123,free_blocks=16,accepted=0)
        r.wav_levels=(1.,1.65);r.wav_previous_levels=(.5,1.65)
        r.service_wav()
        self.assertEqual(r.wav_next_offset,0);self.assertFalse(r.wav_inflight)
        self.assertEqual(r.wav_previous_levels,(.5,1.65));socket.sendall.assert_not_called()
        r.service_wav();self.assertEqual(r.wav_next_offset,480)
        socket.sendall.assert_called_once()
    def test_async_blocks_preserve_notes_pedal_and_dac_levels(self):
        p=FMParameters(preset='Piano Virtual',waveform='virtual',virtual_model='piano',notes=((60,100),(64,90)),oscillator_levels=(1.,0.,0.))
        reference=FMSource(20000,p);worker=SynthProcess(20000,p)
        try:
            for index in range(4):
                if index==1:
                    p=replace(p,notes=((67,110),),note_id=1,virtual_sustain=True)
                    reference.update(p);worker.update(p)
                if index==2:
                    p=replace(p,notes=(),virtual_sustain=False)
                    reference.update(p);worker.update(p)
                a,b=index*480,(index+1)*480
                expected=reference.render_dac_codes(a,b,1.5,1.65)
                deadline=time.monotonic()+10;actual=None
                while actual is None and time.monotonic()<deadline:
                    actual=worker.try_codes(a,b,(1.5,1.65))
                    if actual is None:time.sleep(.001)
                self.assertIsNotNone(actual);np.testing.assert_array_equal(actual,expected)
                self.assertEqual(worker.position,b)
        finally:worker.close()
        self.assertFalse(worker._process.is_alive());worker.close()

if __name__=='__main__':unittest.main()
