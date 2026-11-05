"""Exact private firmware binding; production connection rules stay unchanged."""
from contextlib import contextmanager,ExitStack
import hashlib
import json
import os
from pathlib import Path
from tools.compare_prepare_compiler_v19 import ANCHOR,ROOT
from monitor.v19.io.live_connection import accepted_identity,installed_identity,installed_connection
from monitor.v19.q_support.board import source_files

ENV='ARDUSCOPIO_PRIVATE_FIRMWARE_BINDING'


def checked_firmware(report_path):
    path=Path(report_path).resolve()
    if not path.is_relative_to(ROOT/'diagnosticos/resultados_v19'):
        raise ValueError('Private diagnostic build required')
    report=json.loads(path.read_text());artifact=report.get('artifact',{})
    if report.get('parent_build_report'):
        parent=Path(report['parent_build_report']).resolve()
        if parent!=path.parent/'report.json' or hashlib.sha256(parent.read_bytes()).hexdigest()!=report.get('parent_build_sha256'):
            raise ValueError('Selected firmware parent report changed')
        original=json.loads(parent.read_text())
        if not original.get('ok') or original.get('restoration',{}).get('ok') is not True:
            raise ValueError('Selected firmware parent was not restored')
        if artifact.get('sources')!=original.get('artifact',{}).get('sources') or any(
                value!=original['artifact']['variants'].get(name) for name,value in artifact.get('variants',{}).items()):
            raise ValueError('Selected firmware differs from compiled parent')
    if not (report.get('ok') is True and report.get('restoration',{}).get('ok') is True
            and artifact.get('compiled_with_pair_stopped') is True
            and artifact.get('firmware_installed') is False):
        raise ValueError('Verified isolated firmware comparison required')
    accepted=accepted_identity()
    if artifact['variants']['control_os']['bin_sha256']!=accepted['firmware_sha256']:
        raise ValueError('Control firmware must match accepted BIN exactly')
    sketch=ROOT/'arduino/v19/oscilloscope/sketch'
    sources={p.relative_to(sketch).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files(sketch)}
    if artifact['sources']!=sources:raise ValueError('Original sketch sources changed since comparison')
    extra={}
    if set(artifact['variants']) in ({'control_os','candidate_wav_timing'},
                                   {'control_os','candidate_wav_timing_copy'}):
        from tools.wav_timing_candidate_v19 import candidate_sources,SCHEMA
        if artifact.get('diagnostic_schema')!=SCHEMA:raise ValueError('Exact WAV timing schema required')
        variant=next(n for n in artifact['variants'] if n!='control_os');relative='sketch.ino'
        originals={name:(sketch/name).read_text() for name in ('wav.h','wav_dma.h','sketch.ino')}
        generated=candidate_sources(originals);replacements={}
        if variant=='candidate_wav_timing_copy':
            from tools.wav_copy_candidate_v19 import candidate_text
            generated['wav_dma.h']=candidate_text(generated['wav_dma.h'])
        for name,text in generated.items():
            original=path.parent/'control_os'/name;replacement=path.parent/variant/name
            if original.read_text()!=originals[name] or replacement.read_text()!=text:
                raise ValueError('Exact three-file WAV timing transformation required')
            replacements[name]=dict(path=str(replacement),sha256=hashlib.sha256(replacement.read_bytes()).hexdigest())
        extra=dict(source_files=replacements,diagnostic_schema=SCHEMA)
        expected=generated[relative]
    elif set(artifact['variants'])=={'control_os','candidate_wav_copy'}:
        from tools.wav_copy_candidate_v19 import candidate_text
        variant='candidate_wav_copy';relative='wav_dma.h'
        expected=candidate_text((sketch/relative).read_text())
        for name in ('control_os',variant):
            for unchanged in ('sketch.ino','wav.h'):
                if (path.parent/name/unchanged).read_bytes()!=(sketch/unchanged).read_bytes():
                    raise ValueError('PCM memcpy must preserve sketch and validation')
        if (path.parent/'control_os'/relative).read_bytes()!=(sketch/relative).read_bytes():
            raise ValueError('PCM copy control header changed')
    elif set(artifact['variants'])=={'control_os','candidate_wav_validation'}:
        from tools.wav_validation_candidate_v19 import candidate_text
        variant='candidate_wav_validation';relative='wav.h'
        expected=candidate_text((sketch/relative).read_text())
        # This experiment never changes compiler attributes or the main sketch.
        for name in ('control_os',variant):
            if (path.parent/name/'sketch.ino').read_bytes()!=(sketch/'sketch.ino').read_bytes():
                raise ValueError('WAV validation experiment must preserve sketch.ino')
        if (path.parent/'control_os/wav.h').read_bytes()!=(sketch/'wav.h').read_bytes():
            raise ValueError('WAV control header changed')
    elif set(artifact['variants'])=={'control_os','candidate_o2'}:
        variant='candidate_o2';relative='sketch.ino'
        original=(sketch/relative).read_text()
        if original.count(ANCHOR)!=1:raise ValueError('Unique accepted Os anchor required')
        expected=original.replace(ANCHOR,ANCHOR.replace('"Os"','"O2"'))
    else:raise ValueError('Unknown private firmware experiment')
    source=path.parent/variant/relative
    if source.read_text()!=expected:raise ValueError('Only the exact reviewed source difference is allowed')
    for name in ('control_os',variant):
        for kind,filename in (('bin','sketch.ino.bin'),('elf','sketch.ino.elf')):
            data=path.parent/name/'build'/filename
            if hashlib.sha256(data.read_bytes()).hexdigest()!=artifact['variants'][name][kind+'_sha256']:
                raise ValueError('Compiled firmware artifact changed')
    return dict(source=str(source),source_relative=relative,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                firmware_sha256=artifact['variants'][variant]['bin_sha256'],
                elf_sha256=artifact['variants'][variant]['elf_sha256'],
                relay_sha256=accepted['relay_sha256'],build_report=str(path),**extra)


def checked_pair(firmware_report,relay_report=None):
    candidate=checked_firmware(firmware_report)
    if relay_report is not None:
        from tools.probe_relay_transport_v19 import checked_artifact
        path=Path(relay_report).resolve()
        if not path.is_relative_to(ROOT/'diagnosticos/resultados_v19'):
            raise ValueError('Private relay build report required')
        artifact=checked_artifact(path)
        candidate=dict(candidate,relay_sha256=artifact['sha256'],relay_path=artifact['path'],
                       relay_build_report=str(path))
    return candidate


def binding_identity(serial):
    path=Path(os.environ[ENV]).resolve()
    if not path.is_relative_to(ROOT/'diagnosticos/resultados_v19'):raise RuntimeError('Private binding path required')
    report=json.loads(path.read_text())
    if (report.get('private') is not True or report.get('promoted') is not False
            or report.get('private_firmware_activated') is not True
            or report.get('restoring') or report.get('restoration') or report.get('error')):
        raise RuntimeError('Private firmware binding is not active')
    candidate=checked_pair(report['source_build_report'],report.get('private_relay_build_report'));accepted=accepted_identity()
    baseline=report['baseline']['identity']
    if any(baseline.get(k)!=v for k,v in accepted.items()):raise RuntimeError('Accepted baseline required')
    expected=dict(board_serial=serial,app='scope-v19-main-1',firmware_sha256=candidate['firmware_sha256'],
                  relay_sha256=candidate['relay_sha256'])
    if report['private_identity']!=expected or baseline.get('board_serial')!=serial or baseline.get('app')!=expected['app']:
        raise RuntimeError('Private firmware board/pair differs')
    return expected


def private_identity(serial):
    expected=binding_identity(serial)
    if installed_identity(serial,require_accepted=False)!=expected:
        raise RuntimeError('Installed firmware differs from private binding')
    return expected


@contextmanager
def private_connection(serial):
    with installed_connection(serial,identity=private_identity) as connection:
        # Only this diagnostic factory enables the fixed host comparison arm.
        from tools.radio_query_candidate_v19 import refresh_query_after_chunk_ack
        from tools.relay_wire_metrics_v19 import ENV as METRICS_ENV,observe_connection
        with ExitStack() as stack:
            from tools.ipc_empty_backoff_v19 import ENV as IPC_ENV, empty_backoff
            backoff=int(os.environ.get(IPC_ENV,'0'))
            if backoff:
                binding_path=Path(os.environ[ENV])
                declaration=json.loads(binding_path.read_text()).get('private_ipc_empty_backoff_us')
                if declaration!=backoff:
                    raise RuntimeError('IPC backoff differs from declared private arm')
                stats=stack.enter_context(empty_backoff(backoff))
                from monitor.v19.q_support.prepare import atomic_report
                stack.callback(atomic_report,binding_path.parent/'ipc_backoff.json',stats)
            from tools.radio_burst_inline_v19 import ENV as BURST_ENV, INTERVAL_ENV, STARTUP_ENV, POLL_ENV, PLAY_ENV, inline_burst
            burst=os.environ.get(BURST_ENV)
            if burst is None:
                stack.enter_context(refresh_query_after_chunk_ack())
            else:
                # New comparisons keep the production inline ACK path and
                # select burst only once while constructing a PCM descriptor.
                interval=os.environ.get(INTERVAL_ENV)
                extra={} if os.environ.get(POLL_ENV) is None else dict(poll_ms=int(os.environ[POLL_ENV]))
                if os.environ.get(PLAY_ENV) is not None:
                    selected=int(os.environ[PLAY_ENV])
                    if json.loads(Path(os.environ[ENV]).read_text()).get('private_play_burst')!=selected:
                        raise RuntimeError('PLAY burst differs from declared private arm')
                    extra['play_burst']=selected
                stack.enter_context(inline_burst(int(burst),None if interval is None else int(interval),
                                                os.environ.get(STARTUP_ENV)=='1',**extra))
            path=os.environ.get(METRICS_ENV)
            if path:
                binding=json.loads(Path(os.environ[ENV]).read_text())
                selected=checked_pair(binding['source_build_report'],binding.get('private_relay_build_report'))
                stack.enter_context(observe_connection(connection,Path(path),wav_timing=bool(selected.get('diagnostic_schema'))))
            yield connection
