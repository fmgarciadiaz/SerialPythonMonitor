import json,os,struct,tempfile,unittest,zlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import numpy as np
from monitor.v20.receiver.unoq_config_receiver import OutputReceiver as V20
from monitor.v19.receiver.unoq_config_receiver import OutputReceiver as V19
from monitor.v20.receiver.unoq_acquisition import Configuration
from monitor.v20.receiver.unoq_wav import chunk
from tools.relay_wire_metrics_v19 import observe_connection,ACK_LATENCY_ENV,PROFILE_ENV

class ObserverTests(unittest.TestCase):
    def test_actual_v20_hook_correlates_raw_and_decoded_ack_without_touching_v19(self):
        rid=0x80000001;p=bytearray(992);struct.pack_into('<4sHHII',p,0,b'SCP1',4,12,1,972)
        struct.pack_into('<II',p,16,rid,9);p[24]=2;struct.pack_into('<I',p,40,40000)
        struct.pack_into('<I',p,988,zlib.crc32(p[:988]));connection=SimpleNamespace(read=lambda:bytes(p),socket=Mock())
        old19=V19._process_decoder_events;called=[]
        def real_handler(receiver):called.append(receiver)
        receiver=SimpleNamespace(wav_inflight={rid:(10,13)},decoder=SimpleNamespace(events=[('wav',SimpleNamespace(request_id=rid))]))
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{ACK_LATENCY_ENV:'1',PROFILE_ENV:'[8,2000000]'}),patch.object(V20,'_process_decoder_events',real_handler):
            path=Path(temp)/'report.json'
            with observe_connection(connection,path,receiver_class=V20,configuration=Configuration):
                self.assertIs(V19._process_decoder_events,old19)
                with patch('tools.relay_wire_metrics_v19.time.monotonic',return_value=10):connection.socket.sendall(chunk(rid,9,0,np.zeros(480,dtype=np.uint16)))
                with patch('tools.relay_wire_metrics_v19.time.monotonic',return_value=10.025):connection.read()
                with patch('tools.relay_wire_metrics_v19.time.monotonic',return_value=10.030):V20._process_decoder_events(receiver)
            self.assertIs(V20._process_decoder_events,real_handler)
            report=json.loads(path.read_text());timing=report['raw_chunk_ack_latency']
            self.assertEqual(report['profile'][:3],[8,2000000,80])
            self.assertEqual((timing['matched'],timing['decoded']),(1,1))
            self.assertAlmostEqual(timing['raw_max_ms'],25);self.assertAlmostEqual(timing['decode_max_ms'],5)
            self.assertEqual(called,[receiver])
        self.assertIs(V19._process_decoder_events,old19)

    def test_v20_stage_capture_restores_hook_even_after_exception(self):
        from monitor.v20.receiver import unoq_config_receiver as core
        from tools.reader_stages_v20 import capture
        original=core._ChildStageTiming._observe
        with tempfile.TemporaryDirectory() as temp,patch.object(core,'_child_stage_timing_enabled',True):
            path=Path(temp)/'stages.json'
            with self.assertRaisesRegex(RuntimeError,'abort'):
                with capture(path):
                    tracker=core._ChildStageTiming();tracker._observe('decode',10,10.1,.005)
                    raise RuntimeError('abort')
            self.assertIs(core._ChildStageTiming._observe,original)
            self.assertEqual(json.loads(path.read_text())['slow'][0]['stage'],'decode')
