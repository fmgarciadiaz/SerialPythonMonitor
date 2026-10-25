from dataclasses import replace
import json
import unittest
from monitor.v18.io.device_snapshot import DeviceIdentity,Observation,DeviceSnapshot,restore_contract
from monitor.v18.receiver.unoq_acquisition import Configuration
from monitor.v18.receiver.unoq_generator import GeneratorConfig
from monitor.v18.receiver.unoq_switch import Mode
from monitor.v18.receiver.unoq_wav import State


IDENTITY=DeviceIdentity('fixture','scope-v17-main-1','a'*64,'b'*64)
GEN=GeneratorConfig(enabled=0,frequency=1234567,final_frequency=2345678,low=123,high=3456,duty=37)
BASE=Observation(IDENTITY,Configuration(8,1600000),GEN,False,State.IDLE)


class Backend:
    def __init__(self):
        self.current=replace(BASE,acquisition=Configuration(14,40000),generator=GeneratorConfig(enabled=0))
        self.calls=[];self.fail_adc=False;self.fail_gen=False;self.bad_recovery=False
    def exclusive(self):return True
    def observe(self):return self.current
    def stop_audio(self):self.calls.append('stop');self.current=replace(self.current,wav_state=State.IDLE,running=False)
    def apply_acquisition(self,config):
        self.calls.append('adc')
        if self.fail_adc:raise TimeoutError('No APPLIED')
        self.current=replace(self.current,acquisition=config)
    def apply_generator(self,config):
        self.calls.append('generator')
        if self.fail_gen:raise TimeoutError('No generator ACK')
        self.current=replace(self.current,generator=config)
    def recover(self,seconds):
        self.calls.append('recovery')
        return dict(seconds=seconds,samples=16000000,dropped=int(self.bad_recovery),fatal=0,
                    continuous=True,configuration=self.current.acquisition)


class SnapshotTests(unittest.TestCase):
    def test_json_roundtrip_keeps_wire_profile_and_every_generator_parameter(self):
        snapshot=DeviceSnapshot.capture(BASE)
        decoded=DeviceSnapshot.from_dict(json.loads(json.dumps(snapshot.to_dict())))
        self.assertEqual(snapshot,decoded);self.assertEqual(decoded.acquisition,BASE.acquisition)
        self.assertEqual(decoded.generator,GEN);self.assertEqual(decoded.generator.duty,37)

    def test_capture_does_not_accept_active_audio_generator_or_uart(self):
        for observed in (replace(BASE,wav_state=State.PLAYING),replace(BASE,running=True),
                         replace(BASE,generator=replace(GEN,enabled=1)),replace(BASE,transport=Mode.UART)):
            with self.assertRaises(ValueError):DeviceSnapshot.capture(observed)

    def test_restore_is_verified_but_never_labels_fake_backend_as_hardware(self):
        backend=Backend();report=restore_contract(DeviceSnapshot.capture(BASE),backend)
        self.assertTrue(report['restore_contract_ok']);self.assertFalse(report['hardware_restored'])
        self.assertTrue(json.loads(json.dumps(report,allow_nan=False))['restore_contract_ok'])
        self.assertEqual(backend.calls,['stop','adc','generator','recovery'])
        self.assertTrue(DeviceSnapshot.capture(BASE).matches(backend.observe()))

    def test_identity_change_prevents_all_restore_writes(self):
        backend=Backend();backend.current=replace(backend.current,identity=replace(IDENTITY,relay_sha256='c'*64))
        report=restore_contract(DeviceSnapshot.capture(BASE),backend)
        self.assertFalse(report['restore_contract_ok']);self.assertEqual(backend.calls,[])

    def test_adc_failure_still_attempts_exact_generator_restore_without_success_claim(self):
        backend=Backend();backend.fail_adc=True
        report=restore_contract(DeviceSnapshot.capture(BASE),backend)
        self.assertFalse(report['restore_contract_ok'])
        self.assertEqual(backend.calls,['stop','adc','generator']);self.assertEqual(backend.current.generator,GEN)

    def test_generator_or_recovery_failure_prevents_acceptance(self):
        for field in ('fail_gen','bad_recovery'):
            backend=Backend();setattr(backend,field,True)
            report=restore_contract(DeviceSnapshot.capture(BASE),backend)
            self.assertFalse(report['restore_contract_ok']);self.assertTrue(report['errors'])

    def test_unconfirmed_stop_does_not_change_adc_or_generator(self):
        backend=Backend()
        backend.stop_audio=lambda:backend.calls.append('stop')
        backend.current=replace(backend.current,wav_state=State.PLAYING)
        report=restore_contract(DeviceSnapshot.capture(BASE),backend)
        self.assertFalse(report['restore_contract_ok']);self.assertEqual(backend.calls,['stop'])

    def test_unknown_schema_or_missing_relay_identity_is_rejected(self):
        data=DeviceSnapshot.capture(BASE).to_dict();data['schema']=2
        with self.assertRaises(ValueError):DeviceSnapshot.from_dict(data)
        with self.assertRaises(ValueError):DeviceIdentity('fixture','app','a'*64,'')

    def test_one_sample_in_ten_seconds_is_not_sustained_recovery(self):
        backend=Backend();original=backend.recover
        backend.recover=lambda seconds:{**original(seconds),'samples':1}
        report=restore_contract(DeviceSnapshot.capture(BASE),backend)
        self.assertFalse(report['restore_contract_ok'])
