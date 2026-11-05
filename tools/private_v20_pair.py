"""Exact V20 experiment binding; never overrides a production receipt."""
from contextlib import contextmanager,nullcontext
import hashlib
import json
import os
from pathlib import Path
from monitor.v20.q_support.board import source_files
from monitor.v20.io.live_connection import installed_identity,installed_connection

ROOT=Path(__file__).resolve().parents[1]
ENV='ARDUSCOPIO_PRIVATE_V20_BINDING'
APP='/home/arduino/ArduinoApps/scope-v20-20261031-225916'
APP_CONTAINER=APP.rsplit('/',1)[-1]+'-main-1'


def checked_proof(path):
    path=Path(path).resolve()
    if not path.is_relative_to(ROOT/'diagnosticos/resultados_v20'):raise ValueError('Private V20 evidence required')
    report=json.loads(path.read_text())
    if not (report.get('private') is True and report.get('promoted') is False and report.get('ok') is True
            and report.get('restoration',{}).get('ok') is True and report.get('ready_no_yield',False) is False
            and type(report.get('tcp_queue_recovery',False)) is bool
            and len(report.get('cases',[]))>=2
            and all(c.get('state')=='complete' and c.get('metrics',{}).get('integrity_pass') is True for c in report['cases'])):
        raise ValueError('Restored V20 original-relay physical evidence required')
    from monitor.v20.memory_contract import load_contract
    if report.get('memory_contract')!=load_contract():raise ValueError('Audited V20 memory contract required')
    app=ROOT/'arduino/v20/oscilloscope';relay=ROOT/'arduino/v20/relay'
    for name,folder in [('v20_sources',app),('relay_sources',relay)]:
        files=source_files(folder)
        expected={p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        if name=='relay_sources' and report.get('tcp_queue_recovery') is True:
            candidate=ROOT/'experiments/v20/tcp_queue_recovery/frame_send_queue.h'
            archived=path.parent/'private_frame_send_queue.h'
            if archived.read_bytes()!=candidate.read_bytes():raise ValueError('Private queue header archive differs')
            expected['frame_send_queue.h']=hashlib.sha256(candidate.read_bytes()).hexdigest()
        if report.get(name)!=expected:raise ValueError('V20 sources differ from measured proof: '+name)
    binary=path.parent/'relay.bin'
    if hashlib.sha256(binary.read_bytes()).hexdigest()!=report['relay_sha256']:raise ValueError('V20 relay proof bytes changed')
    return dict(source_report=str(path),source_report_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                firmware_sha256=report['firmware_before'],relay_sha256=report['relay_sha256'],relay_path=str(binary),
                v20_sources=report['v20_sources'],memory_contract=report['memory_contract'])


def expected_identity(serial):
    path=Path(os.environ[ENV]).resolve()
    if not path.is_relative_to(ROOT/'diagnosticos/resultados_v20'):raise RuntimeError('Private V20 binding path required')
    report=json.loads(path.read_text())
    if (report.get('private') is not True or report.get('promoted') is not False or
            not report.get('private_firmware_activated') or report.get('restoring') or report.get('error') or
            report.get('restoration') or report.get('cancelling')):raise RuntimeError('V20 binding is not active')
    proof=checked_proof(report['source_report'])
    if proof['source_report_sha256']!=report.get('source_report_sha256'):raise RuntimeError('V20 proof report changed')
    expected=dict(board_serial=serial,app=APP_CONTAINER,firmware_sha256=proof['firmware_sha256'],relay_sha256=proof['relay_sha256'])
    if report.get('private_identity')!=expected:raise RuntimeError('V20 binding identity differs')
    return expected


def private_identity(serial):
    expected=expected_identity(serial)
    from monitor.v20.memory_contract import verify_runner
    from monitor.v20.receiver.unoq_usb import adb
    verify_runner(serial,adb)
    actual=installed_identity(serial,expected_app=APP_CONTAINER,require_accepted=False)
    if actual!=expected:raise RuntimeError('Installed V20 pair differs from private binding')
    return expected


@contextmanager
def connection(serial):
    from tools.relay_wire_metrics_v19 import observe_connection
    from monitor.v20.receiver.unoq_config_receiver import OutputReceiver
    from monitor.v20.receiver.unoq_acquisition import Configuration
    binding=json.loads(Path(os.environ[ENV]).read_text())
    trial=binding.get('private_profile')
    profile_scope=nullcontext()
    priming_scope=nullcontext()
    if binding.get('private_priming_realtime'):
        requested=binding.get('requested_tests',{})
        if (requested.get('radio_adc_bits'),requested.get('radio_adc_rate'),requested.get('radio_a0_rate'))!=(8,2000000,40000):
            raise ValueError('Private priming experiment requires ADC8/2M and DAC40k')
        from tools.private_radio_priming_v20 import realtime_radio_priming
        priming_scope=realtime_radio_priming()
    if trial is not None:
        from tools.private_rate_profiles_v20 import PRIVATE_PROFILES,diagnostic_profiles
        bits,rate=trial['bits'],trial['rate']
        if not any(b==bits and 160000000//ticks==rate for b,ticks,_ in PRIVATE_PROFILES):
            raise ValueError('Unsupported private GUI ADC candidate')
        profile_scope=diagnostic_profiles(bits,(rate,))
    with profile_scope,priming_scope,installed_connection(serial,identity=private_identity) as connected:
        path=Path(os.environ[ENV]).parent/'wire_metrics.json'
        if os.environ.get('ARDUSCOPIO_PRIVATE_RAW_ACK_LATENCY')=='1':
            from tools.reader_stages_v20 import capture
            stages=capture(path.parent/'reader_stages.json')
        else:stages=nullcontext()
        with stages:
            with observe_connection(connected,path,receiver_class=OutputReceiver,configuration=Configuration,allow_non_native=True):yield connected


def reserve_screen(metrics,capacity):
    """Private normalized reserve screen, never public acceptance."""
    margin=metrics.get('mean_send_margin');peak=metrics.get('mcu_queue_peak');slack=metrics.get('min_slack_ticks')
    valid=(type(capacity) is int and capacity>0 and type(peak) is int and 0<=peak<=capacity)
    return dict(publicly_accepted=False,capacity=capacity,legacy_headroom_pass=metrics.get('headroom_pass',False),
                free_at_peak=capacity-peak if valid else None,
                passes=bool(valid and margin is not None and margin>=.10 and 2*peak<capacity and slack is not None and slack>0),
                criterion='Mean margin >=10%, cumulative peak strictly below half capacity, positive slack; private screen only')
