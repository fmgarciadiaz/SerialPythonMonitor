import unittest
from queue import Queue
from threading import Event
from monitor.v18.io.pcm_request_pump import PcmRequestPump


class PcmPumpTests(unittest.TestCase):
    def test_pcm_serviced_while_rf_dispatch_is_blocked_and_ack_untouched(self):
        rf=Queue();pcm=Queue(2);handled=Event();errors=[]
        ack=dict(type='signal',name='acquisition_confirmed')
        rf.put(dict(type='batch'));rf.put(ack)
        received=[]
        def dispatch(event):received.append(event);handled.set()
        pump=PcmRequestPump(pcm.get,dispatch,errors.append).start()
        try:
            request=dict(type='pcm_request',session=1,start=0,end=480)
            pcm.put(request)
            self.assertTrue(handled.wait(2))
            self.assertEqual(received,[request])
            self.assertEqual(rf.get()['type'],'batch');self.assertIs(rf.get(),ack)
            self.assertEqual(errors,[])
        finally:pump.close()
        self.assertFalse(pump.thread.is_alive())

    def test_control_event_on_pcm_channel_fails_without_dispatch(self):
        pcm=Queue();failed=Event();errors=[];received=[]
        def error(exc):errors.append(exc);failed.set()
        pump=PcmRequestPump(pcm.get,received.append,error).start()
        try:
            pcm.put(dict(type='signal'))
            self.assertTrue(failed.wait(2));self.assertEqual(received,[])
            self.assertIsInstance(errors[0],ValueError)
        finally:pump.close()

    def test_close_does_not_dispatch_future_requests(self):
        pcm=Queue();received=[]
        pump=PcmRequestPump(pcm.get,received.append,lambda exc:None).start()
        pump.close();pcm.put(dict(type='pcm_request'))
        self.assertFalse(pump.thread.is_alive());self.assertEqual(received,[])
