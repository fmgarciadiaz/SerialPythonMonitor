from contextlib import nullcontext
from pathlib import Path
import tempfile,unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from tools.process_resources_v20 import ProcessResources


def process(pid,created,cpu,rss):
    p=Mock(pid=pid);p.create_time.return_value=created;p.oneshot.side_effect=nullcontext
    p.cpu_times.return_value=SimpleNamespace(user=cpu,system=0.);p.memory_info.return_value=SimpleNamespace(rss=rss)
    return p

class ResourceTests(unittest.TestCase):
    def test_cpu_tree_totals_and_interval_subset_do_not_count_shared_rss_as_unique(self):
        root=process(10,1.,1.,100);child=process(11,2.,.5,70);root.children.return_value=[child]
        with tempfile.TemporaryDirectory() as temp,patch('tools.process_resources_v20.psutil.Process',return_value=root),patch('tools.process_resources_v20.time.monotonic',side_effect=[10.,10.001,11.,11.001]):
            observer=ProcessResources(10,Path(temp)/'r.jsonl');observer.sample()
            root.cpu_times.return_value=SimpleNamespace(user=1.4,system=0.)
            child.cpu_times.return_value=SimpleNamespace(user=1.1,system=0.)
            observer.sample();result=observer.summary(10.5,11.5)
            self.assertAlmostEqual(result['cpu_cores_median'],1.)
            self.assertEqual(result['rss_sum_peak_bytes'],170);self.assertEqual(result['samples'],1)
            self.assertIn('double-counts',result['scope'])
    def test_pid_reuse_gets_new_cpu_baseline_and_partial_samples_are_visible(self):
        import psutil
        root=process(10,1.,0.,100);old=process(11,2.,1.,70);root.children.return_value=[old]
        with tempfile.TemporaryDirectory() as temp,patch('tools.process_resources_v20.psutil.Process',return_value=root),patch('tools.process_resources_v20.time.monotonic',side_effect=[10.,10.001,11.,11.001,12.,12.001]):
            observer=ProcessResources(10,Path(temp)/'r.jsonl');observer.sample()
            replacement=process(11,3.,.2,50);root.children.return_value=[replacement];observer.sample()
            self.assertAlmostEqual(observer.rows[-1]['cpu_cores'],.2)
            root.children.side_effect=psutil.AccessDenied(10);observer.sample()
            self.assertEqual(observer.summary()['partial_samples'],1)
