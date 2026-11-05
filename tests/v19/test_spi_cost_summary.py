import unittest
from tools.summarize_spi_costs_v19 import summarize


class CostSummaryTests(unittest.TestCase):
    def test_weighted_cost_excludes_unknown_and_cross_epoch_without_mixing_nodes(self):
        def group(n,prep,check,origin='same_epoch_profile'):
            return dict(observed_phase='playing',previous_batch='playing:rf+rf',previous_origin=origin,
                prepare=dict(count=n,total_us=n*prep,max_us=prep,zero_count=0),
                check=dict(count=n,total_us=n*check,max_us=check,zero_count=0))
        metrics=dict(spi_batch_timing=dict(groups=[group(1,100,50),group(3,200,100),group(2,999,999,'unknown')]),
            physical_batch_mix={'playing:rf+rf':7},node_budget_ticks=299968,
            radio_playing=dict(mean_send_margin=.1))
        result=summarize(metrics)
        self.assertEqual(result['stable_timing_batches'],4)
        self.assertEqual(result['timing_batches_observed'],6)
        self.assertEqual(result['prepare']['mean_us'],175)
        self.assertEqual(result['check']['mean_us'],87.5)
        self.assertAlmostEqual(result['partial_nominal_us_per_covered_batch'],659.3)
        self.assertAlmostEqual(result['service_mean_us_per_node'],1687.32)
