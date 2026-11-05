"""Bridge the validated private ACK behavior to the production inline handler."""
import unittest
from contextlib import nullcontext
from unittest.mock import patch
from types import SimpleNamespace
from tests.v19 import test_radio_query_candidate as query_cases
from tools.radio_query_candidate_v19 import refresh_query_after_chunk_ack
from monitor.v19.receiver.unoq_config_receiver import OutputReceiver
from monitor.v19.receiver.unoq_wav import State


class InlineQueryTests(unittest.TestCase):
    def receiver(self,**changes):return query_cases.QueryCandidateTests().receiver(**changes)
    def run_arm(self,private,changes,mutate=lambda r:None,duplicate=False):
        r=self.receiver(**changes);mutate(r)
        if duplicate:r.decoder.events*=2
        calls=[]
        r.service_wav.side_effect=lambda:calls.append((r.wav_poll_at,dict(r.wav_inflight),r.wav_pending))
        error=None
        try:
            with refresh_query_after_chunk_ack() if private else nullcontext():
                with patch('monitor.v19.receiver.unoq_config_receiver.time.monotonic',return_value=10):
                    r._process_decoder_events()
        except Exception as exc:error=type(exc)
        return (r.wav_poll_at,r.wav_inflight,r.wav_pending,r.on_wav.call_count,calls,error,r.wav_codes is None)
    def test_inline_matches_private_for_valid_duplicate_invalid_and_other_ack_states(self):
        cases=[({},lambda r:None),({'request_id':78},lambda r:None),({'session':12},lambda r:None),
               ({'rate':20000},lambda r:None),({'reason':1},lambda r:None)]
        cases += [({'state':state},lambda r:None) for state in (State.IDLE,State.BUFFERING,State.DONE,State.UNDERRUN,State.FAULT)]
        cases += [({},lambda r:setattr(r,'wav_started',False)),
                  ({},lambda r:setattr(r,'wav_codes',SimpleNamespace(radio_audio=False))),
                  ({},lambda r:r.wav_inflight.update({77:(1,11)})),
                  ({},lambda r:r.wav_inflight.update({78:(2,13)}))]
        for changes,mutate in cases:
            for duplicate in (False,True):
                with self.subTest(changes=changes,duplicate=duplicate):
                    self.assertEqual(self.run_arm(True,changes,mutate,duplicate),self.run_arm(False,changes,mutate,duplicate))
    def test_valid_ack_renews_before_callback_and_refill_without_changing_reservations(self):
        r=self.receiver();r.wav_inflight[78]=(2,13)
        r.on_wav.side_effect=lambda s:self.assertEqual(r.wav_poll_at,10.04)
        with patch('monitor.v19.receiver.unoq_config_receiver.time.monotonic',return_value=10):r._process_decoder_events()
        self.assertEqual(r.wav_inflight,{78:(2,13)})
        self.assertEqual(r.wav_pending,(78,2));r.service_wav.assert_called_once()
        self.assertTrue(OutputReceiver._radio_chunk_ack_refresh)
    def test_callback_exception_and_private_context_do_not_disable_inline(self):
        def callback(r):r.on_wav.side_effect=RuntimeError('callback')
        self.assertEqual(self.run_arm(True,{},callback),self.run_arm(False,{},callback))
        self.assertTrue(OutputReceiver._radio_chunk_ack_refresh)
    def test_poll_interval_clamp_and_other_rates(self):
        for interval,expected in ((.001,.004),(.04,.04),(.5,.1)):
            r=self.receiver();r.wav_codes.poll_interval=interval
            with patch('monitor.v19.receiver.unoq_config_receiver.time.monotonic',return_value=10):r._process_decoder_events()
            self.assertEqual(r.wav_poll_at,10+expected)
        r=self.receiver(rate=20000);r.wav_rate=20000;r._process_decoder_events()
        self.assertEqual(r.wav_poll_at,0)
    def test_missing_ack_timeout_and_query_after_full_queue_remain_active(self):
        case=query_cases.QueryCandidateTests()
        # Run the same deadline/credit checks directly against inline, no wrapper.
        with patch('tests.v19.test_radio_query_candidate.refresh_query_after_chunk_ack',side_effect=lambda *a,**kw:nullcontext()):
            case.test_missing_ack_timeout_stays_active()
            case.test_full_queue_queries_after_last_ack_deadline_without_invented_credit()

if __name__=='__main__':unittest.main()
