import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch, MagicMock
from transport.unoq_generator import GeneratorConfig, generator_request, generator_reply
from transport.unoq_switch import Phase
from transport.unoq_config_decoder import ConfigurationDecoder
from transport.unoq_usb import ProtocolError
from test_acquisition_config import frame
from transport.unoq_acquisition import Configuration

ROOT=Path(__file__).resolve().parents[1]
STUB='''#include <cstdint>
#define GENERATOR_TEST
#define CONFIG_SYS_CLOCK_TICKS_PER_SEC 10000
#define K_TICKS(x) (x)
struct k_timer {};
struct DAC_TypeDef { uint32_t DHR12R1, CR; };static DAC_TypeDef regs;
#define DAC1_BASE (&regs)
#define DAC_CR_TEN1 4U
static int64_t now=0;
static int64_t k_uptime_ticks(){return now;}
static unsigned irq_lock(){return 0;}static void irq_unlock(unsigned){}
static void k_timer_init(k_timer *,void (*)(k_timer *),void *){}
static void k_timer_start(k_timer *,unsigned,unsigned){}
#include "generator_timing.h"
namespace generator_hw {
static bool failed=false, enabled=false;
static generator::Timing current{};
static bool init(){return true;}
static bool healthy(){return !failed;}
static bool stop(uint16_t level){enabled=false;regs.DHR12R1=level;return !failed;}
static bool start(uint32_t *p,unsigned,generator::Timing t){current=t;enabled=true;regs.DHR12R1=p[0];return !failed;}
static void set_timing(generator::Timing t){current=t;}
}
#include "generator.h"
'''

class GeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        cls.folder=Path(cls.tmp.name); cls.exe=cls.folder/'generator'
        source=cls.folder/'generator.cpp'
        source.write_text(STUB+'''#include <cstdio>
int main(){generator::start();uint8_t p[512];scope_gen::Request r{};uint32_t seq=0;
while(fread(p,1,512,stdin)==512){if(!scope_gen::decode(p,512,r))return 2;
const auto reply=generator::submit(r);scope_gen::encode(p,seq++,reply);fwrite(p,1,512,stdout);}return 0;}
''')
        subprocess.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I',str(ROOT/'arduino/v8_config/oscilloscope/sketch'),str(source),'-o',str(cls.exe)],check=True)
        relay=cls.folder/'relay.c';cls.relay=cls.folder/'relay'
        relay.write_text('#define main verifier_main\n#include "diagnosticos/verificar_spi.c"\n#undef main\n'
            '#include "transport/config_relay_protocol.h"\n'
            'int main(int argc,char **argv){(void)argv;init_crc();DualChecker c={.period=32,.bits=14};uint8_t p[512];'
            'while(fread(p,1,512,stdin)==512)if(!(argc>1?dual_command(p):dual_feed(&c,p)))return 2;return 0;}')
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT),str(relay),'-lm','-o',str(cls.relay)],check=True)
    def test_all_waveforms_and_modes_cross_language(self):
        for wave in range(5):
            for mode in range(3 if wave!=4 else 1):
                c=GeneratorConfig(wave=wave,mode=mode,frequency=20000000,final_frequency=100,low=123,high=2345)
                request=generator_request(0x80000001,c)
                packet=subprocess.run([str(self.exe)],input=request,capture_output=True,check=True).stdout
                reply=generator_reply(packet)
                self.assertEqual(reply.active,c);self.assertEqual(reply.phase,Phase.APPLIED)
                self.assertEqual(subprocess.run([str(self.relay),'command'],input=request).returncode,0)
                self.assertEqual(subprocess.run([str(self.relay)],input=packet).returncode,0)
    def test_query_and_duplicate_do_not_reconfigure_acquisition(self):
        c=GeneratorConfig(wave=2,enabled=0)
        request=generator_request(0x80000001,c)
        packets=subprocess.run([str(self.exe)],input=request*2+generator_request(0x80000002),capture_output=True,check=True).stdout
        self.assertEqual(generator_reply(packets[1024:]).active,c)
        decoder=ConfigurationDecoder()
        decoder.feed(packets+frame(Configuration(),epoch=0,seq=3,index=0))
        self.assertEqual(decoder.pairs,2);self.assertEqual(decoder.epoch,0)
    def test_rejected_range_and_conflicting_id_are_reported(self):
        request=bytearray(generator_request(0x80000001))
        struct.pack_into('<H',request,6,8)
        request[16:36]=GeneratorConfig().pack()
        struct.pack_into('<I',request,20,20000001)
        struct.pack_into('<I',request,508,zlib.crc32(request[:508]))
        packet=subprocess.run([str(self.exe)],input=request,capture_output=True,check=True).stdout
        self.assertEqual(generator_reply(packet).phase,Phase.REJECTED)
        a=generator_request(0x80000001,GeneratorConfig())
        b=generator_request(0x80000001,GeneratorConfig(wave=1))
        packet=subprocess.run([str(self.exe)],input=a+b,capture_output=True,check=True).stdout[512:]
        self.assertEqual(generator_reply(packet).phase,Phase.REJECTED)
    def test_corrupt_crc_reserved_and_contradictory_state_rejected(self):
        request=generator_request(0x80000001,GeneratorConfig())
        reply=subprocess.run([str(self.exe)],input=request,capture_output=True,check=True).stdout
        for offset,value in ((22,2),(23,1),(27,1),(64,1)):
            p=bytearray(reply);p[offset]=value;struct.pack_into('<I',p,508,zlib.crc32(p[:508]))
            with self.assertRaises(ProtocolError):generator_reply(p)
            self.assertNotEqual(subprocess.run([str(self.relay)],input=p).returncode,0)
        p=bytearray(request);p[19]=1;struct.pack_into('<I',p,508,zlib.crc32(p[:508]))
        self.assertNotEqual(subprocess.run([str(self.exe)],input=p).returncode,0)
    def test_motor_levels_frequency_completion_and_idempotency(self):
        source=self.folder/'motor.cpp';exe=self.folder/'motor'
        source.write_text(STUB+'''#include <cassert>
int main(){generator::start();assert(generator::running);
for(unsigned wave=0;wave<4;++wave)for(uint32_t ph=0;;ph+=0x01000000U){
const auto v=generator::value(wave,ph,100,3000);assert(v>=100 && v<=3000);if(ph==0xff000000U)break;}
assert(generator::value(2,0,0,4095)==0);assert(generator::value(2,0x80000000U,0,4095)==4095);
auto c=scope_gen::defaults();c.frequency=10000;generator::apply(c);
assert(generator::points==2 && generator_hw::enabled);
assert((uint64_t(generator_hw::current.prescaler)+1)*(generator_hw::current.reload+1)>7999000);
assert((uint64_t(generator_hw::current.prescaler)+1)*(generator_hw::current.reload+1)<8001000);
for(unsigned wave=0;wave<4;++wave){c.wave=wave;c.frequency=20000000;assert(generator::apply(c));
assert(generator::points>=2 && generator::points<=256);
for(unsigned i=0;i<generator::points;++i)assert(generator::samples[i]<=4095);
const auto t=generator::timings[0];
const double actual=160000000.0/(double(t.prescaler+1)*(t.reload+1)*generator::points);
assert(actual>19900 && actual<20100);}
c.wave=4;c.low=123;c.high=3456;c.duration=10;scope_gen::Request r{0x80000001,c,false};
generator::submit(r);assert(regs.DHR12R1==3456);
now+=100;generator::tick(nullptr);assert(!generator::running && regs.DHR12R1==123);
generator::submit(r);assert(!generator::running);r.id++;generator::submit(r);assert(generator::running);
for(unsigned mode=1;mode<=2;++mode){c.wave=1;c.mode=mode;c.duration=100;c.frequency=10000;c.final_frequency=20000000;generator::apply(c);
assert(generator::timings[128].reload<generator::timings[0].reload);now+=1000;generator::tick(nullptr);assert(!generator::running);}
c.mode=0;c.enabled=0;generator::apply(c);assert(!generator::running && regs.DHR12R1==0);return 0;}
''')
        subprocess.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I',str(ROOT/'arduino/v8_config/oscilloscope/sketch'),str(source),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    def test_timer_range_accuracy_and_dac_failure_are_reported(self):
        source=self.folder/'timing.cpp';exe=self.folder/'timing'
        source.write_text(STUB+'''#include <cassert>
int main(){assert(generator::start());auto c=scope_gen::defaults();
for(unsigned wave=0;wave<4;++wave){c.wave=wave;
for(uint32_t f=100;f<=20000000;f=uint32_t(f*1.2)+1){c.frequency=f;
const unsigned n=generator::points_for(c);const auto t=generator::timing(f,n);
const double actual=160000000.0/((double(t.prescaler)+1)*(double(t.reload)+1)*n);
assert(fabs(actual/(f/1000.0)-1)<0.003);
assert(uint64_t(f)*n<=uint64_t(scope_gen::UPDATE_HZ)*1000);}}
c.wave=1;c.frequency=20000000;assert(generator::apply(c));
generator_hw::failed=true;generator::tick(nullptr);assert(!generator::running);
scope_gen::Request query{0x80000001,c,true};
auto r=generator::submit(query);assert(r.phase==scope_control::REJECTED && r.reason==scope_control::HARDWARE);
scope_gen::Request set{0x80000002,c,false};r=generator::submit(set);
assert(r.phase==scope_control::REJECTED && r.reason==scope_control::HARDWARE);
r=generator::submit(set);assert(r.phase==scope_control::REJECTED);return 0;}
''')
        subprocess.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I',str(ROOT/'arduino/v8_config/oscilloscope/sketch'),str(source),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    def test_generator_event_keeps_sample_timeline_and_capture(self):
        from transport.unoq_config_receiver import OutputReceiver
        c=GeneratorConfig(wave=1)
        packet=subprocess.run([str(self.exe)],input=generator_request(0x80000001,c),capture_output=True,check=True).stdout
        receiver=OutputReceiver(MagicMock(),lambda samples:None)
        receiver.mode=0;receiver.next_index=0;receiver.visible=True
        receiver.connection.read.return_value=packet+frame(Configuration(),epoch=0,seq=1,index=0)
        receiver.pump()
        self.assertEqual(receiver.next_index,2);self.assertEqual(receiver.config,Configuration())

class GeneratorUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt5 import QtWidgets
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def test_frequency_typing_commits_on_enter_without_padding(self):
        from monitor.v10.app import SerialMonitorWindow
        from PyQt5 import QtCore, QtTest
        with patch('monitor.v10.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w.show()
            w.serial_worker=MagicMock()
            spin=w.generator_frequency
            spin.setLocale(QtCore.QLocale.c())
            spin.setFocus()
            self.app.processEvents()
            spin.lineEdit().selectAll()
            QtTest.QTest.keyClicks(spin.lineEdit(), '12.5')
            QtTest.QTest.qWait(300)
            self.assertEqual(spin.value(), 2.5)
            w.serial_worker.request_generator.assert_not_called()
            QtTest.QTest.keyClick(spin.lineEdit(), QtCore.Qt.Key_Return)
            QtTest.QTest.qWait(300)
            self.assertEqual(w.serial_worker.request_generator.call_args.args[0].frequency, 12500)
            self.assertEqual(spin.textFromValue(10), '10 Hz')
            self.assertEqual(spin.textFromValue(12.5), '12.5 Hz')
            self.assertEqual(spin.valueFromText('12.5 Hz'), 12.5)
            self.assertEqual(spin.valueFromText('12 kHz'), 12000)
        finally:w.close()
    def test_dial_updates_display_during_drag_and_applies_on_release(self):
        from monitor.v10.app import SerialMonitorWindow
        from PyQt5 import QtTest
        with patch('monitor.v10.app.usb_devices', return_value=[]):
            w = SerialMonitorWindow()
        try:
            w.serial_worker = MagicMock()
            w.generator_frequency_dial.setSliderDown(True)
            w.generator_frequency_dial.setValue(1000)
            self.assertEqual(w.generator_frequency.value(), 20000)
            self.assertEqual(w.generator_frequency.text(), '20 kHz')
            QtTest.QTest.qWait(300)
            w.serial_worker.request_generator.assert_not_called()
            w.generator_frequency_dial.setSliderDown(False)
            QtTest.QTest.qWait(300)
            self.assertEqual(w.serial_worker.request_generator.call_args.args[0].frequency, 20000000)
        finally:
            w.close()

    def test_generator_selectors_open_from_center_and_change_selection(self):
        from monitor.v10.app import SerialMonitorWindow
        from PyQt5 import QtCore, QtTest
        with patch('monitor.v10.app.usb_devices', return_value=[]):
            w = SerialMonitorWindow()
        try:
            w.show()
            self.app.processEvents()
            for combo in (w.generator_mode, w.generator_wave):
                QtTest.QTest.mouseClick(combo, QtCore.Qt.LeftButton, pos=combo.rect().center())
                self.app.processEvents()
                self.assertTrue(combo.view().isVisible())
                QtTest.QTest.keyClick(combo.view(), QtCore.Qt.Key_Down)
                QtTest.QTest.keyClick(combo.view(), QtCore.Qt.Key_Return)
                self.assertEqual(combo.currentIndex(), 1)
                self.assertTrue(w._generator_dirty)
        finally:
            w.close()

    def test_scale_editors_commit_and_follow_dials(self):
        from monitor.v10.app import SerialMonitorWindow
        from PyQt5 import QtCore, QtTest
        with patch('monitor.v10.app.usb_devices', return_value=[]):
            w = SerialMonitorWindow()
        try:
            w.show()
            for editor, text in ((w.lbl_h_scale, '25000'), (w.lbl_v_scale, '4.25')):
                editor.setLocale(QtCore.QLocale.c())
                editor.setFocus()
                editor.lineEdit().selectAll()
                QtTest.QTest.keyClicks(editor.lineEdit(), text)
                QtTest.QTest.keyClick(editor.lineEdit(), QtCore.Qt.Key_Return)
            self.assertEqual(w.h_scale, 25000)
            self.assertEqual(w.dial_h_scale.value(), 25000)
            self.assertEqual(w.v_scale, 4.25)
            self.assertEqual(w.dial_v_scale.value(), 425)
            w.dial_h_scale.setValue(17000)
            w.dial_v_scale.setValue(250)
            self.assertEqual(w.lbl_h_scale.value(), 17000)
            self.assertEqual(w.lbl_v_scale.value(), 2.5)
        finally:
            w.close()

    def test_pulse_units_preserve_duration_when_switching_modes(self):
        from monitor.v10.app import SerialMonitorWindow
        with patch('monitor.v10.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w.generator_mode.setCurrentIndex(1)
            w.generator_duration.setValue(0.2)
            w.generator_wave.setCurrentIndex(4)
            self.assertEqual(w.generator_duration.suffix(), ' ms')
            self.assertEqual(w.generator_duration.value(), 200)
            self.assertEqual(w._generator_config().duration, 200)
            self.assertTrue(w.generator_frequency.isHidden())
            w.generator_duration.setValue(125)
            w.generator_wave.setCurrentIndex(1)
            w.generator_mode.setCurrentIndex(2)
            self.assertEqual(w.generator_duration.suffix(), ' s')
            self.assertEqual(w.generator_duration.value(), 0.125)
            self.assertEqual(w._generator_config().duration, 125)
            self.assertEqual(w._generator_labels[w.generator_frequency].text(), 'Frecuencia inicial')
        finally:w.close()
    def test_generator_column_auto_apply_and_voltage_validation(self):
        from monitor.v10.app import SerialMonitorWindow
        from PyQt5 import QtTest
        with patch('monitor.v10.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w.show();self.app.processEvents();self.assertTrue(w.generator_panel.isVisible())
            self.assertLess(w.generator_column.x(), w.plot_widget.mapTo(w.centralWidget(), w.plot_widget.rect().topLeft()).x())
            self.assertFalse(w.generator_wave.itemIcon(1).isNull())
            w.serial_worker=MagicMock();w.generator_wave.setCurrentIndex(1)
            QtTest.QTest.qWait(300)
            w.serial_worker.request_generator.assert_called_once_with(GeneratorConfig(wave=1))
            w.generator_offset.setValue(0)
            QtTest.QTest.qWait(300)
            self.assertIn('ambos niveles',w.generator_status.text())
            self.assertEqual(w.serial_worker.request_generator.call_count,1)
            w.generator_enabled.setChecked(False)
            QtTest.QTest.qWait(300)
            self.assertEqual(w.serial_worker.request_generator.call_args.args[0].enabled,0)
        finally:w.close()
    def test_frequency_dial_and_numeric_input_stay_in_sync(self):
        from monitor.v10.app import SerialMonitorWindow
        with patch('monitor.v10.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w.generator_frequency_dial.setValue(1000)
            self.assertEqual(w.generator_frequency.value(),20000)
            self.assertEqual(w._generator_config().frequency,20000000)
            w.generator_frequency.setValue(.1)
            self.assertEqual(w.generator_frequency_dial.value(),0)
            w.generator_wave.setCurrentIndex(4)
            self.assertTrue(w.generator_frequency_dial.isHidden())
        finally:w.close()
