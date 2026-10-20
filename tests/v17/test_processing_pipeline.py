"""Offline ordering, lifecycle and GUI contracts for continuous DSP delivery."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from dataclasses import replace
import threading
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
import numpy as np
from PyQt6 import QtCore, QtWidgets
from monitor.v17.app import OutputWorker, SerialMonitorWindow
from monitor.v17.digital_filter import FilterConfig
from monitor.v17.numeric_batch import NumericBatch, SampleClock
from monitor.v17.processing import (BatchProcessor, ProcessingSettings,
    initialize_process_owner, process_owner_ready, process_owned_batch)
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_switch import Mode


def block(start=0,count=32,config=Configuration(),clock=None):
    indices=np.arange(start,start+count)
    period=config.dt_us*config.timestamp_hz/1e6
    raw=np.column_stack(((indices*period)%2**32,np.full(count,config.maximum//2),np.zeros(count),indices))
    batch=NumericBatch(raw,config.maximum,clock or SampleClock(config.timestamp_hz),config.channels)
    batch.acquisition=config
    return batch


class WorkerPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.worker=OutputWorker('offline',Mode.SPI,processing_settings=ProcessingSettings(
            filter=FilterConfig(source='CH1',mode='bypass')))

    def tearDown(self):
        self.worker.stop()
        if self.worker._processing_executor is not None:
            self.worker._processing_executor.shutdown(wait=True)

    def test_radio_demodulates_all_ch1_profiles_with_native_adc_precision(self):
        from monitor.v17.receiver.unoq_native import PROFILES
        profiles={(p['bits'],160000000//p['ticks']) for p in PROFILES if p['channels']==1}
        profiles.update(((8,1203007),(14,599250),(14,661157)))
        self.assertTrue({8,10,12,14}.issubset({bits for bits,_ in profiles}))
        for bits,rate in sorted(profiles):
            with self.subTest(bits=bits,rate=rate):
                config=Configuration(bits,rate);count=int(config.actual_rate*.08)
                t=np.arange(count)/config.actual_rate
                rf=1.65+.6*(1+.5*np.sin(2*np.pi*1000*t))*np.cos(2*np.pi*50000*t)
                raw=np.zeros((count,4),np.uint32)
                raw[:,0]=np.arange(count)*config.period;raw[:,3]=np.arange(count)
                raw[:,1]=np.rint(rf*config.maximum/3.3).astype(np.uint32)
                batch=NumericBatch(raw,config.maximum,SampleClock(config.timestamp_hz),1);batch.acquisition=config
                settings=ProcessingSettings(acquisition=config,radio_enabled=True,radio_frequency=50000,radio_gain=1,radio_offset=0)
                result=BatchProcessor().process(batch,settings).processing
                self.assertIsNone(result['radio_status'])
                audio=result['audio'][1200:]
                frequency=np.fft.rfftfreq(len(audio),1/settings.audio_rate)
                self.assertLess(abs(frequency[np.argmax(abs(np.fft.rfft(audio)))]-1000),30)

    def test_radio_output_timestamps_stay_on_rf_clock_through_level_changes(self):
        config=Configuration(8,1403508)
        processor=BatchProcessor()
        settings=ProcessingSettings(acquisition=config,radio_enabled=True,radio_frequency=50000)
        first=processor.process(block(start=30000,count=65536,config=config),settings).processing
        expected_start=30000*1e6/config.actual_rate
        self.assertAlmostEqual(first['audio_first_time_us'],expected_start)
        next_time=expected_start+len(first['audio'])*1e6/settings.audio_rate
        second=processor.process(block(start=95536,count=65536,config=config),replace(settings,generation=1,radio_gain=3)).processing
        self.assertAlmostEqual(second['audio_first_time_us'],next_time)

    def test_radio_out_of_band_transition_does_not_stop_rf(self):
        config=Configuration(14,599250)
        result=BatchProcessor().process(block(count=128,config=config),ProcessingSettings(
            acquisition=config,radio_enabled=True,radio_frequency=550000)).processing
        self.assertIsNone(result['audio'])
        self.assertIn('fuera',result['radio_status'])
        dual=Configuration(14,40000)
        result=BatchProcessor().process(block(config=dual),ProcessingSettings(acquisition=dual,radio_enabled=True)).processing
        self.assertIsNone(result['audio'])
        self.assertIn('fuera',result['radio_status'])

    def test_radio_gain_offset_scale_audio_without_changing_rf(self):
        config=Configuration(8,1403508)
        count=65536
        t=np.arange(count)/config.actual_rate
        codes=np.rint((1.65+.6*(1+.5*np.sin(2*np.pi*1000*t))*np.cos(2*np.pi*20000*t))*255/3.3).astype(np.uint32)
        raw=np.zeros((count,4),dtype=np.uint32)
        raw[:,0]=np.arange(count)*config.period;raw[:,1]=codes
        raw[:,3]=np.arange(count)
        def make_batch():
            batch=NumericBatch(raw.copy(),config.maximum,SampleClock(config.timestamp_hz),config.channels)
            batch.acquisition=config
            return batch
        settings=ProcessingSettings(acquisition=config,radio_enabled=True,radio_frequency=20000,radio_gain=1,radio_offset=0,
            filter=FilterConfig(source='RADIO',mode='bypass'))
        original=make_batch();scaled=make_batch()
        reference=BatchProcessor().process(original,settings).processing['audio']
        result=BatchProcessor().process(scaled,replace(settings,radio_gain=12,radio_offset=1.65))
        np.testing.assert_allclose(result.processing['audio'],reference*12+1.65)
        np.testing.assert_allclose(result.processing['audio_filter'],reference*12+1.65)
        np.testing.assert_array_equal(result.columns['CH1'],original.columns['CH1'])

    def test_level_change_preserves_continuous_dsp_but_generation_reset_rebuilds(self):
        config=Configuration(8,1403508)
        settings=ProcessingSettings(acquisition=config,radio_enabled=True,radio_frequency=20000,radio_gain=1,radio_offset=0)
        processor=BatchProcessor();reference=BatchProcessor()
        processor.process(block(count=65536,config=config),settings)
        reference.process(block(count=65536,config=config),settings)
        owner=processor.radio
        changed=replace(settings,generation=1,radio_gain=7,radio_offset=1.65)
        result=processor.process(block(start=65536,count=65536,config=config),changed)
        expected=reference.process(block(start=65536,count=65536,config=config),settings)
        self.assertIs(processor.radio,owner)
        np.testing.assert_allclose(result.processing['audio'],expected.processing['audio']*7+1.65)
        processor.process(block(start=131072,count=65536,config=config),replace(changed,generation=2,continuity_epoch=1))
        self.assertIsNot(processor.radio,owner)

    def test_process_backend_off_allocates_no_child_and_active_returns_only_dsp(self):
        worker=OutputWorker('offline',Mode.SPI,processing_backend='process',
            processing_settings=ProcessingSettings())
        delivered=[]
        worker.batch_ready.connect(delivered.append,QtCore.Qt.ConnectionType.DirectConnection)
        worker.publish_batch(block())
        self.assertIsNone(worker._processing_process)
        worker.batch_consumed()
        settings=ProcessingSettings(filter=FilterConfig(source='CH1',mode='bypass'))
        try:
            batch=block()
            original=batch.columns['CH1']
            result=worker._process_separately(batch,settings)
            self.assertIs(result,batch)
            self.assertIs(result.columns['CH1'],original)
            np.testing.assert_allclose(result.columns['FILTER'],original)
        finally:
            worker.stop()
            if worker._processing_process is not None:worker._processing_process.shutdown(wait=True)

    def test_startup_waits_for_gui_and_confirms_configuration_once(self):
        target=Configuration(8,1403508)
        for changed in (False,True):
            with self.subTest(changed=changed):
                worker=OutputWorker('offline',Mode.SPI,config=target,startup_gui_ack=True)
                events=[];pumps=[];published=[];errors=[]
                class Receiver:
                    def __init__(self,connection,collect,status,running):
                        self.collect=collect;self.config=Configuration() if changed else target
                        self.decoder=SimpleNamespace(numeric=False);self.wav_candidate=False
                    def configure(self,config):
                        different=self.config!=config;self.config=config
                        if different:self.on_configuration(config)
                        return different
                    def select(self,*args):pass
                    def pump(self):
                        pumps.append(1)
                        self.collect([(0,0,0,0)])
                        self.assert_not_published()
                        if len(pumps)==3:worker.confirm_startup(target.bits,target.rate)
                    def assert_not_published(self):
                        if published:raise AssertionError('Startup samples published before GUI acknowledgement')
                    def generator(self,*args):worker.stop()
                    def shutdown_output(self):pass
                    def close(self):pass
                worker.acquisition_confirmed.connect(lambda bits,rate:events.append((bits,rate)),QtCore.Qt.ConnectionType.DirectConnection)
                worker.batch_ready.connect(published.append,QtCore.Qt.ConnectionType.DirectConnection)
                worker.error_occurred.connect(errors.append,QtCore.Qt.ConnectionType.DirectConnection)
                connection=MagicMock();connection.__enter__.return_value=connection
                with patch('monitor.v17.app.Connection',return_value=connection),patch('monitor.v17.app.OutputReceiver',Receiver),patch('monitor.v17.bode_calibration.instrument_identity',return_value=None):
                    worker.run()
                self.assertEqual(events,[(target.bits,target.rate)])
                self.assertEqual(len(pumps),3)
                self.assertEqual(errors,[])
                self.assertEqual(worker.pending_batches,0)

    def test_generator_ack_follows_accumulated_samples_even_under_pressure(self):
        for active in (False,True):
            with self.subTest(dsp_active=active):
                settings=ProcessingSettings(filter=FilterConfig(source='CH1' if active else 'OFF',mode='bypass'))
                worker=OutputWorker('offline',Mode.SPI,processing_settings=settings)
                events=[];errors=[]
                class Receiver:
                    def __init__(self,connection,collect,status,running):
                        self.collect=collect;self.config=worker.config
                        self.decoder=SimpleNamespace(numeric=False);self.wav_candidate=False
                    def configure(self,config):return False
                    def select(self,*args):pass
                    def generator(self,*args):
                        self.collect([(0,10,20,0),(32,11,21,1)])
                        self.on_generator('new stimulus')
                        worker.stop()
                    def shutdown_output(self):pass
                    def close(self):pass
                def delivered(batch):events.append('samples');worker.batch_consumed(batch)
                worker.batch_ready.connect(delivered,QtCore.Qt.ConnectionType.DirectConnection)
                worker.generator_confirmed.connect(lambda _:events.append('ack'),QtCore.Qt.ConnectionType.DirectConnection)
                worker.error_occurred.connect(errors.append,QtCore.Qt.ConnectionType.DirectConnection)
                connection=MagicMock();connection.__enter__.return_value=connection
                with patch('monitor.v17.app.Connection',return_value=connection),patch('monitor.v17.app.OutputReceiver',Receiver),patch('monitor.v17.bode_calibration.instrument_identity',return_value=None),patch('monitor.v17.app.time.monotonic',return_value=10.),patch.object(worker,'delivery_pressure',return_value=4):
                    worker.run()
                self.assertEqual(errors,[])
                self.assertEqual(events,['samples','ack'])
                self.assertEqual(worker.pending_batches,0)

    def test_shutdown_failure_preserves_original_acquisition_error(self):
        worker=OutputWorker('offline',Mode.SPI)
        receiver=MagicMock();receiver.config=worker.config
        receiver.configure.return_value=False;receiver.wav_candidate=False
        receiver.generator.side_effect=RuntimeError('primary overload')
        receiver.shutdown_output.side_effect=RuntimeError('secondary boundary')
        errors=[]
        worker.error_occurred.connect(errors.append,QtCore.Qt.ConnectionType.DirectConnection)
        connection=MagicMock();connection.__enter__.return_value=connection
        with patch('monitor.v17.app.Connection',return_value=connection),patch('monitor.v17.app.OutputReceiver',return_value=receiver),patch('monitor.v17.bode_calibration.instrument_identity',return_value=None):
            worker.run()
        self.assertEqual(errors,['primary overload'])
        receiver.close.assert_called_once()

    def test_process_startup_keeps_missing_filter_aligned_with_rf(self):
        worker=OutputWorker('offline',Mode.SPI,processing_backend='process',
            processing_settings=ProcessingSettings(filter=FilterConfig(source='CH1')))
        ready=MagicMock();ready.done.return_value=False
        delivered=[]
        worker.batch_ready.connect(delivered.append,QtCore.Qt.ConnectionType.DirectConnection)
        with patch.object(worker,'_ensure_process',return_value=ready):worker.publish_batch(block())
        self.assertEqual(len(delivered),1)
        self.assertEqual(len(delivered[0].columns['FILTER']),32)
        self.assertTrue(np.isnan(delivered[0].columns['FILTER']).all())
        self.assertIsNone(worker._processing_executor)
        worker.batch_consumed();worker.stop()

    def test_gui_stall_coalesces_rf_without_gaps_or_unbounded_deliveries(self):
        config=Configuration(14,40000)
        worker=OutputWorker('offline',Mode.SPI,config=config)
        worker.pending_batches=4
        clock=[0.];delivered=[];errors=[]
        class Receiver:
            def __init__(self,connection,collect,*args):
                self.collect=collect;self.config=config;self.decoder=SimpleNamespace(numeric=False)
                self.wav_candidate=False;self.wav_codes=None;self.wav_pending=None
                self.last_generator_poll=0.;self.count=0
            def set_wav_levels(self,*args):pass
            def configure(self,*args):return False
            def select(self,*args):pass
            def generator(self,*args):pass
            def pump(self):
                clock[0]+=.03;self.count+=1
                if self.count==3:worker.pending_batches=0
                indices=np.arange((self.count-1)*1000,self.count*1000)
                self.collect(np.column_stack((indices*config.period,indices%config.maximum,np.zeros(1000),indices)))
                if self.count==4:worker.stop()
            def shutdown_output(self):pass
            def close(self):pass
        def consume(batch):delivered.append(batch);worker.batch_consumed()
        worker.batch_ready.connect(consume,QtCore.Qt.ConnectionType.DirectConnection)
        worker.error_occurred.connect(errors.append,QtCore.Qt.ConnectionType.DirectConnection)
        connection=MagicMock();connection.__enter__.return_value=connection
        with patch('monitor.v17.app.Connection',return_value=connection),patch('monitor.v17.app.OutputReceiver',Receiver),patch('monitor.v17.bode_calibration.instrument_identity',return_value=None),patch('monitor.v17.app.time.monotonic',side_effect=lambda:clock[0]):
            worker.run()
        self.assertEqual(errors,[])
        self.assertEqual([len(batch) for batch in delivered],[3000,1000])
        np.testing.assert_array_equal(np.concatenate([b.columns['Muestra'] for b in delivered]),np.arange(4000))
        self.assertGreaterEqual(worker.coalesced_flush_calls,2)
        self.assertEqual(worker.coalesced_rf_peak,3000)
        self.assertEqual(worker.pending_batches,0)

    def test_active_off_active_preserves_order_and_captures_settings(self):
        entered=threading.Event();release=threading.Event();results=[];threads=[]
        processor=self.worker._processor.process
        def delayed(batch,settings):
            threads.append(threading.get_ident())
            if int(batch.columns['Muestra'][0])==0:
                entered.set()
                if not release.wait(3):raise RuntimeError('Test release timeout')
            return processor(batch,settings)
        def received(batch):
            results.append((int(batch.columns['Muestra'][0]),batch.processing['generation'],'FILTER' in batch.columns))
            self.worker.batch_consumed()
        self.worker._processor.process=delayed
        self.worker.batch_ready.connect(received,QtCore.Qt.ConnectionType.DirectConnection)
        try:
            self.worker.publish_batch(block(0))
            self.assertTrue(entered.wait(3))
            self.worker.set_processing_settings(ProcessingSettings(generation=1))
            self.worker.publish_batch(block(32))
            self.worker.set_processing_settings(ProcessingSettings(generation=2,filter=FilterConfig(source='CH1',mode='bypass')))
            self.worker.publish_batch(block(64))
            self.assertEqual(results,[])
        finally:release.set()
        self.worker._processing_executor.shutdown(wait=True)
        self.assertEqual(results,[(0,0,True),(32,1,False),(64,2,True)])
        self.assertEqual(len(set(threads)),1)
        self.assertNotEqual(threads[0],threading.get_ident())
        self.assertEqual(self.worker.pending_batches,0)

    def test_configuration_ack_cannot_overtake_old_clock_batch(self):
        entered=threading.Event();release=threading.Event();events=[]
        processor=self.worker._processor.process
        def delayed(batch,settings):
            if int(batch.columns['Muestra'][0])==0:
                entered.set()
                if not release.wait(3):raise RuntimeError('Test release timeout')
            return processor(batch,settings)
        def received(batch):
            events.append(('batch',batch.acquisition.rate))
            self.worker.batch_consumed()
        self.worker._processor.process=delayed
        self.worker.batch_ready.connect(received,QtCore.Qt.ConnectionType.DirectConnection)
        self.worker.acquisition_confirmed.connect(lambda bits,rate:events.append(('ack',rate)),QtCore.Qt.ConnectionType.DirectConnection)
        try:
            self.worker.publish_batch(block(0))
            self.assertTrue(entered.wait(3))
            self.worker._emit_after_processing(self.worker.acquisition_confirmed,8,1403508)
            self.worker.publish_batch(block(32,config=Configuration(8,1403508)))
            self.assertEqual(events,[])
        finally:release.set()
        self.worker._processing_executor.shutdown(wait=True)
        self.assertEqual(events,[('batch',Configuration().rate),('ack',1403508),('batch',1403508)])

    def test_limit_covers_finished_dsp_until_gui_acknowledges(self):
        received=[];done=threading.Event()
        def delivered(batch):
            received.append(batch)
            if len(received)==8:done.set()
        self.worker.batch_ready.connect(delivered,QtCore.Qt.ConnectionType.DirectConnection)
        for i in range(8):self.worker.publish_batch(block(i*32))
        self.assertTrue(done.wait(3))
        self.assertEqual(self.worker.pending_batches,8)
        with self.assertRaisesRegex(RuntimeError,'8 lotes'):
            self.worker.publish_batch(block(256))
        for _ in received:self.worker.batch_consumed()
        self.assertEqual(self.worker.pending_batches,0)

    def test_error_stops_acquisition_and_releases_failed_slot(self):
        errors=[];done=threading.Event()
        def failed(batch,settings):raise ValueError('Discontinuidad de prueba')
        def error(text):errors.append(text);done.set()
        self.worker._processor.process=failed
        self.worker.error_occurred.connect(error,QtCore.Qt.ConnectionType.DirectConnection)
        self.worker.publish_batch(block())
        self.assertTrue(done.wait(3))
        self.worker._processing_executor.shutdown(wait=True)
        self.assertFalse(self.worker.running)
        self.assertEqual(self.worker.pending_batches,0)
        self.assertEqual(len(errors),1)
        self.assertIn('Discontinuidad de prueba',errors[0])

    def test_initial_off_has_no_dsp_or_executor(self):
        self.worker.set_processing_settings(ProcessingSettings())
        received=[]
        self.worker.batch_ready.connect(received.append,QtCore.Qt.ConnectionType.DirectConnection)
        with patch.object(self.worker._processor,'process',side_effect=AssertionError('OFF processed')):
            self.worker.publish_batch(block())
        self.assertIsNone(self.worker._processing_executor)
        self.assertEqual(len(received),1)
        self.assertNotIn('FILTER',received[0].columns)
        self.worker.batch_consumed()

    def test_finished_waits_for_dsp_callbacks_before_worker_deletion(self):
        entered=threading.Event();release=threading.Event();closing=threading.Event()
        finished=threading.Event();events=[]
        processor=self.worker._processor.process
        def delayed(batch,settings):
            entered.set()
            if not release.wait(3):raise RuntimeError('Test release timeout')
            return processor(batch,settings)
        def received(batch):
            events.append('batch');self.worker.batch_consumed()
        def complete():events.append('finished');finished.set()
        self.worker._processor.process=delayed
        self.worker.batch_ready.connect(received,QtCore.Qt.ConnectionType.DirectConnection)
        self.worker.finished.connect(complete,QtCore.Qt.ConnectionType.DirectConnection)
        self.worker.publish_batch(block())
        self.assertTrue(entered.wait(3))
        executor=self.worker._processing_executor
        shutdown=executor.shutdown
        def observe_shutdown(*args,**kwargs):
            closing.set();return shutdown(*args,**kwargs)
        self.worker.stop()
        thread=threading.Thread(target=self.worker.run)
        try:
            with (patch.object(executor,'shutdown',side_effect=observe_shutdown),
                  patch('monitor.v17.app.Connection',side_effect=AssertionError('Hardware access'))):
                thread.start()
                self.assertTrue(closing.wait(3))
                self.assertFalse(finished.is_set())
                release.set();thread.join(3)
        finally:
            release.set()
            if thread.ident is not None:thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(events,['batch','finished'])
        self.assertEqual(self.worker.pending_batches,0)


class ProcessorTests(unittest.TestCase):
    def test_process_owner_preserves_radio_continuity_and_generation_reset(self):
        config=Configuration(8,1403508)
        settings=ProcessingSettings(acquisition=config,radio_enabled=True,radio_frequency=20525)
        reference=BatchProcessor();clock=SampleClock(config.timestamp_hz)
        with ProcessPoolExecutor(max_workers=1,mp_context=multiprocessing.get_context('spawn'),
                initializer=initialize_process_owner) as pool:
            self.assertNotEqual(pool.submit(process_owner_ready).result(timeout=30),os.getpid())
            for start,generation in ((0,0),(28000,0),(0,1)):
                current=replace(settings,generation=generation,continuity_epoch=generation)
                batch=block(start,28000,config,clock if generation==0 else None)
                expected=reference.process(batch,current)
                actual=pool.submit(process_owned_batch,batch,current).result(timeout=30)
                np.testing.assert_allclose(actual.processing['audio'],expected.processing['audio'])
                self.assertEqual(actual.processing['generation'],generation)

    def test_source_and_radio_rate_changes_reset_only_owner_state(self):
        processor=BatchProcessor()
        settings=ProcessingSettings(filter=FilterConfig(source='CH1'))
        first=processor.process(block(0),settings)
        self.assertGreater(first.columns['FILTER'][-1],1)
        changed=replace(settings,generation=1,filter=FilterConfig(source='CH2'))
        second=processor.process(block(32),changed)
        np.testing.assert_allclose(second.columns['FILTER'],0,atol=1e-14)
        config=Configuration(8,1403508)
        for generation,rate in enumerate((20000,40000,48000),2):
            radio=ProcessingSettings(generation=generation,acquisition=config,
                radio_enabled=True,audio_rate=rate)
            processed=processor.process(block(3456*generation,3456,config),radio)
            self.assertEqual(processed.processing['radio_key'][2],rate)
            self.assertEqual(processor.radio.rate,rate)
            self.assertLess(len(processed.processing['audio']),130)
            self.assertIsNone(processed.processing['audio_filter'])

    def test_batch_acquisition_overrides_older_settings_clock(self):
        settings=ProcessingSettings(acquisition=Configuration(8,1403508),radio_enabled=True)
        batch=block(config=Configuration(8,40000))
        result=BatchProcessor().process(batch,settings).processing
        self.assertIsNone(result['audio'])
        self.assertIn('sintonía fuera',result['radio_status'])

    def test_off_resets_filter_and_generation_restarts_continuity(self):
        processor=BatchProcessor()
        settings=ProcessingSettings(filter=FilterConfig(source='CH1'))
        processor.process(block(0),settings)
        with self.assertRaisesRegex(ValueError,'Discontinuidad'):
            processor.process(block(64),settings)
        processor.process(block(64),replace(settings,generation=1,continuity_epoch=1))
        off=replace(settings,generation=2,filter=FilterConfig(source='OFF'))
        with patch.object(processor.rf_filter,'process',side_effect=AssertionError('OFF filtered')):
            result=processor.process(block(96),off)
        self.assertNotIn('FILTER',result.columns)


class ProcessingUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        with patch('monitor.v17.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()

    def tearDown(self):self.w.close()

    def test_off_default_never_processes_or_accumulates_filter_history(self):
        self.assertEqual(self.w.filter_source.currentText(),'OFF')
        with patch.object(self.w.digital_filter,'process',side_effect=AssertionError('OFF filtered')):
            self.w.handle_batch(block(0));self.w.handle_batch(block(32))
        self.assertEqual(len(self.w.series['FILTER']),0)
        self.assertEqual(len(self.w.sample_numbers),64)
        self.assertFalse(self.w.filter_order.isEnabled())

    def test_old_generation_keeps_raw_and_missing_filter_alignment(self):
        self.w.filter_source.setCurrentText('CH1')
        old=self.w._processing_settings()
        old_batch=BatchProcessor().process(block(0),old)
        self.w.filter_source.setCurrentText('CH2')
        current=self.w._processing_settings()
        self.assertGreater(current.generation,old.generation)
        self.w.handle_batch(old_batch)
        self.w.handle_batch(BatchProcessor().process(block(32),current))
        self.assertEqual(len(self.w.series['FILTER']),len(self.w.sample_numbers))
        self.assertTrue(np.isnan(self.w.series['FILTER'][:32]).all())
        np.testing.assert_allclose(self.w.series['FILTER'][32:],0,atol=1e-12)
        np.testing.assert_array_equal(self.w.series['Muestra'][:],np.arange(64))

    def test_off_filter_selected_for_trigger_or_fft_does_not_read_missing_history(self):
        self.w.handle_batch(block(0,256))
        self.w.graph_channel_actions['FILTER'].setChecked(True)
        self.w.trigger_source_combo.setCurrentText('FILTER')
        self.w.trigger_checkbox.setChecked(True)
        self.w.render_frame()
        self.w.trigger_checkbox.setChecked(False)
        self.w.meas_channel_combo.setCurrentText('FILTER')
        self.w.spectral.mode=1
        self.w._last_measurement_update=0
        self.w.render_frame()
        self.assertEqual(len(self.w.series['FILTER']),0)

    def test_stale_radio_cannot_repopulate_after_stop(self):
        self.w._acquisition_confirmed(8,1403508)
        self.w.radio_enabled.setChecked(True)
        settings=self.w._processing_settings()
        config=settings.acquisition
        batch=BatchProcessor().process(block(0,3456,config),settings)
        self.assertIsNotNone(batch.processing['audio'])
        self.w.radio_enabled.setChecked(False)
        self.w.handle_batch(batch)
        self.assertIsNone(self.w.radio_stream)
        self.assertEqual(len(self.w.series['FILTER']),0)
        self.assertEqual(self.w.sample_counter,3456)

    def test_processed_radio_uses_gui_timeline_without_repeating_dsp(self):
        from monitor.v17.radio_stream import RadioTimeline
        self.w._acquisition_confirmed(8,1403508)
        self.w.radio_enabled.setChecked(True)
        settings=self.w._processing_settings()
        processor=BatchProcessor()
        batch=processor.process(block(0,3456,settings.acquisition),settings)
        with (patch.object(self.w,'_process_radio',side_effect=AssertionError('GUI radio DSP')),
              patch.object(self.w.digital_filter,'process',side_effect=AssertionError('GUI filter DSP'))):
            self.w.handle_batch(batch)
        self.assertIsInstance(self.w.radio_stream,RadioTimeline)
        self.assertFalse(hasattr(self.w.radio_stream,'demod'))
        self.assertEqual(self.w.radio_stream.counter,len(batch.processing['audio']))
        np.testing.assert_array_equal(self.w.radio_stream.series['RADIO'][:],batch.processing['audio'])
        self.assertEqual(len(self.w.radio_stream.series['FILTER']),0)


if __name__=='__main__':unittest.main()
