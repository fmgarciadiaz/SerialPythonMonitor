"""Offline registration, pinned binary and child invocation contracts."""
import json
import unittest
from experimentos.adc8_relay_accept_v17.qualify_radio import EXPECTED_RELAY,STAGES,validate_relay_digest,certified_sources,private_profiles,CERTIFIED
from experimentos.adc8_relay_accept_v17.radio_child import trial_arguments,outcome
from monitor.v17.receiver import unoq_native


class QualificationPreparationTests(unittest.TestCase):
    def test_pinned_relay_and_private_entry_without_public_changes(self):
        validate_relay_digest(EXPECTED_RELAY)
        with self.assertRaises(ValueError):validate_relay_digest('0'*64)
        before=repr(unoq_native.PROFILES)
        profiles=private_profiles(unoq_native.PROFILES,json.loads((CERTIFIED/'candidate_profiles.json').read_text()))
        candidate=next(p for p in profiles if p['ticks']==98)
        self.assertEqual((candidate['node_pairs'],candidate['queue_slots'],candidate['warmup_rate']),(3456,8,1428571))
        self.assertTrue(candidate['integrity_only'] and candidate['optimized_transport'])
        self.assertEqual(repr(unoq_native.PROFILES),before)
        self.assertEqual([seconds for _,seconds in STAGES],[60,120,120,120])
        self.assertTrue(certified_sources()[0]['candidate_identity']['firmware_sha256'].startswith('cc46'))

    def test_child_arguments_and_visual_and_headroom_do_not_replace_integrity(self):
        for seconds in (60,120):
            args=trial_arguments(seconds)
            for flag in ('--analysis-audit','--refill-ring','--defer-diagnostics'):self.assertIn(flag,args)
            self.assertEqual(args[args.index('--rate')+1],'1632653')
            self.assertEqual(args[args.index('--audio-rate')+1],'40000')
            self.assertNotIn('--filter-input',args)
        with self.assertRaises(ValueError):trial_arguments(600)
        report=dict(ok=True,restored=True,errors=[],audio_source_type='RadioDacSource',
            audio_transport={'chunk_burst':8},paint_audit={'exposed_fraction':.5,'fft_fps':10},
            adc_queue_peak=4,joint_send_statistics={'mean_margin':.15,'minimum_slack_ticks':10})
        result=outcome(report)
        self.assertTrue(result['audio_integrity_ok'])
        self.assertFalse(result['visual_ok']);self.assertFalse(result['headroom_ok']);self.assertFalse(result['ok'])
        report['restored']=False
        self.assertFalse(outcome(report)['audio_integrity_ok'])
