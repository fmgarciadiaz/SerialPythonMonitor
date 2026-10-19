import unittest
from types import SimpleNamespace
import numpy as np
from monitor.v17.radio_delivery_budget import DeliveryBudget
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.processing import ProcessingSettings

class BudgetTests(unittest.TestCase):
 def test_clock_changes_count_time_not_batch_number(self):
  b=DeliveryBudget();settings=ProcessingSettings()
  for rate in (40000,1250000):
   c=Configuration(10,rate)
   batch=SimpleNamespace(columns={'CH1':np.zeros(int(c.actual_rate*.4))})
   b.reserve(batch,settings,c)
  self.assertAlmostEqual(b.seconds,.8,places=3)
  with self.assertRaises(RuntimeError):b.reserve(SimpleNamespace(columns={'CH1':np.zeros(20000)}),settings,Configuration(10,40000))
  self.assertEqual(len(b.entries),2)
 def test_byte_limit_and_exact_release(self):
  b=DeliveryBudget();b.max_bytes=1000;c=Configuration(10,40000);s=ProcessingSettings()
  first=SimpleNamespace(columns={'CH1':np.zeros(10)});second=SimpleNamespace(columns={'CH1':np.zeros(10)})
  b.reserve(first,s,c);b.reserve(second,s,c)
  with self.assertRaises(RuntimeError):b.reserve(SimpleNamespace(columns={'CH1':np.zeros(20)}),s,c)
  b.release(second);self.assertIs(b.entries[0][0],first)
  before=b.bytes;b.release(second);self.assertEqual(b.bytes,before)
  b.release(first);self.assertEqual((b.bytes,b.samples,len(b.entries)),(0,0,0))
 def test_worker_sync_failure_releases_all_reservations(self):
  from monitor.v17.app import OutputWorker
  from monitor.v17.receiver.unoq_switch import Mode
  from unittest.mock import Mock
  c=Configuration(10,1250000)
  w=OutputWorker('test',Mode.SPI,config=c,processing_settings=ProcessingSettings(acquisition=c,radio_enabled=True))
  w._dispatch_reserved_batch=Mock(side_effect=RuntimeError('injected'))
  batch=SimpleNamespace(columns={'CH1':np.zeros(100)},acquisition=c)
  with self.assertRaisesRegex(RuntimeError,'injected'):w.publish_batch(batch)
  self.assertEqual((w.pending_batches,w.pending_dsp,w.delivery_budget.bytes),(0,0,0))
 def test_worker_radio_backlog_exceeds_old_count_but_not_time_budget(self):
  from monitor.v17.app import OutputWorker
  from monitor.v17.receiver.unoq_switch import Mode
  from unittest.mock import Mock
  c=Configuration(10,40000)
  w=OutputWorker('test',Mode.SPI,config=c,processing_settings=ProcessingSettings(acquisition=c,radio_enabled=True))
  w._dispatch_reserved_batch=Mock()
  batches=[]
  for _ in range(10):
   batch=SimpleNamespace(columns={'CH1':np.zeros(2000)},acquisition=c)
   w.publish_batch(batch);batches.append(batch)
  self.assertEqual(w.pending_batches,10)
  self.assertEqual(w.delivery_pressure(),0)
  from dataclasses import replace
  w.set_processing_settings(replace(w.processing_settings,radio_enabled=False))
  transition=SimpleNamespace(columns={'CH1':np.zeros(2000)},acquisition=c)
  w.publish_batch(transition);batches.append(transition)
  with self.assertRaises(RuntimeError):w.publish_batch(SimpleNamespace(columns={'CH1':np.zeros(24000)},acquisition=c))
  for batch in batches:w.batch_consumed(batch)
  self.assertEqual((w.pending_batches,w.delivery_budget.samples,w.delivery_budget.bytes),(0,0,0))
