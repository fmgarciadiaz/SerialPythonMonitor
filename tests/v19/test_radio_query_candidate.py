import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from monitor.v19.receiver.unoq_config_receiver import OutputReceiver
from monitor.v19.receiver.unoq_usb import ProtocolError
from monitor.v19.receiver.unoq_wav import State
from tools.radio_query_candidate_v19 import refresh_query_after_chunk_ack


class QueryCandidateTests(unittest.TestCase):
    def test_burst_restores_inherited_attribute_after_exception(self):
        class Source:
            radio_audio=True;chunk_burst=8
        r=self.receiver();source=r.wav_codes=Source()
        r.on_wav=Mock(side_effect=RuntimeError('callback'))
        with self.assertRaises(RuntimeError):
            with refresh_query_after_chunk_ack(burst_limit=2):r._process_decoder_events()
        self.assertNotIn('chunk_burst',vars(source))
        self.assertEqual(source.chunk_burst,8)

    def test_private_burst_only_changes_radio40k_limit(self):
        for radio,rate,expected in ((True,40000,2),(False,40000,8),(True,20000,8)):
            with self.subTest(radio=radio,rate=rate):
                r=self.receiver(rate=rate);r.wav_rate=rate
                r.wav_codes.radio_audio=radio;r.wav_codes.chunk_burst=8
                r.wav_codes.chunk_interval=.006;r.wav_codes.target_blocks=30
                with refresh_query_after_chunk_ack(burst_limit=2):
                    r._process_decoder_events()
                    self.assertEqual(r.wav_codes.chunk_burst,expected)
                self.assertEqual(r.wav_codes.chunk_burst,8)
                self.assertEqual(r.wav_codes.chunk_interval,.006)
                self.assertEqual(r.wav_codes.target_blocks,30)

    def receiver(self,**overrides):
        r=OutputReceiver(SimpleNamespace(socket=Mock()),lambda rows:None)
        r.wav_codes=SimpleNamespace(radio_audio=True,poll_interval=.04)
        r.wav_started=True;r.wav_rate=40000;r.wav_session=9;r.wav_poll_at=0
        r.wav_inflight={77:(1,13)};r.wav_pending=(77,1)
        r.on_wav=Mock();r.service_wav=Mock()
        s=SimpleNamespace(request_id=77,session=9,rate=40000,reason=0,state=State.PLAYING)
        for key,value in overrides.items():setattr(s,key,value)
        r.decoder=SimpleNamespace(events=[('wav',s)])
        return r

    def test_valid_chunk_ack_renews_before_refill_and_restores_callback(self):
        r=self.receiver();callback=r.on_wav
        r.service_wav.side_effect=lambda:self.assertEqual(r.wav_poll_at,10.04)
        original=OutputReceiver._process_decoder_events
        with refresh_query_after_chunk_ack(),patch('tools.radio_query_candidate_v19.time.monotonic',return_value=10):
            r._process_decoder_events()
        self.assertEqual(r.wav_inflight,{})
        self.assertIs(r.on_wav,callback)
        self.assertIs(OutputReceiver._process_decoder_events,original)

    def test_unknown_invalid_terminal_and_other_sources_do_not_renew(self):
        for changes in ({'request_id':78},{'reason':1},{'state':State.UNDERRUN},
                        {'state':State.DONE},{'state':State.FAULT}):
            with self.subTest(changes=changes),refresh_query_after_chunk_ack():
                r=self.receiver(**changes);r._process_decoder_events()
                self.assertEqual(r.wav_poll_at,0)
        for field,value in (('session',10),('rate',20000)):
            with self.subTest(field=field),refresh_query_after_chunk_ack():
                r=self.receiver(**{field:value})
                with self.assertRaises(ProtocolError):r._process_decoder_events()
                self.assertEqual(r.wav_poll_at,0)
        for field,value in (('wav_started',False),('wav_rate',20000),('wav_codes',SimpleNamespace(radio_audio=False))):
            with self.subTest(field=field),refresh_query_after_chunk_ack():
                r=self.receiver(rate=20000 if field=='wav_rate' else 40000)
                setattr(r,field,value);r._process_decoder_events()
                self.assertEqual(r.wav_poll_at,0)

    def test_query_ack_and_other_pending_chunks_keep_original_semantics(self):
        with refresh_query_after_chunk_ack():
            r=self.receiver();r.wav_inflight[77]=(1,11)
            r._process_decoder_events();self.assertEqual(r.wav_poll_at,0)
            r=self.receiver();r.wav_inflight[78]=(2,13)
            r._process_decoder_events()
            self.assertEqual(r.wav_inflight,{78:(2,13)})
            self.assertEqual(r.wav_pending,(78,2))

    def test_sham_preserves_deadline_and_callback(self):
        r=self.receiver();callback=r.on_wav
        with refresh_query_after_chunk_ack(enabled=False):r._process_decoder_events()
        self.assertEqual(r.wav_poll_at,0)
        self.assertIs(r.on_wav,callback)
        callback.assert_called_once()

    def test_exception_restores_callback_and_method(self):
        r=self.receiver();r.on_wav=Mock(side_effect=RuntimeError('callback'))
        callback=r.on_wav;original=OutputReceiver._process_decoder_events
        with self.assertRaisesRegex(RuntimeError,'callback'):
            with refresh_query_after_chunk_ack():r._process_decoder_events()
        self.assertIs(r.on_wav,callback)
        self.assertIs(OutputReceiver._process_decoder_events,original)

    def test_two_acks_keep_reservations_until_each_confirmation(self):
        r=self.receiver();second=SimpleNamespace(**vars(r.decoder.events[0][1]))
        second.request_id=78;r.wav_inflight[78]=(2,13)
        r.decoder.events.append(('wav',second))
        observed=[];r.service_wav.side_effect=lambda:observed.append(set(r.wav_inflight))
        with refresh_query_after_chunk_ack():r._process_decoder_events()
        self.assertEqual(observed,[{78},set()])

    def test_missing_ack_timeout_stays_active(self):
        r=self.receiver();r.decoder.events=[]
        with refresh_query_after_chunk_ack():r._process_decoder_events()
        self.assertEqual(r.wav_poll_at,0)
        r.service_wav=OutputReceiver.service_wav.__get__(r)
        with patch('monitor.v19.receiver.unoq_config_receiver.time.monotonic',return_value=5):r.service_wav()
        self.assertIsNone(r.wav_codes)
        self.assertIsNone(r.wav_pending)

    def test_full_queue_queries_after_last_ack_deadline_without_invented_credit(self):
        class Source:
            live=True;radio_audio=True;poll_interval=.04
            target_blocks=30;maximum_blocks=30
            def __len__(self):return 100000
        r=self.receiver();r.wav_codes=Source()
        r.decoder.events[0][1].free_blocks=0
        r.decoder.events[0][1].queue_slots=30
        r.decoder.events[0][1].accepted=14400
        with refresh_query_after_chunk_ack(),patch('tools.radio_query_candidate_v19.time.monotonic',return_value=10):
            r._process_decoder_events()
        r.service_wav=OutputReceiver.service_wav.__get__(r)
        with patch('monitor.v19.receiver.unoq_config_receiver.time.monotonic',return_value=10.039):
            r.service_wav()
        r.connection.socket.sendall.assert_not_called()
        with patch('monitor.v19.receiver.unoq_config_receiver.time.monotonic',return_value=10.041):
            r.service_wav()
        packet=r.connection.socket.sendall.call_args.args[0]
        self.assertEqual(packet[20],0) # QUERY, without manufacturing free slots.
        self.assertEqual(r.wav_status.free_blocks,0)
