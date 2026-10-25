from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from PyQt6 import QtCore
from diagnosticos.wav_visual_audit_v17 import WavVisualAudit


class WavVisualAuditTests(TestCase):
    def test_counts_only_playback_and_accumulates_replay_time(self):
        class Window(QtCore.QObject):
            def windowHandle(self):
                return SimpleNamespace(isExposed=lambda: True)
        window = Window()
        viewport = QtCore.QObject(window)
        fft = QtCore.QObject(window)
        window.plot_widget = SimpleNamespace(viewport=lambda: viewport)
        window.spectral = SimpleNamespace(widget=SimpleNamespace(viewport=lambda: fft))
        clock = [10.]
        with patch('diagnosticos.wav_visual_audit_v17.time.monotonic',side_effect=lambda:clock[0]):
            audit = WavVisualAudit(window)
            paint = QtCore.QEvent(QtCore.QEvent.Type.Paint)
            audit.eventFilter(viewport,paint)
            audit.sample_exposure()
            self.assertEqual(audit.counts['scope_paints'],0)
            audit.playing(True)
            for _ in range(10):
                clock[0] += .1
                audit.eventFilter(viewport,paint)
                audit.sample_exposure()
            audit.playing(False)
            snapshot = audit.snapshot()
            self.assertTrue(snapshot['visual_ok'])
            self.assertAlmostEqual(snapshot['seconds'],1.)
            clock[0] += 30
            audit.eventFilter(fft,paint)
            self.assertEqual(audit.snapshot()['fft_paints'],0)
            audit.playing(True)
            clock[0] += 1
            audit.eventFilter(fft,paint)
            audit.playing(False)
            self.assertAlmostEqual(audit.snapshot()['seconds'],2.)
            self.assertEqual(audit.snapshot()['fft_paints'],1)
