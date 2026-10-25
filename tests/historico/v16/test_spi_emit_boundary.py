import unittest
from monitor.historico.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.historico.v16.receiver.unoq_usb import ProtocolError,MASK
from monitor.historico.v16.receiver.unoq_acquisition import Configuration
from diagnosticos.benchmark_latencia_host_v16 import adc_payload

class SpiBoundaryTests(unittest.TestCase):
    def receiver(self,index,timestamp):
        out=[];r=OutputReceiver(None,out.append);r.visible=True;r.config=Configuration(14,100000)
        r.next_index=index;r.timestamp=timestamp
        return r,out

    def test_verified_spi_matches_strict_checks_across_uint32_wrap(self):
        for index,start in ((0,100),(MASK-2,MASK-15)):
            records=[((start+i*10)&MASK,100,200,(index+i)&MASK) for i in range(8)]
            strict,a=self.receiver(index,(start-10)&MASK)
            fast,b=self.receiver(index,(start-10)&MASK)
            strict._emit(records);fast._emit(records,validated_spi=True)
            self.assertEqual(a,b)
            self.assertEqual((strict.next_index,strict.timestamp),(fast.next_index,fast.timestamp))

    def test_verified_spi_still_rejects_wrong_receiver_boundaries(self):
        r,_=self.receiver(5,90)
        for records in ([(100,1,2,6)],[(101,1,2,5)],[(100,1,2,5),(111,1,2,6)]):
            with self.assertRaises(ProtocolError):r._emit(records,validated_spi=True)

    def test_unverified_batch_keeps_interior_validation(self):
        r,_=self.receiver(0,None)
        with self.assertRaises(ProtocolError):
            r._emit([(0,1,2,0),(11,1,2,1),(20,1,2,2)])

    def test_wire_decoder_batches_retain_all_samples_and_boundary_evidence(self):
        r,out=self.receiver(0,None)
        r.decoder.feed(adc_payload(2))
        for kind,records in r.decoder.events:
            if kind=='samples':r._emit(records,validated_spi=True)
        flat=[row for batch in out for row in batch]
        self.assertEqual(len(flat),4096)
        self.assertEqual([row[3] for row in flat],list(range(4096)))
        self.assertEqual([row[0] for row in flat],[i*10 for i in range(4096)])
