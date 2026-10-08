import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import numpy as np
from PyQt6.QtCore import QLocale
from monitor.number_format import number
from monitor.v13.wav_source import seek_playback

class LocaleSeekTests(unittest.TestCase):
    def test_locale_decimal_and_grouping(self):
        for language, expected in [('de_DE','12.345,67'),('en_US','12,345.67')]:
            with patch('PyQt6.QtCore.QLocale.system', return_value=QLocale(language)):
                self.assertEqual(number(12345.67,'.2f'),expected)

    def test_seek_uses_played_not_buffered_and_confirms_stop(self):
        r=Mock();r.wav_rate=10;r.wav_status=SimpleNamespace(played=25)
        codes=np.arange(500);order=[]
        r.reset_wav_output.side_effect=lambda:order.append('stop')
        r.wav_request.side_effect=lambda *args:order.append('play')
        origin=seek_playback(r,codes,50,10)
        self.assertEqual(origin,175);self.assertEqual(order,['stop','play'])
        np.testing.assert_array_equal(r.wav_request.call_args.args[1],codes[175:])
        self.assertEqual(seek_playback(r,codes,0,-10),0)
        r.wav_request.reset_mock()
        self.assertEqual(seek_playback(r,codes,450,10),500)
        r.wav_request.assert_not_called()

    def test_stop_failure_does_not_start_new_session(self):
        r=Mock();r.wav_rate=10;r.wav_status=SimpleNamespace(played=25)
        r.reset_wav_output.side_effect=TimeoutError
        with self.assertRaises(TimeoutError):seek_playback(r,np.arange(500),0,10)
        r.wav_request.assert_not_called()
