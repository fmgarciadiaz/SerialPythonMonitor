import tempfile
from types import SimpleNamespace
import unittest
from monitor.v18.io.receiver_lifecycle import ReceiverLifecycle
from monitor.v18.receiver.unoq_acquisition import Configuration
from monitor.v18.receiver.unoq_generator import GeneratorConfig
from monitor.v18.receiver.unoq_switch import Mode, Phase
from monitor.v18.receiver.unoq_wav import State

IDENTITY=dict(board_serial='local-fixture', app='scope-v17-main-1', firmware_sha256='a'*64, relay_sha256='b'*64)

class Receiver:
    def __init__(self, state=State.IDLE, phase=Phase.APPLIED):
        self.decoder=SimpleNamespace(config=Configuration(),mode=Mode.SPI)
        self.wav_status=SimpleNamespace(state=state)
        self.wav_pending=None
        self.phase=phase
        self.calls=[]
    def wav_request(self, op=0):self.calls.append(('wav',op))
    def generator(self, config=None):
        self.calls.append(('generator',config))
        return SimpleNamespace(phase=self.phase,active=GeneratorConfig(enabled=0),running=False)

class LifecycleTests(unittest.TestCase):
    def test_foreign_audio_refused_without_stop_or_configuration(self):
        for state in (State.BUFFERING, State.PLAYING):
            receiver=Receiver(state)
            with tempfile.TemporaryDirectory() as folder:
                lifecycle=ReceiverLifecycle(receiver,IDENTITY,folder)
                with self.assertRaises(ValueError):lifecycle.capture()
                self.assertFalse(lifecycle.restore()['hardware_restored'])
                self.assertEqual(receiver.calls,[('wav',0),('generator',None)])
                self.assertIsNone(lifecycle.path)
    def test_rejected_query_cannot_become_baseline(self):
        receiver=Receiver(phase=Phase.REJECTED)
        with tempfile.TemporaryDirectory() as folder:
            lifecycle=ReceiverLifecycle(receiver,IDENTITY,folder)
            with self.assertRaisesRegex(RuntimeError,'rechazada'):lifecycle.capture()
            self.assertIsNone(lifecycle.snapshot)

if __name__ == '__main__':unittest.main()

class InitialTransportTests(unittest.TestCase):
    def test_waits_for_transport_evidence_before_accepting_baseline(self):
        receiver=Receiver()
        receiver.decoder.mode=None
        pumps=[]
        def pump():
            pumps.append(True)
            receiver.decoder.mode=Mode.SPI
        receiver.pump=pump
        with tempfile.TemporaryDirectory() as folder:
            lifecycle=ReceiverLifecycle(receiver,IDENTITY,folder)
            lifecycle.capture()
            self.assertEqual(len(pumps),1)
            self.assertIsNotNone(lifecycle.snapshot)

class RestorationDurationTests(unittest.TestCase):
    def test_interactive_and_campaign_hold_keep_exact_state_checks(self):
        from unittest.mock import patch
        for duration in (.2,10):
            with self.subTest(duration=duration),tempfile.TemporaryDirectory() as folder:
                receiver=Receiver();receiver.decoder.status={'dropped':0,'fatal':0}
                receiver.on_samples=lambda records:None
                receiver.on_generator=lambda reply:None
                receiver.on_configuration=lambda config:None
                receiver.on_wav=lambda status:None
                elapsed=[0.]
                def pump():
                    elapsed[0]+=.1
                    receiver.on_samples(range(round(receiver.decoder.config.actual_rate*.1)))
                receiver.pump=pump
                receiver.reset_wav_output=lambda:None
                receiver.select=lambda mode:None
                receiver.configure=lambda config:None
                lifecycle=ReceiverLifecycle(receiver,IDENTITY,folder);lifecycle.capture()
                with patch('monitor.v18.io.receiver_lifecycle.time.monotonic',side_effect=lambda:elapsed[0]):
                    report=lifecycle.restore(duration)
                self.assertTrue(report['hardware_restored'],report)
                self.assertGreaterEqual(report['recovery']['seconds'],duration)
                self.assertLess(report['recovery']['seconds'],duration+.21)
