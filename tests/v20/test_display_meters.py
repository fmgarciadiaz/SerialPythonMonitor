import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ['PYQTGRAPH_QT_LIB']='PySide6'
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import pyqtgraph as pg
from PySide6 import QtWidgets,QtTest
from monitor.v20.display_fps import DisplayFps
from monitor.v20.radio_led_spectrum import RadioLedSpectrum
from monitor.v20.wav_output_meter import WavOutputMeter


class DisplayMeterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_fps_counts_data_paints_and_goes_zero_without_new_data(self):
        widget=pg.PlotWidget();counter=DisplayFps();counter.watch(widget,[widget.plotItem])
        curve=widget.plot([0,1],[0,1]);widget.show();QtTest.QTest.qWait(60)
        counter.sample(widget,counter.started+1)
        for i in range(5):curve.setData([0,1],[i,i+1])
        QtTest.QTest.qWait(40)
        rate=counter.sample(widget,counter.started+1)
        self.assertEqual(rate,1.)  # Five updates coalesced into one paint.
        widget.setTitle('Only a title repaint');widget.viewport().update()
        QtTest.QTest.qWait(40)
        self.assertEqual(counter.sample(widget,counter.started+1),0.)
        widget.close()

    def test_spectral_image_paint_uses_its_own_view(self):
        widget=pg.GraphicsLayoutWidget();plot=widget.addPlot()
        image=pg.ImageItem();plot.addItem(image)
        counter=DisplayFps();counter.watch(widget,[plot]);widget.show()
        QtTest.QTest.qWait(40);counter.sample(widget,counter.started+1)
        image.setImage(np.arange(16).reshape(4,4))
        QtTest.QTest.qWait(40)
        self.assertEqual(counter.sample(widget,counter.started+1),1.)
        widget.hide();image.setImage(np.ones((4,4)));QtTest.QTest.qWait(30)
        self.assertEqual(counter.sample(widget,counter.started+1),0.)
        widget.close()

    def test_fps_refresh_uses_current_fs_text(self):
        from monitor.v20.app import SerialMonitorWindow
        titles=[]
        owner=SimpleNamespace(spectral=SimpleNamespace(mode=0),
            plot_widget=SimpleNamespace(setTitle=titles.append),
            _display_fps=SimpleNamespace(sample=lambda widget:12.5),
            fps_label=QtWidgets.QLabel(),lbl_top_fs=QtWidgets.QLabel('40,00 kS/s'),
            current_fs_text='-- S/s',is_running=True,sample_counter=40000,h_scale=9000)
        SerialMonitorWindow._update_display_fps(owner)
        self.assertIn('Fs: 40,00 kS/s',titles[-1])
        self.assertEqual(owner.fps_label.text(),'FPS 12,5')

    def test_wav_mmap_follows_played_position_volume_and_stop(self):
        owner=QtWidgets.QWidget();owner.generator_mode=QtWidgets.QComboBox()
        owner.generator_mode.addItems([str(i) for i in range(8)]);owner.generator_mode.setCurrentIndex(4)
        owner.generator_amplitude=QtWidgets.QDoubleSpinBox();owner.generator_amplitude.setRange(0,3.3)
        owner.generator_amplitude.setValue(3.3)
        spectrum=RadioLedSpectrum(owner);dial=QtWidgets.QDial(owner)
        meter=WavOutputMeter(owner,spectrum,dial)
        owner.resize(300,200);owner.show();spectrum.show();self.app.processEvents()
        codes=np.rint((1.65+1.5*np.sin(2*np.pi*1000*np.arange(30000)/20000))*4095/3.3).astype('<u2')
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'codes.npy';np.save(p,codes)
            meter.load(str(p),20000)
            self.assertIsInstance(meter.codes,np.memmap)
            meter.observe(SimpleNamespace(state=0))
            self.assertIsNotNone(meter.codes)  # An old IDLE poll must not erase priming.
            status=SimpleNamespace(state=2,rate=20000,played=10000,accepted=2000)
            # accepted can be session-relative after a seek; played is absolute.
            with patch('monitor.v20.wav_output_meter.time.monotonic',return_value=10.):
                meter.observe(status);meter.refresh()
            full=meter.target
            self.assertGreater(full,.8);self.assertEqual(len(spectrum.samples),2048)
            self.assertGreater(np.max(spectrum._target),.4)
            owner.generator_amplitude.setValue(1.65)
            with patch('monitor.v20.wav_output_meter.time.monotonic',return_value=10.1):
                meter.observe(status);meter.refresh()
            self.assertAlmostEqual(meter.target,full/2,places=6)
            meter.observe(SimpleNamespace(state=3))
            self.assertIsNone(meter.codes);self.assertFalse(meter.timer.isActive())
            self.assertEqual(dial.audio_meter_level,0.)
            self.assertTrue(np.all(spectrum.levels==0))
        owner.close()


if __name__=='__main__':unittest.main()
