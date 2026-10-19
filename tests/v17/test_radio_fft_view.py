import unittest
from unittest.mock import patch

from PyQt6 import QtWidgets


class RadioFftTests(unittest.TestCase):
    def test_rf_overlay_tuning_scan_log_and_exit(self):
        from monitor.v17.app import SerialMonitorWindow
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v17.app.usb_devices', return_value=[]):
            window = SerialMonitorWindow()
        try:
            window._acquisition_confirmed(8, 1600000)
            window.radio_frequency.setValue(750)
            window.radio_candidates = [{'frequency': 650000}, {'frequency': 750000}]
            view = window.spectral
            view.set_mode(1)
            view.fft_mode.setCurrentText('Radio')
            self.assertTrue(view.radio_fft_view)
            self.assertEqual(view.mode, 1)
            self.assertEqual(view.channels[0].currentText(), 'CH1')
            self.assertEqual(len(view.radio_overlay_items), 6)
            self.assertEqual(view.radio_overlay_items[-1][1].value(), 750000)
            window.radio_enabled.setChecked(True)
            self.assertEqual(view.channels[0].currentText(), 'CH1')
            view.log_frequency.setChecked(True)
            view.configure_plots()
            import numpy as np
            self.assertAlmostEqual(view.radio_overlay_items[-1][1].value(), np.log10(750000))
            view.fft_mode.setCurrentText('Spectre')
            self.assertFalse(view.radio_fft_view)
            self.assertEqual(view.radio_overlay_items, [])
            self.assertEqual(window.radio_gain.maximum(), 60)
            self.assertEqual(window.radio_gain_dial.maximum(), 600)
            window.radio_gain_dial.setValue(600)
            self.assertEqual(window.radio_gain.value(), 60)
        finally:
            window.close()
            app.processEvents()

    def test_scan_pauses_and_resumes_without_replacing_ch1(self):
        from monitor.v17.app import SerialMonitorWindow
        from monitor.v17.radio_scan import SCAN_SIZE,SCAN_BLOCKS
        from concurrent.futures import Future
        from unittest.mock import Mock
        import numpy as np
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w._acquisition_confirmed(8,1600000)
            view=w.spectral;view.set_mode(1);view.channels[0].setCurrentText('CH1')
            view.channels[1].setCurrentText('FILTER')
            self.assertEqual(view.mode_combo.count(),4)
            view.fft_mode.setCurrentText('Radio')
            w.radio_enabled.setChecked(True)
            self.assertEqual(view.channels[0].currentText(),'CH1')
            self.assertEqual(view.channels[1].currentText(),'FILTER')
            w.filter_source.setCurrentText('RADIO')
            w.filter_preset.setCurrentIndex(w.filter_preset.findData('reject_50'))
            preset=w.filter_preset.currentIndex()
            settings=w.filter_config
            gain=w.radio_gain.value()
            count=SCAN_SIZE*SCAN_BLOCKS
            w.series['CH1'].extend(np.ones(count))
            w.series['Tiempo (us)'].extend(np.arange(count)*w.applied_configuration.dt_us)
            w.sample_counter=count
            future=Future();future.set_result([])
            executor=Mock();executor.submit.return_value=future;w._radio_scan_executor=executor
            w._radio_scan()
            self.assertFalse(w.radio_enabled.isChecked())
            self.assertEqual(w.filter_preset.currentIndex(),preset)
            self.assertEqual(w.filter_config,settings)
            w._radio_scan_finished()
            self.assertTrue(w.radio_enabled.isChecked())
            self.assertEqual(w.filter_preset.currentIndex(),preset)
            self.assertEqual(w.filter_config,settings)
            self.assertEqual(w.radio_gain.value(),gain)
            self.assertEqual(view.channels[0].currentText(),'CH1')
            self.assertEqual(view.channels[1].currentText(),'FILTER')
        finally:w.close();app.processEvents()

    def test_click_tunes_rf_or_us_alias_and_rejects_edges(self):
        from monitor.v17.app import SerialMonitorWindow
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w._acquisition_confirmed(8,1600000)
            view=w.spectral
            self.assertTrue(view._tune_radio_fft_frequency(710440))
            self.assertEqual(w.radio_frequency_dial.value(),710440)
            w.radio_us.setChecked(True);w.radio_frequency.setValue(1000)
            self.assertTrue(view._tune_radio_fft_frequency(600000))
            self.assertEqual(w.radio_frequency_dial.value(),1000000)
            w.radio_frequency.setValue(500)
            w.radio_candidates=[dict(frequency=1000000)]
            self.assertTrue(view._tune_radio_fft_frequency(600000))
            self.assertEqual(w.radio_frequency_dial.value(),1000000)
            before=w.radio_frequency.value()
            self.assertFalse(view._tune_radio_fft_frequency(799999))
            self.assertEqual(w.radio_frequency.value(),before)
        finally:w.close();app.processEvents()

    def test_drag_previews_and_commits_only_on_release(self):
        from PyQt6 import QtCore,QtTest
        from monitor.v17.app import SerialMonitorWindow
        import pyqtgraph as pg
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w._acquisition_confirmed(8,1600000)
            view=w.spectral;view.set_mode(1);view.fft_mode.setCurrentText('Radio')
            view.channels[0].setCurrentText('CH1');view.channels[1].setCurrentText('Ninguno')
            w.show();app.processEvents()
            box=view.plots[0].getViewBox();box.setRange(xRange=(0,800000),yRange=(-100,0),padding=0)
            app.processEvents()
            def point(f):return view.widget.mapFromScene(box.mapViewToScene(QtCore.QPointF(f,-50)))
            before=w.radio_frequency.value()
            QtTest.QTest.mousePress(view.widget.viewport(),QtCore.Qt.MouseButton.LeftButton,pos=point(400000))
            self.assertIsNotNone(view.radio_tune_drag.plot)
            self.assertEqual(w.radio_frequency.value(),before)
            QtTest.QTest.mouseMove(view.widget.viewport(),point(600000))
            self.assertEqual(w.radio_frequency.value(),before)
            self.assertEqual(view.radio_tune_drag.items[0].pen.color().name(),'#ffbd66')
            QtTest.QTest.mouseRelease(view.widget.viewport(),QtCore.Qt.MouseButton.LeftButton,pos=point(600000))
            self.assertIsNone(view.radio_tune_drag.plot)
            self.assertLess(abs(w.radio_frequency.value()-600),3)
        finally:w.close();app.processEvents()
