import ctypes
import errno
import json
import unittest
from unittest.mock import patch

from monitor.v17.audio_qos import (
    AudioQoSError, assigned_audio_qos as audio_qos, audio_qos as override_audio_qos)


class FakePthread:
    """No test calls the real priority API."""

    def __init__(self, initial=(0x15, -3)):
        self.state = initial
        self.thread = 123
        self.set_calls = []
        self.get_results = []
        self.set_results = []
        self.ignore_sets = set()
        self.override_handle = 789
        self.override_end_result = 0
        self.override_calls = []

    def pthread_self(self):
        return self.thread

    def pthread_get_qos_class_np(self, thread, qos_class, relative):
        assert thread == self.thread
        result = self.get_results.pop(0) if self.get_results else 0
        ctypes.cast(qos_class, ctypes.POINTER(ctypes.c_uint))[0] = self.state[0]
        ctypes.cast(relative, ctypes.POINTER(ctypes.c_int))[0] = self.state[1]
        return result

    def pthread_set_qos_class_self_np(self, qos_class, relative):
        self.set_calls.append((qos_class, relative))
        result = self.set_results.pop(0) if self.set_results else 0
        if not result and len(self.set_calls) not in self.ignore_sets:
            self.state = (qos_class, relative)
        return result

    def pthread_override_qos_class_start_np(self, thread, qos_class, relative):
        self.override_calls.append(('start', thread, qos_class, relative))
        return self.override_handle

    def pthread_override_qos_class_end_np(self, handle):
        self.override_calls.append(('end', handle))
        return self.override_end_result


class AudioQoSTests(unittest.TestCase):
    def setUp(self):
        self.library = FakePthread()
        self.platform = patch('monitor.v17.audio_qos.sys.platform', 'darwin')
        self.loader = patch('monitor.v17.audio_qos._load_library', return_value=self.library)
        self.platform.start()
        self.load = self.loader.start()
        self.addCleanup(self.platform.stop)
        self.addCleanup(self.loader.stop)

    def test_current_thread_request_and_exact_relative_priority_restoration(self):
        with audio_qos('user_interactive') as report:
            self.assertEqual(self.library.state, (0x21, 0))
            self.assertEqual(report['before']['relative_priority'], -3)
            self.assertEqual(report['applied'], report['requested'])
            self.assertFalse(report['restored'])
        self.assertEqual(self.library.set_calls, [(0x21, 0), (0x15, -3)])
        self.assertTrue(report['restored'])
        self.assertEqual(report['after'], report['before'])
        json.dumps(report)

    def test_body_exception_still_restores(self):
        with self.assertRaisesRegex(ValueError, 'experiment'):
            with audio_qos('user_initiated', -2) as report:
                raise ValueError('experiment')
        self.assertTrue(report['restored'])
        self.assertEqual(self.library.state, (0x15, -3))

    def test_unspecified_or_unknown_initial_state_rejected_without_mutation(self):
        for state in ((0, 0), (1234, 0), (0x15, -16)):
            with self.subTest(state=state):
                self.library.state = state
                with self.assertRaisesRegex(AudioQoSError, 'cannot be restored'):
                    with audio_qos('user_interactive'):
                        self.fail('must not enter')
                self.assertEqual(self.library.set_calls, [])

    def test_unsupported_platform_does_not_load_api(self):
        with patch('monitor.v17.audio_qos.sys.platform', 'linux'):
            with self.assertRaisesRegex(AudioQoSError, 'requires macOS'):
                with audio_qos('default'):
                    self.fail('must not enter')
        self.load.assert_not_called()

    def test_invalid_request_does_not_load_api(self):
        for name, relative in [('realtime', 0), ('default', 1), ('default', -16),
                               ('default', .5), ('default', True)]:
            with self.subTest(name=name, relative=relative):
                with self.assertRaises(AudioQoSError):
                    with audio_qos(name, relative):
                        self.fail('must not enter')
        self.load.assert_not_called()

    def test_missing_api_is_explicit(self):
        self.load.side_effect = AttributeError('missing symbol')
        with self.assertRaisesRegex(AudioQoSError, 'API unavailable'):
            with audio_qos('default'):
                self.fail('must not enter')

    def test_initial_get_failure_does_not_set(self):
        self.library.get_results = [errno.EINVAL]
        with self.assertRaisesRegex(AudioQoSError, 'pthread_get') as caught:
            with audio_qos('default'):
                self.fail('must not enter')
        self.assertEqual(self.library.set_calls, [])
        self.assertFalse(caught.exception.report['restored'])

    def test_failed_set_never_claims_applied(self):
        self.library.set_results = [errno.EPERM]
        with self.assertRaisesRegex(AudioQoSError, 'apply') as caught:
            with audio_qos('user_interactive'):
                self.fail('must not enter')
        self.assertIsNone(caught.exception.report['applied'])
        self.assertFalse(caught.exception.report['restored'])
        self.assertEqual(self.library.state, (0x15, -3))

    def test_apply_verification_mismatch_restores_before_raising(self):
        self.library.ignore_sets = {1}
        with self.assertRaisesRegex(AudioQoSError, 'Applied QoS verification') as caught:
            with audio_qos('user_interactive'):
                self.fail('must not enter')
        self.assertTrue(caught.exception.report['restored'])
        self.assertEqual(len(self.library.set_calls), 2)

    def test_apply_get_failure_also_restores(self):
        self.library.get_results = [0, errno.EINVAL, 0]
        with self.assertRaisesRegex(AudioQoSError, 'pthread_get') as caught:
            with audio_qos('user_interactive'):
                self.fail('must not enter')
        self.assertTrue(caught.exception.report['restored'])

    def test_restore_failure_is_explicit_and_keeps_body_exception(self):
        self.library.set_results = [0, errno.EPERM]
        with self.assertRaisesRegex(AudioQoSError, 'restore') as caught:
            with audio_qos('user_interactive'):
                raise ValueError('experiment failed')
        self.assertIsInstance(caught.exception.__context__, ValueError)
        self.assertFalse(caught.exception.report['restored'])

    def test_restore_verification_mismatch_is_not_success(self):
        self.library.ignore_sets = {2}
        with self.assertRaisesRegex(AudioQoSError, 'restoration verification') as caught:
            with audio_qos('user_interactive'):
                pass
        self.assertFalse(caught.exception.report['restored'])
        self.assertEqual(caught.exception.report['after']['qos_class'], 0x21)

    def test_restore_on_other_thread_is_rejected_without_setting_that_thread(self):
        with self.assertRaisesRegex(AudioQoSError, 'original thread'):
            with audio_qos('user_interactive'):
                self.library.thread = 456
        self.assertEqual(self.library.set_calls, [(0x21, 0)])

    def test_override_supports_unspecified_without_changing_base(self):
        self.library.state = (0, 0)
        with override_audio_qos('user_interactive') as report:
            self.assertTrue(report['override_started'])
            self.assertFalse(report['override_ended'])
            self.assertEqual(report['during'], report['before'])
            self.assertEqual(report['during']['name'], 'unspecified')
        self.assertEqual(self.library.set_calls, [])
        self.assertEqual(self.library.override_calls,
                         [('start', 123, 0x21, 0), ('end', 789)])
        self.assertTrue(report['restored'])
        self.assertTrue(report['base_unchanged'])
        self.assertTrue(report['override_ended'])
        json.dumps(report)

    def test_override_body_failure_still_ends(self):
        with self.assertRaisesRegex(ValueError, 'experiment'):
            with override_audio_qos('user_initiated', -2) as report:
                raise ValueError('experiment')
        self.assertTrue(report['restored'])
        self.assertEqual(self.library.override_calls[0], ('start', 123, 0x19, -2))

    def test_null_override_start_never_claims_started_or_calls_end(self):
        self.library.override_handle = None
        with self.assertRaisesRegex(AudioQoSError, 'NULL') as caught:
            with override_audio_qos('user_interactive'):
                self.fail('must not enter')
        self.assertFalse(caught.exception.report['override_started'])
        self.assertEqual(len(self.library.override_calls), 1)

    def test_override_end_failure_is_explicit(self):
        self.library.override_end_result = errno.EINVAL
        with self.assertRaisesRegex(AudioQoSError, 'end_np') as caught:
            with override_audio_qos('user_interactive'):
                raise ValueError('experiment failed')
        self.assertFalse(caught.exception.report['restored'])
        self.assertFalse(caught.exception.report['override_ended'])
        self.assertIsInstance(caught.exception.__context__, ValueError)

    def test_override_read_failure_after_start_still_ends(self):
        self.library.get_results = [0, errno.EINVAL, 0]
        with self.assertRaisesRegex(AudioQoSError, 'pthread_get') as caught:
            with override_audio_qos('user_interactive'):
                self.fail('must not enter')
        self.assertTrue(caught.exception.report['override_ended'])
        self.assertTrue(caught.exception.report['restored'])

    def test_override_unexpected_base_change_is_explicit(self):
        with self.assertRaisesRegex(AudioQoSError, 'Base QoS changed') as caught:
            with override_audio_qos('user_interactive'):
                self.library.state = (0x19, 0)
        self.assertTrue(caught.exception.report['override_ended'])
        self.assertFalse(caught.exception.report['base_unchanged'])
        self.assertFalse(caught.exception.report['restored'])

    def test_override_rejects_unsupported_platform_and_invalid_requests(self):
        for name, priority in [('bad', 0), ('default', 1), ('default', -16)]:
            with self.assertRaises(AudioQoSError):
                with override_audio_qos(name, priority):
                    self.fail('must not enter')
        with patch('monitor.v17.audio_qos.sys.platform', 'linux'):
            with self.assertRaisesRegex(AudioQoSError, 'requires macOS'):
                with override_audio_qos('default'):
                    self.fail('must not enter')
        self.load.assert_not_called()


if __name__ == '__main__':
    unittest.main()
