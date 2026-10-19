import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from monitor.v17.radio_output import RadioDacSource
from monitor.v17.radio_output_panel import record_stop
class RadioStopDiagnosticsTests(unittest.TestCase):
 def test_fault_retains_source_and_negotiated_dac_state_before_close(self):
  source=RadioDacSource();source.error='audio atrasado'
  source.observe_status(SimpleNamespace(played=480,accepted=960))
  owner=SimpleNamespace(applied_configuration=SimpleNamespace(bits=8,rate=1600000))
  status=SimpleNamespace(state=4,reason=0,played=480,accepted=960,free_blocks=29,queue_slots=30)
  with tempfile.TemporaryDirectory() as folder:
   fake=Path(folder)/'monitor/v17/radio_output_panel.py'
   with patch('monitor.v17.radio_output_panel.__file__',str(fake)):
    record_stop(owner,source,'faltó audio',status);source.close()
   rows=(Path(folder)/'diagnosticos/resultados_v17/radio_a0_stops.jsonl').read_text().splitlines()
   record=json.loads(rows[0]);self.assertEqual(record['reason'],'faltó audio')
   self.assertEqual(record['dac']['queue_slots'],30)
   self.assertEqual(record['source']['error'],'audio atrasado')
   self.assertFalse(record['source']['closed']);self.assertEqual(record['source']['played'],480)
 def test_log_failure_does_not_prevent_stop(self):
  owner=SimpleNamespace(applied_configuration=SimpleNamespace(bits=8,rate=1600000))
  with patch('pathlib.Path.open',side_effect=OSError('disk unavailable')),patch('monitor.v17.radio_output_panel.logging.getLogger') as logger:
   record_stop(owner,RadioDacSource(),'Stop solicitado')
   logger.return_value.exception.assert_called_once()
if __name__=='__main__':unittest.main()
