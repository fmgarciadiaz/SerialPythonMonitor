import socket,time,unittest
import numpy as np
from monitor.historico.v16.socket_probe import SocketProbe
from diagnosticos.analizar_socket_synth_v16 import analyze

class SocketProbeTests(unittest.TestCase):
    def test_probe_observes_without_consuming_and_closes(self):
        a,b=socket.socketpair();probe=SocketProbe(a,1000)
        try:
            probe.start();b.sendall(b'payload')
            deadline=time.monotonic()+1
            while time.monotonic()<deadline and not np.any(probe.samples[:probe.count,2]>0):time.sleep(.001)
            probe.close()
            self.assertIsNone(probe.error)
            self.assertTrue(np.any(probe.samples[:probe.count,2]>0))
            self.assertEqual(a.recv(7),b'payload')
            self.assertFalse(probe._thread.is_alive())
        finally:
            probe.close();a.close();b.close()
    def test_ready_bound_and_probe_wakeup_are_distinct(self):
        result=analyze([('read',1.,1.08,None,.0001)],np.array([[1.01,.001,0],[1.02,.01,1],[1.07,.05,1]]))
        row=result['long_reads'][0]
        self.assertAlmostEqual(row['first_ready_to_read_end_ms'],60)
        self.assertAlmostEqual(row['max_probe_wake_gap_ms'],50)
        self.assertEqual(row['probe_samples'],3)

if __name__=='__main__':unittest.main()
