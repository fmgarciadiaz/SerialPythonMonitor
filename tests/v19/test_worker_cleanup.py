import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, Future, CancelledError, TimeoutError
import time
import unittest
from monitor.v19.worker_cleanup import ComputationExecutor,wait_result,close_process_pool,close_thread_pool


def stuck_worker():
    while True:time.sleep(.1)


class WorkerCleanupTests(unittest.TestCase):
    def test_healthy_pool_manager_reaps_children_without_parallel_join(self):
        for _ in range(4):
            pool=ProcessPoolExecutor(1,mp_context=mp.get_context('spawn'))
            self.assertEqual(pool.submit(sum,(1,2,3)).result(timeout=3),6)
            children=tuple(pool._processes.values())
            self.assertEqual(close_process_pool(pool),0)
            self.assertTrue(all(child.exitcode==0 for child in children))

    def test_stalled_computation_cannot_block_interpreter_exit(self):
        import subprocess,sys
        code='''
from threading import Event
from monitor.v19.worker_cleanup import ComputationExecutor
entered=Event();blocked=Event()
def work():
    entered.set();blocked.wait()
executor=ComputationExecutor();executor.submit(work)
assert entered.wait(1)
executor.shutdown(wait=False,cancel_futures=True)
print('exit without waiting for native task',flush=True)
'''
        result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=3)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('exit without waiting',result.stdout)

    def test_ordered_execution_and_pending_cancellation(self):
        from threading import Event
        entered=Event();release=Event();order=[];executor=ComputationExecutor()
        def first():entered.set();release.wait(2);order.append(1);return 7
        first_future=executor.submit(first);self.assertTrue(entered.wait(1))
        second=executor.submit(lambda:order.append(2))
        executor.shutdown(wait=False,cancel_futures=True)
        self.assertTrue(second.cancelled())
        with self.assertRaises(RuntimeError):executor.submit(lambda:None)
        release.set();self.assertEqual(first_future.result(timeout=1),7)
        close_thread_pool(executor)
        self.assertEqual(order,[1])
    def test_unresponsive_computation_child_is_reaped_within_deadline(self):
        pool=ProcessPoolExecutor(1,mp_context=mp.get_context('spawn'))
        future=pool.submit(stuck_worker)
        deadline=time.monotonic()+5
        while not future.running() and time.monotonic()<deadline:time.sleep(.01)
        processes=tuple(pool._processes.values())
        began=time.monotonic()
        self.assertEqual(close_process_pool(pool,timeout=.1),1)
        self.assertLess(time.monotonic()-began,2)
        self.assertTrue(all(not child.is_alive() for child in processes))
    def test_cancel_and_timeout_release_thread_waiter(self):
        with self.assertRaises(CancelledError):wait_result(Future(),lambda:False)
        with self.assertRaises(TimeoutError):wait_result(Future(),lambda:True,timeout=.02)
        future=Future();future.set_exception(TimeoutError('task timeout'))
        with self.assertRaisesRegex(TimeoutError,'task timeout'):wait_result(future,lambda:True)
