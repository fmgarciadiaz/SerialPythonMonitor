"""Audio already buffered must remain readable while loop detection computes."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch
import numpy as np
from monitor.v18.radio_output import RadioDacSource,HighRateRadioDacSource
from monitor.v18 import radio_loop_guard

class RadioSourceConcurrencyTests(TestCase):
    def source(self):
        source=RadioDacSource(1,buffer_seconds=0)
        source.feed_result(dict(settings=SimpleNamespace(radio_offset=0),
            radio_key=('station','AM',40000),audio=np.ones(960)*.1))
        return source

    def test_buffered_chunk_is_available_during_real_loop_correlation(self):
        source=self.source();entered=Event();release=Event();delivered=Event()
        rng=np.random.default_rng(400)
        source.loop_guard.sent(rng.integers(600,3500,16000,dtype=np.uint16),0)
        observe_values=rng.normal(0,.2,512)
        correlate=radio_loop_guard.correlate
        def paused_correlate(*args,**kwargs):
            entered.set()
            if not release.wait(5):raise TimeoutError('Correlation was not released')
            return correlate(*args,**kwargs)
        def consume():
            try:return source.try_codes(0,480)
            finally:delivered.set()
        with patch.object(radio_loop_guard,'correlate',paused_correlate),ThreadPoolExecutor(2) as pool:
            observer=pool.submit(source.observe_input,observe_values,4000)
            try:
                self.assertTrue(entered.wait(2),'Real correlation was not reached')
                consumer=pool.submit(consume)
                self.assertTrue(delivered.wait(1),'Loop detection holds the audio buffer lock')
                codes=consumer.result()
                self.assertEqual(len(codes),480)
                self.assertTrue(np.all(codes<=4095))
            finally:release.set()
            observer.result(timeout=2)
        self.assertEqual(source._position,480)
        self.assertEqual((source.chunk_burst,HighRateRadioDacSource.chunk_burst),(8,16))

    def test_close_and_existing_error_win_over_late_loop_detection(self):
        for close in (False,True):
            with self.subTest(close=close):
                source=self.source();entered=Event();release=Event()
                def detect(*args):
                    entered.set()
                    if not release.wait(5):raise TimeoutError('Detection not released')
                    return True
                with patch.object(source.loop_guard,'observe',detect),ThreadPoolExecutor(1) as pool:
                    observer=pool.submit(source.observe_input,[0.,.1],4000)
                    try:
                        self.assertTrue(entered.wait(2))
                        if close:source.close()
                        else:
                            with source._lock:source.error='first error'
                    finally:release.set()
                    observer.result(timeout=2)
                self.assertIsNone(source.try_codes(0,480))
                if close:self.assertTrue(source.closed)
                else:self.assertEqual(source.error,'first error')

    def test_positive_detection_still_stops_subsequent_audio(self):
        source=self.source()
        with patch.object(source.loop_guard,'observe',return_value=True):source.observe_input([0.,.1],4000)
        self.assertIn('realimentación',source.error)
        self.assertEqual(source._available,0)
        self.assertIsNone(source.try_codes(0,480))

if __name__=='__main__':main()
