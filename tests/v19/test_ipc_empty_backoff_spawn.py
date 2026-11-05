"""Exercise PCM, RF credits and cancellation in a real spawned candidate owner."""
import time
import unittest
import numpy as np

from monitor.v19.io.receiver_process import ReceiverProcess
from monitor.v19.receiver.unoq_acquisition import Configuration
from tests.v19.io.test_receiver_process import FakeConnection, PcmChannelReceiver


class BackoffConnection(FakeConnection):
    def __enter__(self):
        from tools.ipc_empty_backoff_v19 import empty_backoff
        self.scope=empty_backoff(500)
        self.scope.__enter__()
        return self

    def __exit__(self,*args):
        return self.scope.__exit__(*args)


class SpawnBackoffTests(unittest.TestCase):
    def test_pcm_delivery_rf_credit_and_cancelled_close(self):
        owner=ReceiverProcess('fake',0,Configuration(),connection_factory=BackoffConnection,
            receiver_factory=PcmChannelReceiver).start()
        try:
            owner.submit('wav',opcode=1,codes=dict(kind='live',session=1,length=100,rate=20000),rate=20000)
            request=owner.receive_pcm_request(timeout=5)
            self.assertEqual((request['start'],request['end']),(0,3))
            owner.submit('pcm',session=1,offset=0,codes=np.array([11,22,33],dtype=np.uint16))
            deadline=time.monotonic()+5
            pcm=False;rf=False
            while time.monotonic()<deadline and not (pcm and rf):
                for event in owner.poll():
                    if event['type']=='batch':
                        rf=True;owner.release(event['id'])
                    if event.get('name')=='status_changed' and event.get('args')==('PCM:11,22,33',):
                        pcm=True
                time.sleep(.002)
            self.assertTrue(pcm and rf)
        finally:
            code=owner.close(timeout=5)
        self.assertEqual(code,0)
        self.assertTrue(owner.poll_terminal()['shutdown_confirmed'])
