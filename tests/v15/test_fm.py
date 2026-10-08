import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from PyQt6 import QtWidgets
from monitor.v15.fm_source import FMSource,FMParameters
from monitor.v15.app import SerialMonitorWindow


class FMSourceTests(unittest.TestCase):
    def test_dx_14_ratio_attack_survives_output_band_limit(self):
        from dataclasses import replace
        params=FMParameters(carrier=440,modulator=440,index=0,osc2_wave='fm',
                            osc2_mix=1,osc2_fm_ratio=14,osc2_fm_amount=.55)
        source=FMSource(rate=20000,parameters=params)
        audio=source._render(slice(0,20000),quantize=False)
        spectrum=abs(np.fft.rfft(audio[2000:]*np.hanning(18000)))
        frequencies=np.fft.rfftfreq(18000,1/20000)
        metal=spectrum[(frequencies>5600)&(frequencies<6800)].max()
        fundamental=spectrum[(frequencies>430)&(frequencies<450)].max()
        self.assertGreater(metal/fundamental,.15)
        whole=FMSource(parameters=replace(params,preset='DX Piano',index=2,
                       osc2_mix=.25,bell_mix=.35,dx_body_detune=-7,envelope=(.003,3.4,0,.28)))
        chunked=FMSource(parameters=whole.parameters)
        expected=whole[0:4800]
        actual=np.concatenate([chunked[i:i+480] for i in range(0,4800,480)])
        self.assertLessEqual(np.max(abs(actual.astype(int)-expected.astype(int))),1)

    def test_piano_dx_velocity_changes_normalized_brightness(self):
        from dataclasses import replace
        params=FMParameters(carrier=440,modulator=440,index=1.6,preset='DX Piano',
                            bell_mix=.28,brightness_decay=.45,velocity_sensitivity=.8)
        def brightness(level):
            source=FMSource(parameters=replace(params,level=level))
            audio=source._render(slice(0,8000),quantize=False)[1000:5000]
            power=abs(np.fft.rfft(audio*np.hanning(len(audio))))**2
            frequencies=np.fft.rfftfreq(len(audio),1/source.rate)
            return power[frequencies>1000].sum()/power.sum()
        self.assertGreater(brightness(1),brightness(.25)*1.5)

    def test_midi_mix_uses_dac_range_with_soft_headroom(self):
        params=FMParameters(waveform='sine',notes=((69,127),),envelope=(.001,.001,1,.01))
        source=FMSource(parameters=params)
        volts=source.render_dac_codes(0,8000,3.3,1.65).astype(float)*3.3/4095
        self.assertGreaterEqual(volts.min(),.295)
        self.assertLessEqual(volts.max(),3.005)

    def test_synth_low_volume_is_linear_before_extreme_limiter(self):
        params=FMParameters(waveform='sine',notes=((69,127),),envelope=(.001,.001,1,.01))
        source=FMSource(parameters=params);reference=FMSource(parameters=params)
        expected=reference._render(slice(0,8000),quantize=False)*.5/2+1.65
        actual=source.render_dac_codes(0,8000,.5,1.65).astype(float)*3.3/4095
        self.assertLess(np.max(abs(actual-expected)),3.3/4095)

    def test_silent_pedal_voices_retire_without_restarting(self):
        from dataclasses import replace
        params=FMParameters(waveform='sine',notes=((60,100),),envelope=(.001,.01,0,.01))
        source=FMSource(rate=20000,parameters=params)
        source[0:1000]
        self.assertEqual(source.voices,{})
        self.assertIn(60,source.finished_notes)
        self.assertLess(np.max(abs(source[1000:1480].astype(float)-2047.5)),1)
        source.update(replace(params,note_id=1))
        source[1480:1960]
        self.assertEqual(source.finished_notes,{60})
        source.update(replace(params,notes=()))
        source[1960:2440]
        self.assertFalse(source.finished_notes)

    def test_compressor_gain_changes_gradually_and_recovers(self):
        from dataclasses import replace
        params=FMParameters(waveform='sine',notes=tuple((n,127) for n in range(60,69)),envelope=(.001,.001,1,.001))
        source=FMSource(rate=20000,parameters=params)
        source.render_dac_codes(0,480,3.3,1.65)
        self.assertGreater(source.compressor_gain,0)
        self.assertLess(source.compressor_gain,1)
        source.update(replace(params,notes=()))
        source.render_dac_codes(480,960,3.3,1.65)
        before=source.compressor_gain
        source.render_dac_codes(960,1440,3.3,1.65)
        self.assertGreater(source.compressor_gain,before)
        self.assertLess(source.compressor_gain,1)

    def test_piano_dx_high_notes_decay_faster(self):
        low=FMSource(parameters=FMParameters(carrier=220,modulator=220,preset='DX Piano',index=1.6))
        high=FMSource(parameters=FMParameters(carrier=880,modulator=880,preset='DX Piano',index=1.6))
        low[0:40000];high[0:40000]
        self.assertGreater(low.envelope_value,high.envelope_value)

    def test_piano_modulator_envelopes_are_independent_and_continuous(self):
        params=FMParameters(preset='DX Piano',bell_mix=.28,
                            fm_body_envelope=(.002,.01,1,.05),
                            fm_brightness_envelope=(.001,.01,0,.01))
        chunked=FMSource(parameters=params);whole=FMSource(parameters=params)
        audio=np.concatenate([chunked[i:i+480] for i in range(0,4800,480)])
        self.assertLessEqual(np.max(abs(audio.astype(int)-whole[0:4800].astype(int))),1)
        self.assertEqual(chunked.fm_states[0].envelope_value,1)
        self.assertEqual(chunked.fm_states[1].envelope_value,0)

    def test_unified_fm_adsr_is_rendered_once(self):
        envelope=(.003,1.2,.15,.18)
        source=FMSource(parameters=FMParameters(preset='DX Piano',bell_mix=.28,
            envelope=envelope,fm_body_envelope=envelope,fm_brightness_envelope=envelope))
        with patch.object(source,'_envelope',wraps=source._envelope) as render:
            source[0:480]
            self.assertEqual(render.call_count,1)
        for state in source.fm_states:
            self.assertEqual(state.envelope_value,source.envelope_value)

    def test_high_midi_note_does_not_change_existing_voice_timbre(self):
        from dataclasses import replace
        params=FMParameters(notes=((60,100),),note_ratio=1,note_index=3)
        source=FMSource(rate=20000,parameters=params);source[0:480]
        before=source.voices[60].parameters
        source.update(replace(params,carrier=7900,modulator=.1,index=0,notes=((60,100),(108,100)),note_id=1))
        source[480:960]
        after=source.voices[60].parameters
        self.assertEqual((before.modulator,before.index),(after.modulator,after.index))

    def test_low_queue_grows_once_per_episode(self):
        from types import SimpleNamespace as Status
        from monitor.v15.receiver.unoq_config_receiver import OutputReceiver
        source=FMSource(rate=20000)
        receiver=OutputReceiver(None,lambda batch:None)
        receiver.wav_codes=source;receiver.wav_session=1;receiver.wav_started=True
        receiver._wav_send=MagicMock()
        for rid,free,target in ((1,12,7),(2,13,7),(3,10,7),(4,12,9)):
            receiver.wav_status=Status(session=1,free_blocks=free,accepted=0,request_id=rid)
            receiver.service_wav()
            self.assertEqual(source.target_blocks,target)

    def test_shared_antialias_matches_sum_of_individual_filters_and_release(self):
        from dataclasses import replace
        params=FMParameters(waveform='sine',notes=((60,100),(64,80)),envelope=(.001,.003,.5,.004))
        mixed=FMSource(rate=20000,parameters=params)
        references=[]
        for note,velocity in params.notes:
            frequency=440*2**((note-69)/12)
            references.append(FMSource(rate=20000,parameters=replace(params,notes=None,
                carrier=frequency,modulator=frequency*.5,level=velocity/127)))
        for start in range(0,2400,480):
            if start==960:
                mixed.update(replace(params,notes=()))
                for source in references:source.update(replace(source.parameters,gate=False,level=0))
            actual=mixed._render(slice(start,start+480),quantize=False)
            expected=sum(source._render(slice(start,start+480),quantize=False) for source in references)*.9
            self.assertLess(np.max(abs(actual-expected)),1e-12)
        self.assertFalse(mixed.voices)

    def test_second_fm_oscillator_keeps_detune_and_chunk_continuity(self):
        params=FMParameters(waveform='sine',osc2_wave='fm',osc2_mix=.5,
                            osc2_fm_ratio=.5,osc2_fm_amount=2,osc2_detune=7)
        chunked=FMSource(parameters=params);whole=FMSource(parameters=params)
        audio=np.concatenate([chunked[i:i+480] for i in range(0,4800,480)])
        self.assertLessEqual(np.max(abs(audio.astype(int)-whole[0:4800].astype(int))),1)
        expected=4800*2*np.pi*440*2**(7/1200)/chunked.rate
        self.assertAlmostEqual(chunked.osc2_phase,expected%(2*np.pi),places=8)
        self.assertTrue(np.all(audio<=4095))

    def test_oscillators_have_independent_envelopes(self):
        from dataclasses import replace
        params=FMParameters(waveform='sine',osc2_wave='sine',osc2_mix=1,
                            envelope=(.001,.001,0,.01),osc2_envelope=(.001,.001,1,.1))
        source=FMSource(parameters=params)
        audio=source._render(slice(0,4000),quantize=False)
        self.assertGreater(np.sqrt(np.mean(audio[-1000:]**2)),.5)
        self.assertEqual(source.envelope_value,0)
        self.assertEqual(source.osc2_envelope_state.envelope_value,1)
        source.update(replace(params,gate=False))
        source[4000:6000]
        self.assertEqual(source.envelope_stage,'idle')
        self.assertEqual(source.osc2_envelope_state.envelope_stage,'release')
        with self.assertRaises(ValueError):source.update(replace(params,osc2_envelope=(0,1,1,1)))

    def test_chunking_preserves_phase_and_filter_state(self):
        source=FMSource();whole=FMSource()
        blocks=np.concatenate([source[i:i+480] for i in range(0,4800,480)])
        expected=whole[0:4800]
        self.assertLessEqual(np.max(abs(blocks.astype(int)-expected.astype(int))),1)
        self.assertLess(len(source),2**32)
        self.assertEqual(blocks.dtype,np.dtype('<u2'))
        self.assertTrue(np.all(blocks<=4095))

    def test_fm_has_carrier_and_sidebands(self):
        source=FMSource(parameters=FMParameters(4000,500,2))
        data=source[0:80000].astype(float)/2047.5-1
        spectrum=abs(np.fft.rfft(data[-40000:]))
        for frequency in (3000,3500,4000,4500,5000):
            self.assertGreater(spectrum[frequency],1000)

    def test_parameters_update_without_resetting_stream(self):
        source=FMSource();source[0:480]
        source.update(FMParameters(660,220,3,0))
        source[480:960];silence=source[960:1920]
        self.assertTrue(np.all(abs(silence[64:].astype(int)-2048)<=1))
        self.assertEqual(source.position,1920)
        with self.assertRaises(ValueError):source.update(FMParameters(10000,10000,20))
        with self.assertRaises(ValueError):source[0:480]

    def test_receiver_streams_lazy_source_with_existing_credit_protocol(self):
        from types import SimpleNamespace
        from monitor.v15.receiver.unoq_config_receiver import OutputReceiver
        import struct
        receiver=OutputReceiver(None,lambda batch:None)
        receiver.wav_candidate=True
        receiver.wav_status=SimpleNamespace(rates_mask=7)
        frames=[];receiver._wav_send=frames.append
        source=FMSource();receiver.set_wav_levels(2,1.65)
        receiver.wav_request(1,source,40000)
        self.assertEqual(struct.unpack_from('<I',frames[-1],24)[0],len(source))
        receiver.wav_status=SimpleNamespace(session=receiver.wav_session,free_blocks=16,accepted=0)
        receiver.service_wav()
        self.assertEqual(source.position,480)
        self.assertEqual(struct.unpack_from('<H',frames[-1],24)[0],480)
        codes=np.frombuffer(frames[-1],dtype='<u2',count=480,offset=28)
        self.assertTrue(np.all((codes>=806)&(codes<=3290)))
        receiver.wav_status.accepted=480;receiver.wav_status.free_blocks=15
        receiver.service_wav();self.assertEqual(source.position,960)

    def test_instrument_envelopes_and_release(self):
        from dataclasses import replace
        for preset in ('Flauta','Órgano','DX Brillo'):
            params=FMParameters(440,440,1,.8,preset,True,1)
            source=FMSource(parameters=params)
            data=source[0:160000].astype(float)-2047.5
            if preset=='DX Brillo':
                self.assertGreater(np.std(data[4000:8000]),100)
                self.assertLess(np.std(data[-4000:]),1)
            else:self.assertGreater(np.std(data[-4000:]),100)
            source.update(replace(params,gate=False,level=0))
            release=source[160000:184000].astype(float)-2047.5
            self.assertLess(np.max(abs(release[-1000:])),1)

    def test_shortening_envelope_mid_release_keeps_stream_alive(self):
        from dataclasses import replace
        params=FMParameters(440,440,1,.8,'DX Brillo')
        source=FMSource(parameters=params)
        source[0:4000]
        source.update(replace(params,gate=False))
        source[4000:8000]  # 100 ms into the original 350 ms release.
        source.update(replace(params,preset='Manual',gate=False))
        result=source[8000:10000]
        self.assertEqual(len(result),2000)
        self.assertLess(np.max(abs(result[-500:].astype(int)-2048)),2)
        source.update(replace(params,preset='Órgano',note_id=1))
        audible=source[10000:14000]
        self.assertGreater(np.std(audible[-1000:]),100)

    def test_live_envelope_edits_all_stages(self):
        from dataclasses import replace
        params=FMParameters(envelope=(.5,.5,.7,.5))
        source=FMSource(parameters=params)
        source[0:4000]
        source.update(replace(params,envelope=(.001,.001,.4,.001)))
        result=source[4000:8000]
        self.assertGreater(np.std(result[-1000:]),100)
        source.update(replace(params,gate=False,envelope=(.001,.001,.4,.5)))
        source[8000:12000]
        source.update(replace(params,gate=False,envelope=(.001,.001,.4,.001)))
        result=source[12000:14000]
        self.assertLess(np.max(abs(result[-500:].astype(int)-2048)),2)
        # Defensive transition even if elapsed position came from an old patch.
        source.envelope_stage='attack';source.envelope_position=100000
        self.assertTrue(np.all(source[14000:14480]<=4095))

    def test_nine_voices_release_and_stealing(self):
        from dataclasses import replace
        params=FMParameters(index=0,notes=tuple((n,100) for n in (40,43,48,52,55,60,64,67,72)))
        source=FMSource(parameters=params)
        result=source[0:20000]
        self.assertEqual(len(source.voices),9)
        spectrum=abs(np.fft.rfft(result[-16000:].astype(float)-2047.5))
        for note in (60,64,67,72):
            bin_index=round(440*2**((note-69)/12)/2.5)
            self.assertGreater(max(spectrum[bin_index-1:bin_index+2]),10000)
        source.update(replace(params,notes=tuple((n,100) for n in (43,48,52,55,60,64,67,72,76))))
        source[20000:20480]
        self.assertEqual(set(source.voices),{43,48,52,55,60,64,67,72,76})
        source.update(replace(params,notes=()))
        silent=source[20480:24480]
        self.assertFalse(source.voices)
        self.assertLess(np.max(abs(silent[-500:].astype(int)-2048)),2)

    def test_fm_refills_when_only_six_blocks_remain(self):
        from types import SimpleNamespace
        from monitor.v15.receiver.unoq_config_receiver import OutputReceiver
        receiver=OutputReceiver(None,lambda batch:None)
        source=FMSource();receiver.wav_codes=source;receiver.wav_session=123;receiver.wav_started=True
        receiver.wav_status=SimpleNamespace(session=123,free_blocks=10,accepted=0)
        sent=[];receiver._wav_send=sent.append
        receiver.service_wav()
        self.assertEqual(source.position,480);self.assertEqual(len(sent),1)

    def test_usb_commands_disable_nagle(self):
        import socket
        from monitor.v15.receiver.unoq_usb import Connection
        with patch('monitor.v15.receiver.unoq_usb.usb_devices',return_value=['q']), \
             patch('monitor.v15.receiver.unoq_usb.adb',side_effect=['','12345']), \
             patch('monitor.v15.receiver.unoq_usb.socket.create_connection') as connect:
            connection=Connection('q');connection.open()
            connect.return_value.setsockopt.assert_called_once_with(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)

    def test_piano_dx_pair_chunk_continuity_and_editing(self):
        params=FMParameters(preset='DX Piano',bell_mix=.35)
        source=FMSource(parameters=params);whole=FMSource(parameters=params)
        chunks=np.concatenate([source[i:i+480] for i in range(0,4800,480)])
        expected=whole[0:4800]
        self.assertLessEqual(np.max(abs(chunks.astype(int)-expected.astype(int))),1)

    def test_piano_dx_metallic_attack_decays_independently(self):
        from dataclasses import replace
        params=FMParameters(preset='DX Piano',bell_mix=.35,
                            brightness_decay=.2,envelope=(.001,.01,1,.1))
        mixed=FMSource(parameters=params)
        body=FMSource(parameters=replace(params,bell_mix=0))
        audio=mixed._render(slice(0,80000),quantize=False)
        baseline=body._render(slice(0,80000),quantize=False)
        tine=audio-.65*baseline
        early=np.sqrt(np.mean(tine[1000:3000]**2))
        late=np.sqrt(np.mean(tine[-4000:]**2))
        self.assertGreater(early,.01)
        self.assertLess(late,early*.01)

    def test_fm_fills_complete_queue_before_starting(self):
        from types import SimpleNamespace
        from monitor.v15.receiver.unoq_config_receiver import OutputReceiver
        receiver=OutputReceiver(None,lambda batch:None)
        source=FMSource();receiver.wav_codes=source;receiver.wav_session=123
        receiver.wav_status=SimpleNamespace(session=123,free_blocks=0,accepted=7680)
        sent=[];receiver._wav_send=sent.append
        receiver.service_wav()
        self.assertTrue(receiver.wav_started);self.assertEqual(len(sent),1)
        receiver.wav_poll_at=float('inf');receiver.service_wav()
        self.assertEqual(len(sent),1)
        self.assertEqual(source.position,0)

    def test_waveforms_have_expected_spectra_and_chunk_continuity(self):
        for wave in ('sine','square','triangle','saw'):
            params=FMParameters(carrier=500,waveform=wave)
            source=FMSource(parameters=params);whole=FMSource(parameters=params)
            chunked=np.concatenate([source[i:i+480] for i in range(0,4800,480)])
            expected=whole[0:4800]
            self.assertLessEqual(np.max(abs(chunked.astype(int)-expected.astype(int))),1)
            source=FMSource(parameters=params)
            data=source[0:80000].astype(float)-2047.5
            spectrum=abs(np.fft.rfft(data[-40000:]))
            self.assertGreater(spectrum[500],10000)
            if wave=='sine':self.assertLess(spectrum[1500],spectrum[500]*.001)
            elif wave=='triangle':self.assertAlmostEqual(spectrum[1500]/spectrum[500],1/9,delta=.02)
            elif wave=='square':self.assertAlmostEqual(spectrum[1500]/spectrum[500],1/3,delta=.02)
            else:self.assertAlmostEqual(spectrum[1000]/spectrum[500],.5,delta=.02)

    def test_live_sound_changes_keep_four_voice_stream_running(self):
        from dataclasses import replace
        params=FMParameters(notes=((60,100),(64,100),(67,100),(72,100)))
        source=FMSource(rate=20000,parameters=params)
        position=0
        for wave in ('fm','saw','square','triangle','sine','fm'):
            source.update(replace(params,waveform=wave))
            data=source[position:position+480];position+=480
            self.assertEqual(len(source.voices),4)
            self.assertTrue(np.all(data<=4095))

    def test_filter_modes_have_expected_frequency_response(self):
        for mode in ('lowpass','highpass','bandpass','notch'):
            params=FMParameters(filter_type=mode,cutoff=1000)
            source=FMSource(rate=20000,parameters=params)
            t=np.arange(40000)/20000
            signal=.1*(np.sin(2*np.pi*200*t)+np.sin(2*np.pi*1000*t)+np.sin(2*np.pi*4000*t))
            output=np.concatenate([source._filter_audio(signal[i:i+480],params) for i in range(0,40000,480)])
            spectrum=abs(np.fft.rfft(output[-20000:]))
            if mode=='lowpass':self.assertLess(spectrum[4000]/spectrum[200],.1)
            elif mode=='highpass':self.assertLess(spectrum[200]/spectrum[4000],.1)
            elif mode=='bandpass':self.assertGreater(spectrum[1000]/spectrum[4000],3)
            else:self.assertLess(spectrum[1000]/spectrum[4000],.01)

    def test_filter_edits_and_bypass_stay_finite_with_four_voices(self):
        from dataclasses import replace
        params=FMParameters(waveform='saw',notes=((60,100),(64,100),(67,100),(72,100)))
        source=FMSource(rate=20000,parameters=params);position=0
        for mode,cutoff,q in (('lowpass',20,8),('highpass',9000,8),('bandpass',1000,8),
                              ('notch',50,.5),('off',2000,.7)):
            source.update(replace(params,filter_type=mode,cutoff=cutoff,resonance=q,drive=3))
            for _ in range(5):
                data=source[position:position+480];position+=480
                self.assertTrue(np.all(data<=4095));self.assertTrue(np.all(np.isfinite(source.filter_zi)))
            self.assertEqual(len(source.voices),4)
        self.assertEqual(len(source[position:position]),0)

    def test_diagnostic_ack_gap_excludes_idle_time(self):
        from types import SimpleNamespace
        source=FMSource()
        status=SimpleNamespace(state=2,free_blocks=8,reason=0)
        with patch('monitor.v15.fm_source.time.monotonic',return_value=100):source.observe_status(status)
        with patch('monitor.v15.fm_source.time.monotonic',return_value=100.05):source.observe_status(status)
        status.state=0
        with patch('monitor.v15.fm_source.time.monotonic',return_value=200):source.observe_status(status)
        self.assertAlmostEqual(source._max_ack_gap,.05)
        self.assertIsNone(source._last_ack)

    def test_steady_voices_share_coefficients_and_skip_parameter_validation(self):
        params=FMParameters(notes=((60,100),(64,100)))
        source=FMSource(parameters=params);source[0:480]
        first,second=source.voices.values()
        self.assertIs(first.sos,second.sos)
        self.assertIsNot(first.zi,second.zi)
        with patch.object(first,'update',wraps=first.update) as update:
            source[480:960]
            update.assert_not_called()
        self.assertEqual(first.position,960)

    def test_synth_pipeline_reserves_two_credits_and_advances_on_ack(self):
        from types import SimpleNamespace
        import struct
        from monitor.v15.receiver.unoq_config_receiver import OutputReceiver
        socket=MagicMock();connection=SimpleNamespace(socket=socket,read=lambda:b'')
        receiver=OutputReceiver(connection,lambda batch:None)
        receiver.wav_candidate=True
        receiver.wav_codes=FMSource(rate=20000);receiver.wav_session=123;receiver.wav_started=True
        receiver.wav_status=SimpleNamespace(session=123,free_blocks=16,accepted=0)
        receiver.service_wav();receiver.service_wav();receiver.service_wav()
        self.assertEqual(len(receiver.wav_inflight),2)
        self.assertEqual(receiver.wav_codes.position,960)
        self.assertEqual(receiver.wav_codes.target_blocks,7)
        frames=[call.args[0] for call in socket.sendall.call_args_list]
        self.assertEqual([struct.unpack_from('<I',f,20)[0] for f in frames],[0,480])
        first_id=struct.unpack_from('<I',frames[0],8)[0]
        receiver.decoder=MagicMock()
        receiver.decoder.events=[('wav',SimpleNamespace(request_id=first_id,session=123,rate=20000,
                                 reason=0,state=2,accepted=480,free_blocks=15))]
        receiver.pump()
        self.assertEqual(len(receiver.wav_inflight),2)
        self.assertEqual(receiver.wav_codes.position,1440)
        self.assertEqual(struct.unpack_from('<I',socket.sendall.call_args.args[0],20)[0],960)
        receiver.wav_request(3)
        self.assertEqual(len(receiver.wav_inflight),1)
        receiver.pump() # Old ACK cannot supersede STOP.
        self.assertEqual(len(receiver.wav_inflight),1)

    def test_file_wav_does_not_pipeline(self):
        from types import SimpleNamespace
        from monitor.v15.receiver.unoq_config_receiver import OutputReceiver
        socket=MagicMock();receiver=OutputReceiver(SimpleNamespace(socket=socket),lambda batch:None)
        receiver.wav_codes=np.zeros(4800,dtype='<u2');receiver.wav_session=123;receiver.wav_started=True
        receiver.wav_status=SimpleNamespace(session=123,free_blocks=16,accepted=0)
        receiver.service_wav();receiver.service_wav()
        self.assertEqual(len(receiver.wav_inflight),1)
        socket.sendall.assert_called_once()

    def test_detuned_second_oscillator_has_two_distinct_tones(self):
        params=FMParameters(waveform='sine',osc2_wave='sine',osc2_mix=.5,osc2_detune=10)
        source=FMSource(rate=20000,parameters=params)
        data=source[0:100000].astype(float)-2047.5
        spectrum=abs(np.fft.rfft(data[-80000:]))
        second=440*2**(10/1200)
        for freq in (440,second):
            bin_index=round(freq/.25)
            self.assertGreater(max(spectrum[bin_index-1:bin_index+2]),1e7)

    def test_second_oscillator_chunk_continuity(self):
        params=FMParameters(waveform='saw',osc2_wave='square',osc2_mix=.3,osc2_detune=7)
        source=FMSource(parameters=params);whole=FMSource(parameters=params)
        chunks=np.concatenate([source[i:i+480] for i in range(0,4800,480)])
        self.assertLessEqual(np.max(abs(chunks.astype(int)-whole[0:4800].astype(int))),1)


class FMPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def setUp(self):
        with patch('monitor.v15.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()
    def tearDown(self):self.w.close()

    def test_fm_isolated_layout_and_start_stop(self):
        w=self.w;w.generator_mode.setCurrentIndex(5);w.show();self.app.processEvents()
        self.assertTrue(w.fm_panel.isVisible())
        self.assertFalse(w.generator_enabled.isVisible())
        self.assertEqual(w._generator_config().enabled,0)
        worker=MagicMock();w.serial_worker=worker;w._wav_capable=True
        w.wav_rate.model().item(w.wav_rate.findData(20000)).setEnabled(True)
        w.fm_panel.toggle()
        args=worker.request_wav.call_args.args
        self.assertEqual((args[0],args[2]),(1,20000));self.assertIsInstance(args[1],FMSource)
        w.fm_panel.controls[0].setValue(660)
        self.assertEqual(w.fm_panel.source.parameters.carrier,660)
        w.fm_panel.toggle();worker.request_wav.assert_called_with(3)
        w.generator_mode.setCurrentIndex(0);self.app.processEvents()
        self.assertFalse(w.fm_panel.isVisible());self.assertTrue(w.generator_amplitude.isVisible())
        self.assertTrue(w._generator_labels[w.generator_amplitude].isVisible())

    def test_midi_note_and_note_off(self):
        from types import SimpleNamespace
        panel=self.w.fm_panel;self.w.generator_mode.setCurrentIndex(5)
        self.w.serial_worker=MagicMock();panel.source=FMSource()
        panel.midi_input.addItem('test');panel.midi_input.blockSignals(True);panel.midi_input.setCurrentIndex(1);panel.midi_input.blockSignals(False)
        panel.midi=MagicMock();panel.midi.iter_pending.return_value=[SimpleNamespace(type='note_on',note=69,velocity=100)]
        panel.poll_midi()
        self.assertEqual(panel.source.parameters.carrier,440)
        self.assertAlmostEqual(panel.source.parameters.level,100/127)
        panel.midi.iter_pending.return_value=[SimpleNamespace(type='note_off',note=69)]
        panel.poll_midi();self.assertEqual(panel.source.parameters.level,0)
        self.assertFalse(panel.source.parameters.gate)
        self.assertEqual(panel.velocity_label.text(),'Velocidad · 100')

    def test_pedal_note_history_stays_bounded(self):
        from types import SimpleNamespace as Msg
        panel=self.w.fm_panel;panel.midi=MagicMock()
        messages=[Msg(type='control_change',control=64,value=127)]
        for note in range(40,80):
            messages.extend((Msg(type='note_on',note=note,velocity=100),Msg(type='note_off',note=note)))
        panel.midi.iter_pending.return_value=messages;panel.poll_midi()
        self.assertEqual(len(panel.notes),9)
        self.assertEqual([n for n,v in panel.notes],list(range(71,80)))
        panel.midi.iter_pending.return_value=[Msg(type='control_change',control=64,value=0)]
        panel.poll_midi();self.assertFalse(panel.notes)

    def test_sustain_pedal_holds_and_releases_notes(self):
        from types import SimpleNamespace as Msg
        panel=self.w.fm_panel
        panel.midi=MagicMock()
        def send(*messages):
            panel.midi.iter_pending.return_value=messages
            panel.poll_midi()
        send(Msg(type='note_on',note=60,velocity=100),
             Msg(type='control_change',control=64,value=127),
             Msg(type='note_off',note=60))
        self.assertEqual(panel.notes,[(60,100)])
        send(Msg(type='note_on',note=64,velocity=80),
             Msg(type='control_change',control=64,value=0))
        self.assertEqual(panel.notes,[(64,80)])
        send(Msg(type='control_change',control=120,value=0))
        self.assertEqual(panel.notes,[])
        self.assertFalse(panel.sustain_pedal)
        self.assertEqual(panel.pressed_notes,set())

    def test_preset_tracks_midi_pitch_and_velocity(self):
        from types import SimpleNamespace
        panel=self.w.fm_panel;panel.preset.setCurrentText('DX Brillo')
        panel.source=FMSource();self.w.serial_worker=MagicMock()
        panel.midi_input.blockSignals(True);panel.midi_input.addItem('test');panel.midi_input.setCurrentIndex(1);panel.midi_input.blockSignals(False)
        panel.midi=MagicMock();panel.midi.iter_pending.return_value=[SimpleNamespace(type='note_on',note=81,velocity=40)]
        panel.poll_midi()
        params=panel.source.parameters
        self.assertEqual((params.carrier,params.modulator,params.preset),(880,880,'DX Brillo'))
        self.assertAlmostEqual(params.level,40/127)
        panel.midi.iter_pending.return_value=[SimpleNamespace(type='note_on',note=108,velocity=127)]
        panel.poll_midi()
        self.assertLessEqual(panel.source.parameters.carrier+(panel.source.parameters.index+1)*panel.source.parameters.modulator,16000.01)

    def test_dials_update_ratio_and_envelope_during_play(self):
        panel=self.w.fm_panel;panel.source=FMSource();self.w.serial_worker=MagicMock()
        panel.ratio.setValue(2)
        self.assertEqual(panel.source.parameters.modulator,880)
        panel.envelope_controls[3].setValue(100)
        self.assertEqual(panel.source.parameters.envelope[3],.1)
        panel.dials[2].setValue(350)
        self.assertEqual(panel.source.parameters.index,3.5)
        panel.preset.setCurrentText('DX Brillo')
        self.assertEqual(panel.envelope_controls[1].value(),2800)
        from PyQt6 import QtCore
        self.w.generator_mode.setCurrentIndex(5);self.w.show();self.app.processEvents()
        for tab in range(panel.tabs.count()):
            panel.tabs.setCurrentIndex(tab);self.app.processEvents()
            viewport=panel.parentWidget().parentWidget()
            bottom=panel.info.mapTo(viewport,QtCore.QPoint(0,panel.info.height())).y()
            self.assertLessEqual(bottom,viewport.height())

    def test_midi_chord_and_manual_high_notes(self):
        from types import SimpleNamespace
        panel=self.w.fm_panel;panel.source=FMSource();self.w.serial_worker=MagicMock()
        panel.midi_input.blockSignals(True);panel.midi_input.addItem('test');panel.midi_input.setCurrentIndex(1);panel.midi_input.blockSignals(False)
        panel.midi=MagicMock()
        panel.midi.iter_pending.return_value=[SimpleNamespace(type='note_on',note=n,velocity=100) for n in (60,64,67,72,76)]
        panel.poll_midi()
        self.assertEqual(tuple(n for n,v in panel.source.parameters.notes),(60,64,67,72,76))
        self.assertEqual(len(panel.source[0:480]),480)
        panel.midi.iter_pending.return_value=[SimpleNamespace(type='note_on',note=127,velocity=100)]
        panel.poll_midi()
        self.assertEqual(len(panel.source[480:960]),480)

    def test_editor_selector_icons_and_low_rate_polyphony(self):
        from dataclasses import replace
        panel=self.w.fm_panel
        self.assertEqual(panel.output_rate.currentData(),20000)
        for index in range(5):
            self.assertFalse(panel.editor_mode.itemIcon(index).isNull())
            panel.editor_mode.setCurrentIndex(index)
            self.assertEqual(panel.tabs.currentIndex(),index)
        panel.preset.setCurrentText('DX Piano')
        params=replace(panel.parameters(),notes=((60,100),(64,100),(67,100),(127,100)))
        source=FMSource(rate=20000,parameters=params)
        for start in range(0,20000,480):
            end=min(start+480,20000)
            self.assertEqual(len(source[start:end]),end-start)
        self.assertEqual(len(source.voices),4)

    def test_fm_editor_sits_beside_mode(self):
        panel=self.w.fm_panel;self.w.generator_mode.setCurrentIndex(5)
        grid=self.w.generator_panel.layout()
        self.assertEqual(grid.getItemPosition(grid.indexOf(panel.editor_mode)),(1,1,1,1))
        self.assertIs(grid.itemAtPosition(1,0).widget(),self.w.generator_mode)
        self.w.generator_mode.setCurrentIndex(0)
        self.assertTrue(panel.editor_mode.isHidden())

    def test_low_rate_queue_grows_when_running_low(self):
        from types import SimpleNamespace
        from monitor.v15.receiver.unoq_config_receiver import OutputReceiver
        source=FMSource(rate=20000);self.assertEqual(source.target_blocks,5)
        receiver=OutputReceiver(None,lambda batch:None)
        receiver.wav_codes=source;receiver.wav_session=1;receiver.wav_started=True
        receiver.wav_status=SimpleNamespace(session=1,free_blocks=12,accepted=0)
        receiver._wav_send=MagicMock();receiver.service_wav()
        self.assertEqual(source.target_blocks,7)
        self.assertEqual(source.position,480)

    def test_dx_presets_use_two_editable_fm_blocks(self):
        panel=self.w.fm_panel
        for name,mix,ratio,amount in (('DX Piano',.25,14,.55),('DX Brillo',.42,14,1.35)):
            panel.apply_preset(name)
            params=panel.parameters()
            self.assertEqual((params.waveform,params.osc2_wave),('fm','fm'))
            self.assertEqual(params.osc2_mix,mix)
            self.assertEqual((params.osc2_fm_ratio,params.osc2_fm_amount),(ratio,amount))
            self.assertEqual(params.bell_mix,0)
            self.assertGreater(params.osc3_mix,0)
            self.assertEqual(params.osc2_octave,0)
            self.assertIsNone(params.dx_body_detune)
            self.assertNotEqual(params.envelope,params.osc2_envelope)
            panel.osc2_detune.setValue(5)
            self.assertEqual(panel.parameters().osc2_detune,5)
            source=FMSource(rate=20000,parameters=panel.parameters())
            self.assertEqual(len(source[0:480]),480)

    def test_synth_waveform_selector_disables_fm_only_controls(self):
        panel=self.w.fm_panel
        self.assertEqual(self.w.generator_mode.itemText(5),'Synth')
        panel.waveform.setCurrentIndex(panel.waveform.findData('saw'))
        self.assertFalse(panel.ratio.isEnabled());self.assertFalse(panel.controls[2].isEnabled())
        self.assertTrue(panel.controls[0].isEnabled());self.assertTrue(panel.controls[3].isEnabled())
        self.assertEqual(panel.parameters().waveform,'saw')
        panel.preset.setCurrentText('Manual')
        panel.preset.setCurrentText('DX Piano')
        self.assertEqual(panel.waveform.currentData(),'fm');self.assertTrue(panel.ratio.isEnabled())

    def test_subtractive_presets_load_editable_wave_envelope_filter(self):
        from monitor.v15.fm_source import SYNTH_PATCHES
        panel=self.w.fm_panel
        self.assertEqual(panel.editor_mode.itemText(5),'Filtros')
        self.assertFalse(panel.editor_mode.itemIcon(4).isNull())
        for name,patch in SYNTH_PATCHES.items():
            panel.preset.setCurrentText(name)
            params=panel.parameters()
            self.assertEqual(params.waveform,patch[0]);self.assertEqual(params.filter_type,'lowpass')
            self.assertEqual(params.cutoff,patch[1]);self.assertAlmostEqual(params.resonance,patch[2])
            self.assertTrue(panel.filter_controls[0].isEnabled())
            source=FMSource(rate=20000,parameters=params)
            self.assertEqual(len(source[0:480]),480)
        panel.filter_controls[0].setValue(1234)
        self.assertEqual(panel.parameters().cutoff,1234)
        panel.filter_type.setCurrentIndex(0)
        self.assertFalse(panel.filter_controls[0].isEnabled())

    def test_stable_interval_does_not_shrink_live_queue(self):
        from types import SimpleNamespace
        from monitor.v15.receiver.unoq_config_receiver import OutputReceiver
        source=FMSource(rate=20000);source.target_blocks=10
        receiver=OutputReceiver(None,lambda batch:None)
        receiver.wav_codes=source;receiver.wav_session=1;receiver.wav_started=True
        receiver.wav_buffer_adjust_at=100;receiver.wav_poll_at=float('inf')
        receiver.wav_status=SimpleNamespace(session=1,free_blocks=6,accepted=0)
        receiver._wav_send=MagicMock()
        with patch('monitor.v15.receiver.unoq_config_receiver.time.monotonic',return_value=1000):receiver.service_wav()
        self.assertEqual(source.target_blocks,10)
        receiver._wav_send.assert_not_called()

    def test_eight_midi_voices_and_instrument_icons(self):
        from types import SimpleNamespace
        panel=self.w.fm_panel;panel.source=FMSource(rate=20000);self.w.serial_worker=MagicMock()
        panel.midi_input.blockSignals(True);panel.midi_input.addItem('test');panel.midi_input.setCurrentIndex(1);panel.midi_input.blockSignals(False)
        panel.midi=MagicMock()
        panel.midi.iter_pending.return_value=[SimpleNamespace(type='note_on',note=n,velocity=100) for n in (43,48,52,55,60,64,67,72,76)]
        panel.poll_midi();panel.source[0:480]
        self.assertEqual(tuple(n for n,v in panel.source.parameters.notes),(43,48,52,55,60,64,67,72,76))
        self.assertEqual(len(panel.source.voices),9)
        for index in range(panel.preset.count()):self.assertFalse(panel.preset.itemIcon(index).isNull())

    def test_eight_voices_and_equal_generator_columns(self):
        from dataclasses import replace
        panel=self.w.fm_panel
        notes=tuple((n,100) for n in (43,48,52,55,60,64,67,72))
        source=FMSource(rate=40000,parameters=replace(panel.parameters(),notes=notes))
        self.assertEqual(source.minimum_blocks,16)
        self.assertEqual(len(source[0:480]),480);self.assertEqual(len(source.voices),8)
        self.w.generator_mode.setCurrentIndex(5);self.w.show();self.app.processEvents()
        self.assertLessEqual(abs(self.w.generator_mode.width()-panel.editor_mode.width()),1)
        self.assertLessEqual(abs(panel.waveform.width()-panel.preset.width()),1)

    def test_second_oscillator_editor_and_preset_settings(self):
        panel=self.w.fm_panel
        self.assertEqual(panel.editor_mode.itemText(1),'Osc 2')
        panel.preset.setCurrentText('Warm Pad')
        params=panel.parameters()
        self.assertEqual((params.osc2_detune,params.osc2_mix,params.osc2_octave),(10,.5,0))
        panel.preset.setCurrentText('Bass Punch')
        self.assertEqual(panel.parameters().osc2_octave,-1)
        panel.osc2_detune.setValue(-7)
        self.assertEqual(panel.parameters().osc2_detune,-7)
