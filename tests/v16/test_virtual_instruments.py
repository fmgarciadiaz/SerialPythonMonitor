import unittest
import numpy as np
from dataclasses import replace
from monitor.v16.virtual_instruments import PianoStrings, InstrumentBody, GuitarStrings, warmup, modal_kernel
from monitor.v16.fm_source import FMSource, FMParameters
from monitor.v16.piano_profile import piano_profile

class PhysicalInstrumentTests(unittest.TestCase):
    def test_attack_filter_matches_scipy(self):
        from scipy.signal import sosfilt
        from monitor.v16.virtual_instruments import attack_filter_kernel,_attack_band
        signal=np.random.default_rng(81).normal(size=4800)
        for rate in (20000,40000):
            for low,high in ((100,400),(900,1800),(6000,8400)):
                coefficients=_attack_band(rate,low,high)
                np.testing.assert_allclose(attack_filter_kernel(coefficients,signal),sosfilt(coefficients,signal),rtol=1e-12,atol=1e-12)
    def test_prepare_audio_preserves_samples_and_position(self):
        params=FMParameters(waveform='virtual',virtual_model='piano',preset='Piano Virtual',notes=((60,100),))
        prepared=FMSource(20000,params);reference=FMSource(20000,params)
        prepared.prepare_audio();body=prepared.physical_body
        self.assertEqual(prepared.position,0)
        prepared.prepare_audio();self.assertIs(prepared.physical_body,body)
        np.testing.assert_array_equal(prepared[0:960],reference[0:960])
    def test_strain_filter_matches_scipy_across_block_boundaries(self):
        from scipy.signal import lfilter
        from monitor.v16.virtual_instruments import strain_kernel
        signal=np.random.default_rng(17).normal(size=2048)
        expected,state=lfilter([1,-1],[1,-.995],signal*signal,zi=[.17])
        previous=.17;blocks=[]
        for start,stop in ((0,1),(1,479),(479,960),(960,2048)):
            block,previous=strain_kernel(signal[start:stop],previous)
            blocks.append(block)
        np.testing.assert_allclose(np.concatenate(blocks),expected,rtol=0,atol=1e-12)
        self.assertAlmostEqual(previous,state[0],places=12)
    def setUp(self):
        if modal_kernel is None:self.skipTest('Numba no instalado')
        warmup()
    def test_piano_preset_keeps_audible_release_then_retires_voices(self):
        from monitor.v16.fm_source import PRESETS
        def release(envelope):
            params=FMParameters(preset='Piano Virtual',waveform='virtual',virtual_model='piano',
                                notes=((60,100),),envelope=envelope)
            source=FMSource(20000,params)
            source._render(slice(0,10000),quantize=False)
            source.update(replace(params,notes=()))
            tail=source._render(slice(10000,34000),quantize=False)
            self.assertFalse(source.voices)
            self.assertTrue(np.isfinite(tail).all())
            settled=source._render(slice(34000,90000),quantize=False)
            self.assertLess(np.max(abs(settled[-2000:])),1e-5)
            return tail
        old=release((.001,.01,1,.22))
        new=release(PRESETS['Piano Virtual'][2:6])
        self.assertGreater(np.linalg.norm(new[2000:4000]),np.linalg.norm(old[2000:4000])*2)
        self.assertLess(np.max(abs(new[-2000:])),2e-4)
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
            # Undamped treble strings now ring beyond the first second.
            impulse=np.zeros(120000);impulse[0]=1
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
        from monitor.v16.virtual_instruments import hammer_kernel
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
        from monitor.v16.virtual_instruments import hammer_kernel
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

    def test_reflected_hammer_contact_shortens_in_high_register(self):
        from monitor.v16.virtual_instruments import hammer_kernel
        durations=[]
        for note in (36,60,84,96,108):
            frequency=440*2**((note-69)/12)
            force=hammer_kernel(80000,1.,.78,frequency)
            significant=np.flatnonzero(force>force.max()*.001)
            durations.append((significant[-1]-significant[0]+1)/80000)
            self.assertTrue(np.isfinite(force).all())
            self.assertAlmostEqual(force.sum(),1)
        self.assertLess(durations[-1],.001)
        self.assertLess(durations[2],durations[1])

    def test_bass_uses_available_band_and_damper_reduces_tail(self):
        source=PianoStrings(20000,65.406)
        source.render(480)
        self.assertGreater(len(source.orders),64)
        self.assertTrue(np.all(source.frequencies<source.bandlimit))
        ringing=PianoStrings(20000,261.626)
        damped=PianoStrings(20000,261.626)
        ringing.render(4000);damped.render(4000)
        open_tail=ringing.render(4000)
        closed_tail=damped.render(4000,damper_t60=.1)
        self.assertLess(np.linalg.norm(closed_tail[-1000:]),np.linalg.norm(open_tail[-1000:])*.01)

    def test_native_piano_does_not_resample_and_handles_mixed_transitions(self):
        from unittest.mock import patch
        params=FMParameters(preset='Piano Virtual',waveform='virtual',virtual_model='piano',
                            notes=((60,110),(64,100)),envelope=(.001,.01,1,.1))
        source=FMSource(20000,params)
        with patch('monitor.v16.fm_source.sosfilt',side_effect=AssertionError('piano resampled')):
            native=source[0:480]
        self.assertTrue(np.isfinite(native).all())
        previous=native
        for at,mix,wave in ((480,.2,'virtual'),(960,0.,'virtual'),(1440,0.,'fm'),(1920,0.,'virtual'),(2400,0.,'virtual')):
            previous_route=source._last_native
            source.update(replace(params,osc2_mix=mix,waveform=wave))
            data=source[at:at+480]
            self.assertEqual(len(data),480)
            self.assertTrue(np.isfinite(data).all())
            if source._last_native!=previous_route:
                self.assertLess(abs(int(data[0])-int(previous[-1])),128)
            previous=data

    def test_native_damper_release_is_independent_of_block_size(self):
        params=FMParameters(preset='Piano Virtual',waveform='virtual',virtual_model='piano',
                            envelope=(.001,.01,1,.1))
        whole=FMSource(20000,params);chunks=FMSource(20000,params)
        whole[0:4000];chunks[0:4000]
        whole.update(replace(params,gate=False));chunks.update(replace(params,gate=False))
        expected=whole[4000:7000]
        parts=[]
        at=4000
        for size in (137,480,213,1000,1170):
            parts.append(chunks[at:at+size]);at+=size
        actual=np.concatenate(parts)
        self.assertGreater(np.std(expected[:1000]),1)
        self.assertLessEqual(np.max(abs(actual.astype(int)-expected.astype(int))),1)

    def test_shared_bridge_is_passive_and_preserves_differential_motion(self):
        from monitor.v16.virtual_instruments import bridge_unisons_kernel
        common=np.ones((6,2))
        differential=np.tile([[1.,-2.],[-1.,2.],[0.,0.]],(2,1))
        reference=differential.copy()
        loss=np.array([.3,.1])
        bridge_unisons_kernel(common,3,loss)
        bridge_unisons_kernel(differential,3,loss)
        self.assertLess(np.sum(common**2),12)
        np.testing.assert_array_equal(differential,reference)
        state=np.random.default_rng(12).normal(size=(120,2))
        energy=np.sum(state**2)
        bridge_unisons_kernel(state,3,np.linspace(.01,.9,40))
        self.assertLessEqual(np.sum(state**2),energy)

    def test_force_driven_impact_is_short_and_register_sensitive(self):
        from monitor.v16.virtual_instruments import hammer_impact
        soft=hammer_impact(20000,.25,.78,220.,.12)
        hard=hammer_impact(20000,1.,.78,220.,.12)
        self.assertTrue(np.isfinite(hard).all())
        self.assertGreater(np.linalg.norm(hard),np.linalg.norm(soft))
        self.assertLess(np.linalg.norm(hard[-100:]),np.linalg.norm(hard[:100])*.01)
        self.assertFalse(np.array_equal(hard,hammer_impact(20000,1.,.78,880.,.12)))
        for rate in (20000,40000):
            for note in range(24,109,12):
                impact=hammer_impact(rate,1.,.78,440*2**((note-69)/12),.12)
                self.assertLess(np.max(abs(impact)),.12)

    def test_motion_bridge_and_impact_survive_irregular_short_blocks(self):
        expected=PianoStrings(20000,261.626).render(4000)
        source=PianoStrings(20000,261.626)
        parts=[source.render(n) for n in (1,7,13,480,137,3362)]
        np.testing.assert_array_equal(expected,np.concatenate(parts))
