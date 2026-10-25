import unittest
from unittest.mock import Mock, patch
from monitor.v17.receiver.unoq_acquisition import Configuration, RATES, UART_RATES
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_switch import Mode

class ADC1600Tests(unittest.TestCase):
    def test_scope_and_private_preparation(self):
        config=Configuration(8,1600000)
        self.assertEqual((config.period,config.channels,config.node_pairs),(100,1,3456))
        self.assertFalse(config._native['headroom'])
        self.assertNotIn(1428571,RATES)
        self.assertNotIn(1600000,UART_RATES)
        for bits in (10,12,14,16):
            with self.assertRaises(ValueError):Configuration(bits,1600000)

    def test_preparation_pumps_and_never_publishes_private_samples(self):
        for connected,seconds in ((False,2.),(True,.5)):
            with self.subTest(connected=connected):
                receiver=OutputReceiver(Mock(),Mock())
                receiver.mode=Mode.SPI if connected else None
                receiver.select=Mock(side_effect=lambda mode:setattr(receiver,'mode',mode))
                samples,confirmed=receiver.on_samples,Mock()
                receiver.on_configuration=confirmed
                receiver.generator=Mock()
                applied=[];now=[0.]
                def configure(config):
                    applied.append(config.rate)
                    receiver.on_configuration(config)
                    return True
                def pump():
                    receiver.on_samples(['private']);now[0]+=.25
                receiver._configure_once=configure
                receiver.pump=Mock(side_effect=pump)
                with patch('monitor.v17.receiver.unoq_config_receiver.time.monotonic',side_effect=lambda:now[0]):
                    self.assertTrue(receiver.configure(Configuration(8,1600000)))
                self.assertEqual(now[0],seconds)
                self.assertEqual(applied,[40000,1428571,1600000])
                self.assertEqual(receiver.pump.call_count,int(seconds/.25))
                samples.assert_not_called()
                confirmed.assert_called_once_with(Configuration(8,1600000))
                self.assertIs(receiver.on_samples,samples)
                self.assertIs(receiver.on_configuration,confirmed)
                receiver.generator.assert_not_called()

    def test_preparation_failure_restores_callbacks_without_requesting_target(self):
        receiver=OutputReceiver(Mock(),Mock());receiver.mode=Mode.SPI
        samples,confirmed=receiver.on_samples,receiver.on_configuration
        receiver.generator=Mock()
        receiver._configure_once=Mock(side_effect=RuntimeError('APPLIED missing'))
        with self.assertRaises(RuntimeError):receiver.configure(Configuration(8,1600000))
        self.assertEqual(receiver._configure_once.call_count,1)
        self.assertIs(receiver.on_samples,samples)
        self.assertIs(receiver.on_configuration,confirmed)
        receiver.generator.assert_not_called()

    def test_reapplying_same_rate_does_not_prepare_or_change_generator(self):
        receiver=OutputReceiver(Mock(),Mock());receiver.mode=Mode.SPI
        receiver.config=Configuration(8,1600000)
        receiver.generator=Mock();receiver._configure_once=Mock()
        self.assertFalse(receiver.configure(receiver.config))
        receiver.generator.assert_not_called()
        receiver._configure_once.assert_not_called()

    def test_first_target_samples_after_applied_in_same_pump_are_delivered(self):
        receiver=OutputReceiver(Mock(),Mock());receiver.mode=Mode.SPI
        samples=receiver.on_samples;order=[]
        receiver.on_configuration=lambda c:order.append(('applied',c.rate))
        samples.side_effect=lambda rows:order.append(('samples',rows))
        def configure(config):
            receiver.on_samples(['before-applied'])
            receiver.on_configuration(config)
            receiver.on_samples([config.rate])
            return True
        receiver._configure_once=configure
        receiver.pump=Mock(side_effect=lambda:receiver.on_samples(['warm']))
        with patch('monitor.v17.receiver.unoq_config_receiver.time.monotonic',side_effect=[0,2.1]):
            receiver.configure(Configuration(8,1600000))
        self.assertEqual(order,[('applied',1600000),('samples',[1600000])])
        self.assertIs(receiver.on_samples,samples)

if __name__=='__main__':unittest.main()

class ADC1600SelectorTests(unittest.TestCase):
    def test_label_and_private_preparation_visibility(self):
        from PyQt6 import QtWidgets
        from monitor.v17.app import SerialMonitorWindow
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        pending=Configuration(8,1600000)._native.get('integration_pending',False)
        # Exercise the accepted selector without leaking metadata changes across tests.
        with patch.dict(Configuration(8,1600000)._native,{'integration_pending':False}), patch('monitor.v17.app.usb_devices',return_value=[]), patch('monitor.v17.app.RATES',__import__('monitor.v17.app',fromlist=['RATES']).RATES+(1600000,)):
            window=SerialMonitorWindow()
        try:
            Configuration(8,1600000)._native['integration_pending']=False
            window.config_bits_combo.setCurrentIndex(window.config_bits_combo.findData(8))
            window._destination_changed()
            sample=window.legend.items[0][0]
            if not hasattr(sample,'sigClicked'):
                from PyQt6 import QtCore
                event=Mock();event.button.return_value=QtCore.Qt.MouseButton.LeftButton
                name=window.known_columns[0]
                was_checked=window.graph_channel_actions[name].isChecked()
                sample.mouseClickEvent(event)
                self.assertEqual(window.graph_channel_actions[name].isChecked(),not was_checked)
                event.accept.assert_called_once()
            index=window.config_rate_combo.findData(1600000)
            self.assertGreaterEqual(index,0)
            self.assertTrue(window.config_rate_combo.itemText(index).endswith('(CH1)'))
            self.assertNotIn('s/holg',window.config_rate_combo.itemText(index))
            self.assertTrue(window.config_rate_combo.model().item(index).isEnabled())
            self.assertEqual(window.config_rate_combo.findData(1428571),-1)
            window.applied_configuration=Configuration(8,1600000)
            window._refresh_applied_summary()
            self.assertNotIn('s/holg',window.confirmed_output_label.text())
            window.config_bits_combo.setCurrentIndex(window.config_bits_combo.findData(14))
            window._destination_changed()
            self.assertFalse(window.config_rate_combo.model().item(index).isEnabled())
        finally:
            Configuration(8,1600000)._native['integration_pending']=pending
            window.close()
            app.processEvents()


    def test_rate_change_preserves_generator_and_vertical_controls(self):
        from PyQt6 import QtWidgets
        from monitor.v17.app import SerialMonitorWindow
        from monitor.v17.receiver.unoq_generator import GeneratorConfig, GeneratorReply
        from monitor.v17.receiver.unoq_switch import Phase, Reason
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v17.app.usb_devices',return_value=[]):
            window=SerialMonitorWindow()
        try:
            window._acquisition_confirmed(8,1403508)
            config=GeneratorConfig(wave=1,enabled=1,frequency=1234000,
                final_frequency=1234000,low=620,high=1870,duration=2345)
            window._generator_dirty=False
            window._generator_confirmed(GeneratorReply(0x80000001,Phase.APPLIED,
                Reason.OK,True,config,config,True,True,True,True,True))
            controls=(window.generator_frequency,window.generator_final_frequency,
                window.generator_amplitude,window.generator_offset,
                window.generator_duty,window.generator_duration,
                window.generator_frequency_dial,window.generator_offset_slider,
                window.dial_v_scale)
            before=[c.value() for c in controls]
            window.spectral.channels[1].setCurrentText('CH1')
            window._acquisition_confirmed(8,1600000)
            self.assertEqual([c.value() for c in controls],before)
            self.assertEqual(window.spectral.channels[1].currentText(),'CH1')
            window.spectral.channels[1].setCurrentText('FILTER')
            window._acquisition_confirmed(8,1403508)
            self.assertEqual(window.spectral.channels[1].currentText(),'FILTER')
            window.spectral.channels[1].setCurrentText('RADIO')
            window._acquisition_confirmed(8,1600000)
            self.assertEqual(window.spectral.channels[1].currentText(),'RADIO')
            self.assertEqual(window._generator_active,config)
            self.assertTrue(window.generator_enabled.isChecked())
        finally:
            window.close();app.processEvents()
