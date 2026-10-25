"""Offline contracts for same-binary ADC8 A/B; never accesses the Q."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from experimentos.fs_max_all_bits_v17.adc8_ab import EXP,private_profiles,certified_sources,argument_parser
from experimentos.fs_max_all_bits_v17.adc8_radio_fft import UniqueNodeStatistics
from monitor.v17.receiver import unoq_native
from monitor.v17.receiver.unoq_acquisition import Configuration


class ADC8ABTests(unittest.TestCase):
    def test_radio_statistics_deduplicate_target_nodes_and_keep_epoch_changes(self):
        stats=UniqueNodeStatistics(1600000)
        base=dict(rate=1600000,epoch=4,produced=10,send_ticks=100,queue_peak=2,copy_ticks=30,slack_ticks=90)
        stats.observe(base);stats.observe(dict(base,queue_peak=8,send_ticks=999))
        stats.observe(dict(base,rate=1428571,produced=11,queue_peak=8))
        stats.observe(dict(base,epoch=5,send_ticks=200,queue_peak=3,copy_ticks=40,slack_ticks=80))
        stats.observe(dict(base,epoch=5,produced=11,send_ticks=300,queue_peak=5,copy_ticks=50,slack_ticks=70))
        result=stats.snapshot(100,3456)
        self.assertEqual(result['unique_observations'],3)
        self.assertEqual(result['sum_send_ticks'],600)
        self.assertEqual(result['queue_peak'],8)
        self.assertEqual(result['maximum_send_ticks'],999)
        self.assertEqual(result['minimum_slack_ticks'],70)
        self.assertAlmostEqual(result['mean_send_margin'],1-200/345600)

    def test_effective_profiles_share_entry_without_mutating_certified_inputs(self):
        self.assertEqual(argument_parser().parse_args([]).rates,[1600000,1632653])
        args=argument_parser().parse_args(['--radio-fft','--rates','1632653'])
        self.assertTrue(args.radio_fft);self.assertEqual(args.rates,[1632653])
        public=deepcopy(unoq_native.PROFILES)
        candidates=json.loads((EXP/'candidate_profiles.json').read_text())
        old_public,old_candidates=deepcopy(public),deepcopy(candidates)
        profiles=private_profiles(public,candidates)
        self.assertEqual(public,old_public);self.assertEqual(candidates,old_candidates)
        for profile in profiles:
            self.assertEqual({key:profile[key] for key in ('bits','channels','node_pairs','queue_slots','optimized_transport','integrity_only','warmup_rate')},
                dict(bits=8,channels=1,node_pairs=3456,queue_slots=8,optimized_transport=True,integrity_only=True,warmup_rate=1428571))
        with patch.object(unoq_native,'PROFILES',profiles+public):
            configs=[Configuration(8,160000000//p['ticks']) for p in profiles]
            self.assertEqual([config.rate for config in configs],[1600000,1632653])
            self.assertEqual([config.node_pairs for config in configs],[3456,3456])
        bad=deepcopy(candidates);next(p for p in bad if p['bits']==8)['queue_slots']=4
        with self.assertRaises(ValueError):private_profiles(public,bad)

    def test_candidate_headers_assign_both_rates_same_transport_and_queue(self):
        source='''#include "high_rate_profile.h"
#include "cpu_profile.h"
int main(){for(unsigned t: {98U,100U,112U}) {
 if(!scope_spi40(8,1,t,3456)||!scope_high_rate(8,1,t,3456)||
    scope_queue_capacity(8,1,t,3456)!=8||!scope_cpu_profile(8,1,t,3456))return 1;
}return 0;}'''
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);(path/'check.cpp').write_text('#include <initializer_list>\n'+source)
            subprocess.run(['c++','-std=c++17','-I',str(EXP/'relay'),str(path/'check.cpp'),'-o',str(path/'check')],check=True)
            subprocess.run([str(path/'check')],check=True)
        summary,_,_,_=certified_sources()
        self.assertTrue(summary['candidate_identity']['firmware_sha256'].startswith('cc46'))
