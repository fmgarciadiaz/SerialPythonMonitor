import json
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import nullcontext
from unittest.mock import Mock,patch
from tools import private_firmware_v19 as binding
from tools.probe_prepare_firmware_v19 import activate
from monitor.v19.q_support.backend import APP


ACCEPTED=dict(firmware_sha256='b'*64,relay_sha256='c'*64)
PRIVATE=dict(board_serial='test',app='scope-v19-main-1',firmware_sha256='d'*64,relay_sha256='c'*64)
CANDIDATE=dict(source='private.ino',source_sha256='e'*64,firmware_sha256='d'*64,elf_sha256='f'*64,relay_sha256='c'*64)


class PrivateFirmwareTests(unittest.TestCase):
    def test_timing_binding_accepts_only_exact_three_file_schema(self):
        from tools.wav_timing_candidate_v19 import accepted_sources,candidate_sources,SCHEMA
        originals=accepted_sources();generated=candidate_sources(originals)
        digest=lambda b:hashlib.sha256(b).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();sketch=root/'arduino/v19/oscilloscope/sketch'
            sketch.mkdir(parents=True)
            for name,text in originals.items():(sketch/name).write_text(text)
            folder=root/'diagnosticos/resultados_v19/timing';folder.mkdir(parents=True)
            variants={}
            for name,files in [('control_os',originals),('candidate_wav_timing',generated)]:
                target=folder/name;(target/'build').mkdir(parents=True);variants[name]={}
                for filename,text in files.items():(target/filename).write_text(text)
                for kind in ('bin','elf'):
                    data=(name+kind).encode();(target/'build'/('sketch.ino.'+kind)).write_bytes(data)
                    variants[name][kind+'_sha256']=digest(data)
            report=dict(ok=True,restoration=dict(ok=True),artifact=dict(diagnostic_schema=SCHEMA,
                compiled_with_pair_stopped=True,firmware_installed=False,
                sources={p.name:digest(p.read_bytes()) for p in sketch.iterdir()},variants=variants))
            path=folder/'report.json';path.write_text(json.dumps(report))
            accepted=dict(ACCEPTED,firmware_sha256=variants['control_os']['bin_sha256'])
            with patch.object(binding,'ROOT',root),patch.object(binding,'accepted_identity',return_value=accepted):
                selected=binding.checked_firmware(path)
                self.assertEqual(set(selected['source_files']),set(originals))
                self.assertEqual(selected['diagnostic_schema'],SCHEMA)
                for filename in originals:
                    target=folder/'candidate_wav_timing'/filename;before=target.read_bytes()
                    target.write_bytes(before+b' ')
                    with self.assertRaises(ValueError):binding.checked_firmware(path)
                    target.write_bytes(before)
                report['artifact']['diagnostic_schema']='unknown';path.write_text(json.dumps(report))
                with self.assertRaises(ValueError):binding.checked_firmware(path)

    def test_timing_activation_requires_full_specific_source_set(self):
        from tools.wav_timing_candidate_v19 import SCHEMA
        backend,acceptance,journal=self.backend()
        files={n:dict(path='private-'+n,sha256='e'*64) for n in ('sketch.ino','wav.h','wav_dma.h')}
        selected=dict(CANDIDATE,source_files=files,diagnostic_schema=SCHEMA)
        backend._sources.return_value=dict(acceptance['sources']['app'],
                                          **{'sketch/'+n:'e'*64 for n in files})
        activate(backend,acceptance,selected,{},journal)
        for n in files:backend._board().run.assert_any_call('push','private-'+n,APP+'/sketch/'+n)
        backend,acceptance,journal=self.backend()
        with self.assertRaises(ValueError):activate(backend,acceptance,dict(selected,source_files={}),{},journal)
        backend._board().run.assert_not_called()

    def test_exact_wav_binding_rejects_header_sketch_and_binary_tampering(self):
        from tools.wav_validation_candidate_v19 import candidate_text,SKETCH
        original=(SKETCH/'wav.h').read_text()
        ino=(SKETCH/'sketch.ino').read_text()
        digest=lambda b:hashlib.sha256(b).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();sketch=root/'arduino/v19/oscilloscope/sketch'
            sketch.mkdir(parents=True)
            (sketch/'wav.h').write_text(original);(sketch/'sketch.ino').write_text(ino)
            folder=root/'diagnosticos/resultados_v19/experiment';folder.mkdir(parents=True)
            variants={}
            for name in ('control_os','candidate_wav_validation'):
                target=folder/name;(target/'build').mkdir(parents=True)
                (target/'sketch.ino').write_text(ino)
                (target/'wav.h').write_text(original if name=='control_os' else candidate_text(original))
                variants[name]={}
                for kind in ('bin','elf'):
                    data=(name+kind).encode();(target/'build'/('sketch.ino.'+kind)).write_bytes(data)
                    variants[name][kind+'_sha256']=digest(data)
            sources={p.name:digest(p.read_bytes()) for p in sketch.iterdir()}
            report=dict(ok=True,restoration=dict(ok=True),artifact=dict(
                compiled_with_pair_stopped=True,firmware_installed=False,sources=sources,variants=variants))
            path=folder/'report.json';path.write_text(json.dumps(report))
            accepted=dict(ACCEPTED,firmware_sha256=variants['control_os']['bin_sha256'])
            with patch.object(binding,'ROOT',root),patch.object(binding,'accepted_identity',return_value=accepted):
                self.assertEqual(binding.checked_firmware(path)['source_relative'],'wav.h')
                for relative in ('candidate_wav_validation/wav.h','candidate_wav_validation/sketch.ino',
                                 'control_os/wav.h','candidate_wav_validation/build/sketch.ino.bin'):
                    target=folder/relative;before=target.read_bytes();target.write_bytes(before+b' ')
                    with self.subTest(relative=relative),self.assertRaises(ValueError):binding.checked_firmware(path)
                    target.write_bytes(before)

    def test_wav_header_activation_preserves_main_sketch_manifest(self):
        backend,acceptance,journal=self.backend()
        selected=dict(CANDIDATE,source='private-wav.h',source_relative='wav.h')
        backend._sources.return_value=dict(acceptance['sources']['app'],
                                          **{'sketch/wav.h':selected['source_sha256']})
        activate(backend,acceptance,selected,{},journal)
        backend._board().run.assert_any_call('push','private-wav.h',APP+'/sketch/wav.h')
        private=backend.verify_new.call_args.args[1]
        self.assertEqual(private['sources']['app']['sketch/sketch.ino'],'b'*64)
        self.assertNotIn('sketch/wav.h',acceptance['sources']['app'])

    def test_unknown_source_is_rejected_before_any_push(self):
        backend,acceptance,journal=self.backend()
        with self.assertRaisesRegex(ValueError,'Unknown reviewed'):
            activate(backend,acceptance,dict(CANDIDATE,source_relative='../other.h'),{},journal)
        backend._board().run.assert_not_called()

    def test_play_arm_must_match_explicit_binding_declaration(self):
        from tools.radio_burst_inline_v19 import ENV as BURST_ENV,STARTUP_ENV,PLAY_ENV
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'report.json';path.write_text('{"private_play_burst":1}')
            with patch.dict(os.environ,{binding.ENV:str(path),BURST_ENV:'1',STARTUP_ENV:'1',PLAY_ENV:'1'},clear=True), \
                 patch.object(binding,'installed_connection',return_value=nullcontext(object())), \
                 patch('tools.radio_burst_inline_v19.inline_burst',return_value=nullcontext()) as selected:
                with binding.private_connection('test'):pass
                selected.assert_called_once_with(1,None,True,play_burst=1)
                path.write_text('{}')
                with self.assertRaisesRegex(RuntimeError,'PLAY burst differs'):
                    with binding.private_connection('test'):pass

    def test_ipc_combination_requires_matching_declaration_and_preserves_context(self):
        from tools.ipc_empty_backoff_v19 import ENV as IPC_ENV
        from tools.radio_burst_inline_v19 import ENV as BURST_ENV
        import multiprocessing.queues
        original=multiprocessing.queues.Queue.get
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'report.json'
            path.write_text(json.dumps(dict(private_ipc_empty_backoff_us=500)))
            with patch.dict(os.environ,{binding.ENV:str(path),IPC_ENV:'500',BURST_ENV:'8'},clear=True), \
                 patch.object(binding,'installed_connection',return_value=nullcontext(object())), \
                 patch('tools.radio_burst_inline_v19.inline_burst',return_value=nullcontext()):
                with binding.private_connection('test'):
                    self.assertIsNot(multiprocessing.queues.Queue.get,original)
                self.assertIs(multiprocessing.queues.Queue.get,original)
                self.assertEqual(json.loads((path.parent/'ipc_backoff.json').read_text())['microseconds'],500)
                path.write_text('{}')
                with self.assertRaisesRegex(RuntimeError,'declared private arm'):
                    with binding.private_connection('test'):pass
                self.assertIs(multiprocessing.queues.Queue.get,original)

    def test_combination_requires_explicit_relay_receipt_and_exact_two_hashes(self):
        combined=dict(PRIVATE,relay_sha256='9'*64)
        with tempfile.TemporaryDirectory(dir=binding.ROOT/'diagnosticos/resultados_v19') as folder:
            path=Path(folder)/'report.json'
            report=dict(private=True,promoted=False,private_firmware_activated=True,
                        source_build_report='firmware.json',private_relay_build_report='relay.json',
                        baseline=dict(identity=dict(PRIVATE,**ACCEPTED)),private_identity=combined)
            path.write_text(json.dumps(report))
            def checked(firmware,relay=None):
                return dict(CANDIDATE,relay_sha256='9'*64 if relay=='relay.json' else ACCEPTED['relay_sha256'])
            with patch.dict(os.environ,{binding.ENV:str(path)}), \
                 patch.object(binding,'checked_pair',side_effect=checked), \
                 patch.object(binding,'accepted_identity',return_value=ACCEPTED), \
                 patch.object(binding,'installed_identity',return_value=combined):
                self.assertEqual(binding.private_identity('test'),combined)
                del report['private_relay_build_report'];path.write_text(json.dumps(report))
                with self.assertRaisesRegex(RuntimeError,'pair differs'):binding.private_identity('test')

    def test_combined_activation_stages_only_the_exact_selected_relay(self):
        backend,acceptance,journal=self.backend()
        selected=dict(CANDIDATE,relay_path='reviewed-private-relay.bin',relay_sha256='9'*64)
        backend._hash.side_effect=lambda p:selected['elf_sha256'] if p.endswith('.elf') else selected['relay_sha256']
        activate(backend,acceptance,selected,{},journal)
        backend._board().run.assert_any_call('push','reviewed-private-relay.bin','/private/relay/unoq_stream')
        prepared=backend.start_new_relay.call_args.args[1]
        self.assertEqual(prepared['candidate_identity'],dict(firmware_sha256='d'*64,relay_sha256='9'*64))

    def test_inline_burst_arm_never_activates_legacy_ack_wrapper(self):
        from tools.radio_burst_inline_v19 import ENV as BURST_ENV
        connection=object()
        with patch.dict(os.environ,{BURST_ENV:'4'},clear=True), \
                patch.object(binding,'installed_connection',return_value=nullcontext(connection)), \
                patch('tools.radio_query_candidate_v19.refresh_query_after_chunk_ack') as replay, \
                patch('tools.radio_burst_inline_v19.inline_burst',return_value=nullcontext()) as burst:
            with binding.private_connection('test') as result:
                self.assertIs(result,connection)
            burst.assert_called_once_with(4,None,False)
            replay.assert_not_called()

    def test_binding_requires_exact_private_firmware_and_accepted_relay(self):
        with tempfile.TemporaryDirectory(dir=binding.ROOT/'diagnosticos/resultados_v19') as folder:
            path=Path(folder)/'report.json'
            report=dict(private=True,promoted=False,private_firmware_activated=True,
                source_build_report='build.json',private_identity=PRIVATE,
                baseline=dict(identity=dict(PRIVATE,**ACCEPTED)))
            def save():path.write_text(json.dumps(report))
            save()
            with patch.dict(os.environ,{binding.ENV:str(path)}),patch.object(binding,'checked_firmware',return_value=CANDIDATE), \
                    patch.object(binding,'accepted_identity',return_value=ACCEPTED), \
                    patch.object(binding,'installed_identity',return_value=PRIVATE):
                self.assertEqual(binding.private_identity('test'),PRIVATE)
                for mutate in (dict(restoring=True),dict(error='failed'),dict(promoted=True),
                               dict(private_identity=dict(PRIVATE,relay_sha256='9'*64)),
                               dict(private_identity=dict(PRIVATE,board_serial='other'))):
                    original=dict(report);report.update(mutate);save()
                    with self.assertRaises(RuntimeError):binding.binding_identity('test')
                    report=original
                save()
                with patch.object(binding,'installed_identity',return_value=dict(PRIVATE,**ACCEPTED)):
                    with self.assertRaisesRegex(RuntimeError,'differs'):binding.private_identity('test')

    def backend(self):
        backend=Mock();backend.new_relay='/private/relay'
        sources={'sketch/sketch.ino':'b'*64,'python/main.py':'a'*64}
        acceptance=dict(candidate_identity=ACCEPTED,sources=dict(app=sources),
                        artifacts=dict(relay=dict(path='accepted-relay.bin')))
        backend._sources.return_value=dict(sources,**{'sketch/sketch.ino':CANDIDATE['source_sha256']})
        backend._hash.side_effect=lambda p:CANDIDATE['elf_sha256'] if p.endswith('.elf') else CANDIDATE['relay_sha256']
        backend.verify_new.return_value={k:True for k in ('accepted_identity_equal','sources_exact','snapshot_equal',
            'continuous','integrity_ok','cpu_equal','relay_configuration_verified')}
        journal=Mock();journal.step.side_effect=lambda name,operation:operation()
        return backend,acceptance,journal

    def test_source_only_rebuild_uses_expected_hash_before_relay(self):
        backend,acceptance,journal=self.backend()
        activate(backend,acceptance,CANDIDATE,{},journal)
        backend._board().run.assert_any_call('push','private.ino',APP+'/sketch/sketch.ino')
        expected=dict(candidate_identity=dict(ACCEPTED,firmware_sha256='d'*64))
        backend.start_new_app.assert_called_once_with(expected)
        backend.start_new_relay.assert_called_once_with({},expected)
        private=backend.verify_new.call_args.args[1]
        self.assertEqual(private['sources']['app']['sketch/sketch.ino'],'e'*64)
        self.assertEqual(acceptance['sources']['app']['sketch/sketch.ino'],'b'*64)

    def test_source_elf_or_launcher_failure_never_starts_relay(self):
        for failure in ('source','elf','launcher'):
            with self.subTest(failure=failure):
                backend,acceptance,journal=self.backend()
                if failure=='source':backend._sources.return_value={}
                elif failure=='elf':backend._hash.side_effect=lambda p:'0'*64 if p.endswith('.elf') else 'c'*64
                else:backend.start_new_app.side_effect=RuntimeError('BIN differs')
                with self.assertRaises(RuntimeError):activate(backend,acceptance,CANDIDATE,{},journal)
                backend.start_new_relay.assert_not_called()

    def test_partial_private_rebuild_failure_invokes_full_original_restore(self):
        from tools.build_relay_candidate_v19 import execute_build
        from tests.v19.test_q_update_transaction import Backend
        backend=Backend();capture=backend.capture
        backend.capture=lambda:dict(capture(),identity=ACCEPTED)
        backend.new_relay='/private/relay';backend._board=Mock();backend._require_stopped_original=Mock()
        sources={'sketch/a.h':'a'*64}
        acceptance=dict(candidate_identity=ACCEPTED,sources=dict(app=sources),
                        artifacts=dict(relay=dict(path='accepted.bin')))
        backend._sources=Mock(return_value=dict(sources,**{'sketch/sketch.ino':'e'*64}))
        backend._hash=Mock(side_effect=lambda p:'0'*64 if p.endswith('.elf') else 'c'*64)
        backend.start_new_app=Mock();backend.start_new_relay=Mock()
        report={};journal=Mock();journal.step.side_effect=lambda name,operation:operation()
        execute_build(backend,acceptance,Path('.'),Path('.'),report,lambda:None,
                      builder=lambda *_:activate(backend,acceptance,CANDIDATE,{},journal))
        self.assertFalse(report['ok']);self.assertTrue(report['restoration']['ok'])
        self.assertFalse(report['state_uncertain'])
        self.assertIn('restore_sources',backend.calls);self.assertIn('verify_original',backend.calls)
        backend.start_new_relay.assert_not_called()

    def test_firmware_gui_adapter_hands_off_owner_and_rolls_back(self):
        from tests.v19 import test_private_relay_gui as fixtures
        from tools.probe_relay_gui_v19 import execute_gui
        for fails in (False,True):
            with self.subTest(fails=fails):
                backend=fixtures.PrivateGuiTests().backend();backend._identity.return_value=PRIVATE
                report={}
                def adapter(*_):
                    self.assertEqual(backend.depth,1)
                    if fails:raise RuntimeError('private load failed')
                    return backend.verify_new()
                def gui():
                    self.assertEqual(backend.depth,0)
                    self.assertTrue(report['private_firmware_activated'])
                    self.assertNotIn('private_candidate_activated',report)
                    return dict(ok=True)
                execute_gui(backend,dict(candidate_identity=ACCEPTED),CANDIDATE,
                            report,lambda:None,gui,activate_pair=adapter)
                self.assertEqual(report['ok'],not fails)
                self.assertTrue(report['restoration']['ok'])
                self.assertFalse(report['state_uncertain'])
