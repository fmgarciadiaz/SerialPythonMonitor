import multiprocessing as mp
import queue
import unittest
import numpy as np
from monitor.historico.v16.adc_ipc import SharedAdcRing


def write_batches(ring, count):
    import time
    for i in range(count):
        data=np.full((1+i%7,4),i,dtype=np.uint32)
        deadline=time.monotonic()+5
        while True:
            try:
                ring.put_nowait(data)
                break
            except queue.Full:
                if time.monotonic()>deadline:raise TimeoutError('reader stalled')
                time.sleep(.001)


class SharedAdcRingTests(unittest.TestCase):
    def test_full_empty_wrap_and_reader_retention(self):
        ring=SharedAdcRing(mp.get_context('spawn'),slots=2,rows=3)
        with self.assertRaises(queue.Empty):ring.get_nowait()
        a=np.full((3,4),0xffffffff,dtype=np.uint32)
        ring.put_nowait(a);ring.put_nowait(a[:1])
        with self.assertRaises(queue.Full):ring.put_nowait(a)
        first=ring.get_nowait()
        ring.put_nowait(np.zeros((2,4),dtype=np.uint32))
        np.testing.assert_array_equal(first,a)
        np.testing.assert_array_equal(ring.get_nowait(),a[:1])
        self.assertEqual(ring.get_nowait().shape,(2,4))
        with self.assertRaises(queue.Empty):ring.get_nowait()

    def test_invalid_batch_does_not_consume_capacity(self):
        ring=SharedAdcRing(mp.get_context('spawn'),slots=1,rows=2)
        for data in (np.zeros((3,4),np.uint32),np.zeros((2,4)),np.zeros((0,4),np.uint32),np.zeros((2,3),np.uint32)):
            with self.assertRaises(ValueError):ring.put_nowait(data)
        ring.put_nowait(np.zeros((2,4),np.uint32))
        self.assertEqual(ring.get(timeout=.1).shape,(2,4))

    def test_spawn_transfer_preserves_fifo_after_many_wraps(self):
        context=mp.get_context('spawn');ring=SharedAdcRing(context,slots=3,rows=7)
        process=context.Process(target=write_batches,args=(ring,100))
        process.start()
        try:
            for i in range(100):
                data=ring.get(timeout=10)
                np.testing.assert_array_equal(data,np.full((1+i%7,4),i,dtype=np.uint32))
            process.join(10);self.assertEqual(process.exitcode,0)
        finally:
            if process.is_alive():process.terminate();process.join()
            ring.close()


if __name__=='__main__':unittest.main()
