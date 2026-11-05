from pathlib import Path
from types import SimpleNamespace
import unittest
from tools.probe_v20_gui import scenario_command,queue_capacity

class ScenarioTests(unittest.TestCase):
    def command(self,**changes):
        args=dict(serial='test',bits=8,rate=1860465,hold=20,analysis_mode=None,us=False,scan_during_a0=False,wav=False,fm=False,voices=1,window_seconds=0,detail_percent=None)
        return scenario_command(SimpleNamespace(**dict(args,**changes)),Path('/binding'),Path('/out'))
    def test_us_before_and_during_are_mutually_selected(self):
        first=self.command(us=True);during=self.command(us=True,scan_during_a0=True)
        self.assertIn('--us',first);self.assertIn('--scan',first)
        self.assertIn('--us',during);self.assertIn('--scan-during-a0',during);self.assertNotIn('--scan',during)
    def test_analysis_has_no_audio_hold_and_explicit_bits_rate(self):
        cmd=self.command(analysis_mode='heatmap',bits=14,rate=31250)
        self.assertIn('--fft-only',cmd);self.assertEqual(cmd[cmd.index('--hold-radio-seconds')+1],'0')
        self.assertEqual(cmd[cmd.index('--bits')+1],'14');self.assertEqual(cmd[cmd.index('--rate')+1],'31250')
        self.assertNotIn('--wav',cmd);self.assertNotIn('--fm',cmd)
    def test_ordinary_audio_command_retains_hold_and_selection(self):
        cmd=self.command(wav=True,fm=True,voices=20)
        self.assertEqual(cmd[cmd.index('--hold-radio-seconds')+1],'20')
        self.assertIn('--wav',cmd);self.assertIn('--fm',cmd);self.assertNotIn('--scan',cmd)

    def test_capacity_follows_actual_profile_instead_of_adc8_arena_maximum(self):
        self.assertEqual(queue_capacity(8,1860465),16)
        self.assertEqual(queue_capacity(10,1355932),4)
        self.assertEqual(queue_capacity(12,1103448),4)
        self.assertEqual(queue_capacity(16,150943),4)
        self.assertEqual(queue_capacity(14,31250),4)

    def test_radio_time_window_keeps_time_view_and_audio_hold(self):
        cmd=self.command(window_seconds=2,detail_percent=100)
        self.assertNotIn('--fft-size',cmd);self.assertNotIn('--fft-only',cmd)
        self.assertEqual(cmd[cmd.index('--hold-radio-seconds')+1],'20')
        self.assertIn('--window-seconds',cmd)
