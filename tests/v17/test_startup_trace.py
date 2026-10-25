import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch
from PyQt6 import QtCore, QtWidgets

from monitor.v17.startup_trace import StartupTrace
from monitor.v17.app import OutputWorker, SerialMonitorWindow
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_switch import Mode


class StartupTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_opt_out_never_reads_clock_or_keeps_records(self):
        clock=Mock(side_effect=AssertionError('disabled clock read'))
        trace=StartupTrace(enabled=False,clock=clock)
        self.assertIsNone(trace.begin('connection_start',Configuration()))
        trace.record(1,'event')
        self.assertEqual(trace.snapshot(),[])
        clock.assert_not_called()

    def test_bounds_generations_once_and_snapshot_is_detached(self):
        now=[10.]
        trace=StartupTrace(enabled=True,clock=lambda:now[0])
        old=trace.begin('connection_start',Configuration())
        for _ in range(4):current=trace.begin('active_change',Configuration(8,1600000))
        trace.record(old,'stale')
        now[0]=12.
        trace.record(current,'first_publish',once=True)
        trace.record(current,'first_publish',once=True)
        for _ in range(200):trace.record(current,'extra')
        snapshot=trace.snapshot()
        self.assertEqual(len(snapshot),4)
        self.assertEqual(len(snapshot[-1]['events']),128)
        self.assertEqual([e['monotonic'] for e in snapshot[-1]['events'][:2]],[10.,12.])
        self.assertEqual(sum(e['event']=='first_publish' for e in snapshot[-1]['events']),1)
        snapshot[-1]['events'].clear()
        self.assertEqual(len(trace.snapshot()[-1]['events']),128)

    def test_receiver_trace_reports_live_half_second_preparation_and_noop(self):
        receiver=OutputReceiver(Mock(),Mock());receiver.mode=Mode.SPI
        now=[0.]
        trace=StartupTrace(enabled=True,clock=lambda:now[0])
        generation=trace.begin('active_change',Configuration(8,1600000))
        receiver.startup_trace=lambda event,**kw:trace.record(generation,event,**kw)
        applied=[];samples=receiver.on_samples
        def configure(config):
            applied.append(config.rate);receiver.config=config
            receiver.on_configuration(config)
            receiver.on_samples([config.rate])
            return True
        def pump():
            receiver.on_samples(['private']);now[0]+=.5
        receiver._configure_once=configure;receiver.pump=pump
        with patch('monitor.v17.receiver.unoq_config_receiver.time.monotonic',side_effect=lambda:now[0]):
            receiver.configure(Configuration(8,1600000))
            self.assertFalse(receiver.configure(Configuration(8,1600000)))
        self.assertEqual(applied,[40000,1428571,1600000])
        samples.assert_called_once_with([1600000])
        events={e['event']:e['monotonic'] for e in trace.snapshot()[0]['events']}
        self.assertEqual(events['settle_2s_end']-events['settle_2s_begin'],.5)
        begin=next(e for e in trace.snapshot()[0]['events'] if e['event']=='settle_2s_begin')
        self.assertEqual((begin['seconds'],begin['connected']),(.5,True))
        self.assertIn('target_applied',events)
        self.assertIn('configure_noop',events)

    def test_warmup_guard_requires_autoload_restart_spi_and_optimized(self):
        cases=[(True,True,Configuration(8,1600000),True),
               (True,False,Configuration(8,1600000),False),
               (False,True,Configuration(8,1600000),False),
               (True,True,Configuration(14,40000),False)]
        for autoload,restarted,config,expected in cases:
            with self.subTest(autoload=autoload,restarted=restarted,rate=config.rate):
                now=[0.];worker=OutputWorker('offline',Mode.SPI,config=config,autoload=autoload)
                worker.trace=StartupTrace(enabled=True,clock=lambda:now[0])
                connection=MagicMock();connection.__enter__.return_value=connection
                connection.scope_restarted=restarted
                class Receiver:
                    def __init__(self,*args):
                        self.config=Configuration();self.decoder=SimpleNamespace(numeric=False)
                        self.wav_candidate=False
                    def configure(self,active):
                        changed=self.config!=active;self.config=active
                        if changed:self.on_configuration(active)
                        return changed
                    def select(self,*args):pass
                    def pump(self):now[0]+=1
                    def generator(self,*args):worker.stop()
                    def shutdown_output(self):pass
                    def close(self):pass
                errors=[]
                worker.error_occurred.connect(errors.append,QtCore.Qt.ConnectionType.DirectConnection)
                with patch('monitor.v17.app.Connection',return_value=connection),patch('monitor.v17.app.connect_scope',return_value=connection),patch('monitor.v17.app.OutputReceiver',Receiver),patch('monitor.v17.bode_calibration.instrument_identity',return_value=None),patch('monitor.v17.app.time.monotonic',side_effect=lambda:now[0]):
                    worker.run()
                self.assertEqual(errors,[])
                events={e['event']:e['monotonic'] for e in worker.trace.snapshot()[0]['events']}
                self.assertEqual('warmup_5s_begin' in events,expected)
                if expected:self.assertEqual(events['warmup_5s_end']-events['warmup_5s_begin'],5.)

    def test_old_buffer_keeps_its_generation_across_active_change(self):
        now=[0.];initial=Configuration(14,40000);target=Configuration(8,1600000)
        worker=OutputWorker('offline',Mode.SPI,config=initial)
        worker.trace=StartupTrace(enabled=True,clock=lambda:now[0])
        delivered=[];errors=[]
        class Receiver:
            def __init__(self,connection,collect,*args):
                self.collect=collect;self.config=initial
                self.decoder=SimpleNamespace(numeric=False);self.wav_candidate=False
                self.wav_codes=None;self.wav_pending=None;self.last_generator_poll=0.
            def configure(self,config):
                if config==self.config:return False
                self.collect([(0,10,20,0)])
                self.config=config;self.on_configuration(config)
                self.collect([(0,10,0,0)])
                return True
            def select(self,*args):pass
            def set_wav_levels(self,*args):pass
            def generator(self,*args):
                self.collect([(0,10,20,0)])
                worker.request_output(Mode.SPI,None,target)
            def pump(self):
                now[0]+=.03;self.collect([(100,10,0,1)]);worker.stop()
            def shutdown_output(self):pass
            def close(self):pass
        def consume(batch):delivered.append(batch);worker.batch_consumed(batch)
        worker.batch_ready.connect(consume,QtCore.Qt.ConnectionType.DirectConnection)
        worker.error_occurred.connect(errors.append,QtCore.Qt.ConnectionType.DirectConnection)
        connection=MagicMock();connection.__enter__.return_value=connection
        with patch('monitor.v17.app.Connection',return_value=connection),patch('monitor.v17.app.OutputReceiver',Receiver),patch('monitor.v17.bode_calibration.instrument_identity',return_value=None),patch('monitor.v17.app.time.monotonic',side_effect=lambda:now[0]):
            worker.run()
        self.assertEqual(errors,[])
        self.assertEqual([(b.acquisition,b.startup_trace_generation) for b in delivered],[(initial,1),(target,2)])
        requests=worker.trace.snapshot()
        self.assertEqual([r['kind'] for r in requests],['connection_start','active_change'])
        self.assertTrue(all(any(e['event']=='first_batch_ready_signal' for e in r['events']) for r in requests))

    def test_gui_acceptance_rejects_retired_worker_and_mismatched_acquisition(self):
        config=Configuration();worker=OutputWorker('offline',Mode.SPI,config=config)
        worker.trace=StartupTrace(enabled=True,clock=lambda:0.)
        generation=worker.trace.begin('connection_start',config)
        owner=SimpleNamespace(serial_worker=None,applied_configuration=config,
            _from_worker=Mock(),_gui_slow_callbacks=[])
        batch=SimpleNamespace(acquisition=config,startup_trace_generation=generation)
        SerialMonitorWindow._deliver_worker_batch(owner,worker,batch)
        owner.serial_worker=worker;owner.handle_batch=Mock()
        batch.acquisition=Configuration(8,1600000)
        SerialMonitorWindow._deliver_worker_batch(owner,worker,batch)
        self.assertNotIn('first_gui_batch_accepted',[e['event'] for e in worker.trace.snapshot()[0]['events']])
        batch.acquisition=config
        SerialMonitorWindow._deliver_worker_batch(owner,worker,batch)
        self.assertIn('first_gui_batch_accepted',[e['event'] for e in worker.trace.snapshot()[0]['events']])
