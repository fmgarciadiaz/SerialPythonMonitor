import unittest
import numpy as np
from dataclasses import replace
from monitor.v15.virtual_instruments import PianoStrings, InstrumentBody, GuitarStrings, warmup, modal_kernel
from monitor.v15.fm_source import FMSource, FMParameters
from monitor.v15.piano_profile import piano_profile

class PhysicalInstrumentTests(unittest.TestCase):
    def setUp(self):
        if modal_kernel is None:self.skipTest('Numba no instalado')
        warmup()
    def test_stiff_piano_partial_is_inharmonic_and_chunks_match(self):
        source=PianoStrings(20000,220,.12)
        audio=source.render(20000,brightness=.95,stiffness=.002)
        spectrum=abs(np.fft.rfft(audio*np.hanning(len(audio))))
        frequencies=np.fft.rfftfreq(len(audio),1/20000)
        b=piano_profile(220)['stiffness']*.002/.0003
        expected=5*220*np.sqrt((1+b*25)/(1+b))
        mask=(frequencies>expected-10)&(frequencies<expected+10)
        peak=frequencies[mask][np.argmax(spectrum[mask])]
        self.assertLess(abs(peak-expected),4)
        self.assertGreater(peak-5*220,10)
        whole=PianoStrings(20000,440).render(4800)
        chunks=PianoStrings(20000,440)
        np.testing.assert_array_equal(whole,np.concatenate([chunks.render(480) for _ in range(10)]))
    def test_hammer_velocity_changes_normalized_brightness(self):
        def brightness(velocity):
            a=PianoStrings(20000,220,.12,velocity).render(4000,brightness=.8)
            spectrum=abs(np.fft.rfft(a*np.hanning(len(a))))**2
            f=np.fft.rfftfreq(len(a),1/20000)
            return spectrum[f>2000].sum()/spectrum.sum()
        self.assertGreater(brightness(1),brightness(.25))
    def test_bridge_and_body_have_stable_decaying_tails(self):
        for model in ('guitar','piano'):
            body=InstrumentBody(40000,model)
            impulse=np.zeros(40000);impulse[0]=1
            output=body.render(impulse,.8,.5)
            self.assertTrue(np.isfinite(output).all())
            self.assertGreater(np.max(abs(output[1:4000])),.0001)
            self.assertLess(np.max(abs(output[-4000:])),1e-6)
    def test_polyphonic_guitar_and_piano_release(self):
        for model in ('guitar','piano'):
            params=FMParameters(preset='Piano Virtual' if model=='piano' else 'Guitarra',waveform='virtual',virtual_model=model,notes=((48,100),(60,127)),envelope=(.001,.01,1,.1))
            source=FMSource(rate=40000,parameters=params)
            data=source[0:4800];self.assertGreater(np.std(data),50)
            source.update(replace(params,notes=()))
            for i in range(4800,24000,480):source[i:i+480]
            self.assertEqual(len(source.voices),0)

    def test_nonlinear_hammer_and_coupling_are_bounded(self):
        from monitor.v15.virtual_instruments import hammer_kernel
        soft=hammer_kernel(80000,.25,.75,220.)
        hard=hammer_kernel(80000,1.,.75,220.)
        self.assertTrue(np.isfinite(hard).all())
        self.assertGreaterEqual(hard.min(),0)
        self.assertAlmostEqual(hard.sum(),1)
        self.assertGreater(hard.max(),soft.max())
        state=np.random.default_rng(1).normal(size=(24,2))
        energy=np.sum(state**2)
        rotation=np.tile([.999,0.],(24,1))
        modal_kernel(state,rotation,np.ones(24),np.zeros(1),1,1000,3,.005)
        self.assertLess(np.sum(state**2),energy)

    def test_pedal_extends_sympathetic_resonance(self):
        impulse=np.zeros(40000);impulse[0]=1
        dry=InstrumentBody(40000,'piano').render(impulse,.8,.2,False)
        sustained=InstrumentBody(40000,'piano').render(impulse,.8,.2,True)
        self.assertGreater(np.std(sustained[20000:]),np.std(dry[20000:])*2)
        body=InstrumentBody(40000,'piano')
        body.render(impulse[:4000],.8,.2,True)
        tail=body.render(np.zeros(120000),.8,.2,False)
        self.assertLess(np.max(abs(tail[-4000:])),1e-6)

    def test_upgraded_guitar_and_piano_are_chunk_continuous(self):
        for model in ('guitar','piano'):
            def make():return GuitarStrings(80000,220,.22,.8) if model=='guitar' else PianoStrings(80000,220,.12,.8,8400)
            whole=make().render(4800)
            source=make();parts=np.concatenate([source.render(480) for _ in range(10)])
            np.testing.assert_allclose(whole,parts,atol=1e-12,rtol=1e-12)

    def test_native_piano_pipeline_is_continuous_at_both_output_rates(self):
        for rate in (20000,40000):
            params=FMParameters(preset='Piano Virtual',waveform='virtual',virtual_model='piano',notes=((60,110),(64,100)),envelope=(.001,.01,1,.1))
            whole=FMSource(rate=rate,parameters=params)[0:4800]
            source=FMSource(rate=rate,parameters=params)
            chunks=np.concatenate([source[i:i+480] for i in range(0,4800,480)])
            self.assertLessEqual(np.max(abs(whole.astype(int)-chunks.astype(int))),1)
            self.assertEqual(source.voices[60].string.rate,rate)

    def test_published_profile_anchors_and_units(self):
        for note,b,z,mass,position,k,p in (
                (36,.000221,19.10,.011,.135,4e8,2.3),
                (60,.000364,12.26,.009,.125,4.5e9,2.5),
                (96,.007740,9.63,.006,.09,1e12,3.)):
            profile=piano_profile(440*2**((note-69)/12))
            self.assertAlmostEqual(profile['stiffness']/b,1,delta=.003)
            self.assertAlmostEqual(profile['impedance'],z,delta=.015)
            self.assertAlmostEqual(profile['mass'],mass)
            self.assertAlmostEqual(profile['position'],position)
            self.assertAlmostEqual(profile['contact_k']/k,1)
            self.assertAlmostEqual(profile['exponent'],p)

    def test_contact_and_tuning_across_register_and_velocity(self):
        from monitor.v15.virtual_instruments import hammer_kernel
        for note in range(24,109,12):
            frequency=440*2**((note-69)/12)
            for velocity in (.25,1.):
                force=hammer_kernel(80000,velocity,.78,frequency)
                self.assertTrue(np.isfinite(force).all())
                self.assertGreaterEqual(force.min(),0)
                self.assertAlmostEqual(force.sum(),1)
                source=PianoStrings(20000,frequency,velocity=velocity)
                audio=source.render(4000,brightness=.78)
                self.assertTrue(np.isfinite(audio).all())
                self.assertGreater(np.std(audio),1e-8)
                self.assertAlmostEqual(source.frequencies[0]/frequency,2**((-2 if source.strings==3 else -1.5 if source.strings==2 else 0)/1200))
                self.assertTrue(np.all(source.amplitudes[source.frequencies>=source.bandlimit]==0))

    def test_measured_fundamental_survives_register_profile(self):
        for frequency in (65.4063913,261.625565,2093.00452):
            audio=PianoStrings(20000,frequency).render(40000,brightness=.78)
            f=np.fft.rfftfreq(len(audio),1/20000)
            power=abs(np.fft.rfft(audio*np.hanning(len(audio))))
            region=(f>frequency*.98)&(f<frequency*1.02)
            peak=f[region][np.argmax(power[region])]
            # Unison detune is intentionally up to +/-2 cents.
            self.assertLess(abs(peak-frequency),max(1.,frequency*.002))
