from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from experimentos.radio_ipc_compact_v17.coalesce_probe import install
from experimentos.radio_ipc_compact_v17.test_sample_coalescer import records


class Receiver:
    def __init__(self):
        self.log=[];self.on_samples=lambda rows:self.log.append(('samples',int(rows[0][3]),len(rows)))
        self.wav_codes=SimpleNamespace(radio_audio=True)
        self.config=SimpleNamespace(bits=8,rate=1600000)
        self.visible=True;self.mode='SPI';self.decoder=SimpleNamespace(events=[])
        self.validated=0
    def _emit(self,rows,*,validated_spi=False):
        self.validated+=len(rows)
        if self.visible:self.on_samples(rows)
    def _process_decoder_events(self):
        for kind,value in self.decoder.events:
            if kind=='samples':self._emit(value,validated_spi=True)
            else:self.log.append((kind,))
    def pump(self):self._process_decoder_events()
    def configure(self,*args):self.log.append(('configure',))
    def generator(self,*args):self.log.append(('generator',))
    def wav_request(self,*args):self.log.append(('wav_request',))
    def shutdown_output(self):self.log.append(('shutdown',))
    def close(self):self.log.append(('close',))
    def _switch(self,*args):self.log.append(('switch',))


class AdapterTests(unittest.TestCase):
    def test_validation_still_runs_per_frame_and_control_order_is_exact(self):
        with ExitStack() as stack:
            registry=[];install(stack,Receiver,registry);r=Receiver()
            r._emit(records(0,4),validated_spi=True)
            self.assertEqual(r.validated,4);self.assertEqual(r.log,[])
            r.decoder.events=[('samples',records(4,4)),('configuration',None),('samples',records(8,4))]
            r._process_decoder_events()
            self.assertEqual(r.log,[('samples',0,4),('samples',4,4),('configuration',),('samples',8,4)])
            self.assertEqual(r.validated,12)

    def test_shutdown_flushes_and_patch_scope_restores_original_method(self):
        original=Receiver._emit
        with ExitStack() as stack:
            registry=[];install(stack,Receiver,registry);r=Receiver()
            r._emit(records(0,4),validated_spi=True);r.close()
            self.assertEqual(r.log,[('samples',0,4),('close',)])
            self.assertEqual(registry[0].count,0)
        self.assertIs(Receiver._emit,original)

    def test_unsupported_profile_bypasses_grouping(self):
        with ExitStack() as stack:
            install(stack,Receiver,[]);r=Receiver();r.config=SimpleNamespace(bits=10,rate=1250000)
            r._emit(records(0,4),validated_spi=True)
            self.assertEqual(r.log,[('samples',0,4)])

    def test_callback_reference_restored_on_emission_failure(self):
        with ExitStack() as stack:
            install(stack,Receiver,[]);r=Receiver()
            def fail(rows):raise RuntimeError('delivery')
            r.on_samples=fail
            with self.assertRaises(RuntimeError):r._emit(records(0,16000),validated_spi=True)
            self.assertIs(r.on_samples,fail)

    def test_real_receiver_still_rejects_rf_gap_before_delivery(self):
        from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
        from monitor.v17.receiver.unoq_acquisition import Configuration
        from monitor.v17.receiver.unoq_switch import Mode
        from monitor.v17.receiver.unoq_usb import ProtocolError
        with ExitStack() as stack:
            registry=[];install(stack,OutputReceiver,registry)
            output=[]
            r=OutputReceiver(SimpleNamespace(socket=None),output.append)
            r.config=Configuration(8,1600000);r.mode=Mode.SPI;r.visible=True
            r.next_index=0
            r.wav_codes=SimpleNamespace(radio_audio=True)
            r._emit(records(0,8),validated_spi=True)
            with self.assertRaises(ProtocolError):r._emit(records(9,8),validated_spi=True)
            self.assertEqual(output,[])
            registry[0].flush()
            self.assertEqual(sum(map(len,output)),8)


if __name__=='__main__':unittest.main()
