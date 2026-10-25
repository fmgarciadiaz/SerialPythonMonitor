import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from monitor.historico.v16.process_control import stop_process_tree

@unittest.skipUnless(os.name=='posix','POSIX process groups')
class ProcessControlTests(unittest.TestCase):
    def test_watchdog_stops_child_that_ignores_term(self):
        with tempfile.TemporaryDirectory() as folder:
            heartbeat=Path(folder)/'heartbeat'
            child="import signal,time,sys; signal.signal(signal.SIGTERM,signal.SIG_IGN); f=open(sys.argv[1],'a',buffering=1)\nwhile True: f.write('x\\n'); time.sleep(.02)"
            parent="import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',sys.argv[1],sys.argv[2]]); time.sleep(60)"
            process=subprocess.Popen([sys.executable,'-c',parent,child,str(heartbeat)],start_new_session=True)
            try:
                deadline=time.monotonic()+10
                while not heartbeat.exists() and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue(heartbeat.exists())
                stop_process_tree(process)
                self.assertIsNotNone(process.poll())
                time.sleep(.1);size=heartbeat.stat().st_size
                time.sleep(.1);self.assertEqual(size,heartbeat.stat().st_size)
            finally:stop_process_tree(process)
