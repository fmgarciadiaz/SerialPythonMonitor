import unittest
from types import SimpleNamespace
import numpy as np
from monitor.v18.flow_limits import FlowLimitExceeded
from monitor.v18.radio_delivery_budget import DeliveryBudget
from monitor.v18.receiver.unoq_acquisition import Configuration
from monitor.v18.processing import ProcessingSettings


class FlowLimitsTests(unittest.TestCase):
    def setUp(self):
        self.config=Configuration(10,40000)
        self.settings=ProcessingSettings()
    def batch(self,n):
        return SimpleNamespace(columns={'CH1':np.zeros(n)},acquisition=self.config)
    def test_exact_sample_boundary_and_rejected_batch_preserve_reservations(self):
        budget=DeliveryBudget();budget.max_samples=10
        first=self.batch(10);budget.reserve(first,self.settings,self.config)
        before=budget.snapshot()
        with self.assertRaises(FlowLimitExceeded) as caught:
            budget.reserve(self.batch(1),self.settings,self.config)
        error=caught.exception
        self.assertIsInstance(error,RuntimeError)
        self.assertEqual(error.details['exceeded'],['samples'])
        self.assertEqual(error.details['projected']['samples'],11)
        self.assertEqual(error.details['context']['actual_rate'],40000)
        self.assertEqual(budget.snapshot(),before)
        budget.release(first)
        self.assertEqual(budget.samples,0)
        self.assertEqual(budget.peaks()['samples'],10)
    def test_each_original_limit_is_reported_independently(self):
        for name in ('max_seconds','max_bytes','max_batches'):
            with self.subTest(limit=name):
                budget=DeliveryBudget();setattr(budget,name,0)
                with self.assertRaises(FlowLimitExceeded) as caught:
                    budget.reserve(self.batch(1),self.settings,self.config)
                self.assertEqual(caught.exception.details['exceeded'],[name.removeprefix('max_')])
                self.assertEqual(budget.snapshot(),dict(samples=0,seconds=0.,bytes=0,batches=0))
    def test_multiple_limits_and_time_tolerance(self):
        budget=DeliveryBudget();budget.max_samples=0;budget.max_seconds=0.;budget.max_batches=0
        with self.assertRaises(FlowLimitExceeded) as caught:budget.reserve(self.batch(1),self.settings,self.config)
        self.assertEqual(set(caught.exception.details['exceeded']),{'samples','seconds','batches'})
        budget=DeliveryBudget();budget.max_seconds=1/self.config.actual_rate-5e-10
        budget.reserve(self.batch(1),self.settings,self.config)
        self.assertEqual(budget.samples,1)
    def test_worker_failure_snapshot_keeps_machine_readable_limit(self):
        from monitor.v18.app import OutputWorker
        from monitor.v18.receiver.unoq_switch import Mode
        worker=OutputWorker('test',Mode.SPI,config=self.config,processing_settings=self.settings)
        worker.delivery_budget.max_samples=0
        with self.assertRaises(FlowLimitExceeded) as caught:worker.publish_batch(self.batch(1))
        worker._capture_delivery_failure(caught.exception)
        snapshot=worker.delivery_failure_snapshot
        self.assertEqual(snapshot['limit_details']['exceeded'],['samples'])
        self.assertEqual(snapshot['delivery_peaks']['samples'],0)
        self.assertEqual(worker.pending_batches,0)
