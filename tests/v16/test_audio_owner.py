import unittest
import numpy as np
from diagnosticos.probar_audio_owner_v16 import validate_adc_batch,monitor_processes,require_available_wav

class AudioOwnerIpcTests(unittest.TestCase):
    def test_accepts_completed_wav_without_stopping_another_session(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from monitor.v16.receiver.unoq_wav import State
        receiver=Mock(wav_status=SimpleNamespace(state=State.DONE,reason=0))
        require_available_wav(receiver,SimpleNamespace(enabled=False))
        receiver.wav_request.assert_not_called()
        for state,reason,enabled in ((State.PLAYING,0,False),(State.DONE,2,False),(State.DONE,0,True)):
            receiver=Mock(wav_status=SimpleNamespace(state=state,reason=reason))
            with self.assertRaises(RuntimeError):require_available_wav(receiver,SimpleNamespace(enabled=enabled))
            receiver.wav_request.assert_not_called()

    def test_preflight_detects_open_monitors_and_ignores_current_process(self):
        text="""101 /env/bin/python /project/monitor/v16/app.py
102 python iniciar_monitor.py --version v16
103 python diagnosticos/probar_audio_owner_v16.py
104 python /project/monitor/historico/v15/app.py
"""
        self.assertEqual(monitor_processes(text,103),[101,102,104])
        self.assertEqual(monitor_processes(text,101),[102,104])

    def test_40khz_timestamps_are_checked_with_actual_period(self):
        data=np.array([[25,1,2,1],[50,2,3,2]],dtype=np.uint32)
        self.assertEqual(validate_adc_batch(data,0,0,25),(2,50,2))
        with self.assertRaises(ValueError):validate_adc_batch(data,0,0,10)

    def test_wrap_and_continuity_across_batches(self):
        data=np.array([[0xfffffffa,1,16383,0xffffffff],[4,2,0,0]],dtype=np.uint32)
        self.assertEqual(validate_adc_batch(data,0xfffffffe,0xfffffff0),(0,4,2))
        self.assertEqual(validate_adc_batch(np.array([[14,3,4,1]],dtype=np.uint32),0,4),(1,14,1))
    def test_rejects_gaps_and_bad_codes(self):
        valid=np.array([[10,1,2,1],[20,3,4,2]],dtype=np.uint32)
        for column,value in ((0,21),(3,3),(1,16384),(2,16384)):
            bad=valid.copy();bad[1,column]=value
            with self.assertRaises(ValueError):validate_adc_batch(bad,0,0)
        with self.assertRaises(ValueError):validate_adc_batch(valid,7,0)
        with self.assertRaises(ValueError):validate_adc_batch(valid,0,4)

if __name__=='__main__':unittest.main()
