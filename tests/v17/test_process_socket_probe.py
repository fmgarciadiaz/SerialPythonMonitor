import socket,time,unittest,tempfile
from pathlib import Path
from monitor.v17.socket_probe import ProcessSocketProbe
import numpy as np

class ProcessSocketProbeTests(unittest.TestCase):
    def test_observes_readiness_without_consuming_or_closing_original(self):
        left,right=socket.socketpair();probe=ProcessSocketProbe(left,capacity=64,interval=.002)
        try:
            probe.start();right.sendall(b'preserved');time.sleep(.035)
            self.assertEqual(left.recv(9),b'preserved')
            time.sleep(.15);probe.close()
            self.assertGreater(probe.count,0)
            self.assertTrue(np.any(probe.samples[:probe.count,2]==1))
            right.sendall(b'open');self.assertEqual(left.recv(4),b'open')
            with tempfile.TemporaryDirectory() as folder:
                report=probe.save(Path(folder)/'probe.npz')
                self.assertEqual(report['mode'],'process');self.assertIsNone(report['error'])
        finally:
            if probe._process.is_alive():probe.close()
            left.close();right.close()
