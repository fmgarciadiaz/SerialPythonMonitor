"""Exact private working V20 pair; never grants acceptance or deploys Q."""
import hashlib
import json
from pathlib import Path
import re
from monitor.v20.memory_contract import load_contract, verify_runner
from monitor.v20.q_support.board import source_files

ROOT=Path(__file__).resolve().parents[3]
RECEIPT=Path(__file__).with_name('working_pair.json')
APP='scope-v20-20261031-225916-main-1'
PROOF='diagnosticos/resultados_v20/storage_lifetime_cycle_20261101/report.json'
CHECKS=('accepted_identity_equal','sources_exact','snapshot_equal','continuous',
        'integrity_ok','cpu_equal','relay_configuration_verified')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def manifest(folder):
    return {p.relative_to(folder).as_posix():digest(p) for p in source_files(folder)}


def checked_local(receipt,serial):
    identity=receipt.get('identity',{})
    if (receipt.get('schema')!=1 or receipt.get('version')!=20 or receipt.get('private') is not True
            or receipt.get('promoted') is not False or receipt.get('public_rates_changed') is not False
            or identity.get('app')!=APP or identity.get('board_serial')!=serial
            or set(identity)!=set(('board_serial','app','firmware_sha256','relay_sha256'))
            or any(not isinstance(identity.get(k),str) or not re.fullmatch('[0-9a-f]{64}',identity[k])
                   for k in ('firmware_sha256','relay_sha256'))):
        raise RuntimeError('Recibo privado de trabajo V20 inválido')
    proof_path=Path(receipt['source_report']).resolve()
    if proof_path!=(ROOT/PROOF).resolve() or digest(proof_path)!=receipt.get('source_report_sha256'):
        raise RuntimeError('Prueba original V20 cambió')
    proof=json.loads(proof_path.read_text())
    if (proof.get('private') is not True or proof.get('promoted') is not False or proof.get('version')!=20
            or proof.get('ok') is not True or proof.get('restoration',{}).get('ok') is not True
            or proof.get('ready_no_yield',False) is not False or proof.get('tcp_queue_recovery',False) is not False
            or len(proof.get('cases',[]))<2 or any(c.get('state')!='complete'
                or c.get('metrics',{}).get('integrity_pass') is not True for c in proof['cases'])
            or proof.get('baseline',{}).get('identity',{}).get('board_serial')!=serial):
        raise RuntimeError('Prueba física original/restaurada V20 requerida')
    contract=load_contract()
    if receipt.get('memory_contract')!=contract or proof.get('memory_contract')!=contract:
        raise RuntimeError('Contrato BSP V20 cambió')
    for name,folder in (('v20_sources',ROOT/'arduino/v20/oscilloscope'),('relay_sources',ROOT/'arduino/v20/relay')):
        actual=manifest(folder)
        if receipt.get(name)!=actual or proof.get(name)!=actual:
            raise RuntimeError('Fuentes V20 difieren de la prueba: '+name)
    if (identity['firmware_sha256']!=proof.get('firmware_before') or identity['relay_sha256']!=proof.get('relay_sha256')
            or digest(proof_path.parent/'relay.bin')!=identity['relay_sha256']):
        raise RuntimeError('Binarios V20 difieren de la prueba')
    return dict(identity)


def receipt_from_report(path,serial):
    path=Path(path).resolve()
    if not path.is_relative_to(ROOT/'diagnosticos/resultados_v20'):
        raise RuntimeError('Informe de activación V20 requerido')
    report=json.loads(path.read_text())
    if (report.get('ok') is not True or report.get('private') is not True or report.get('promoted') is not False
            or report.get('private_firmware_activated') is not True or report.get('error') or report.get('restoration')
            or report.get('restoring') or report.get('cancelling') or report.get('state_uncertain')
            or any(report.get('private_verification',{}).get(k) is not True for k in CHECKS)):
        raise RuntimeError('Activación V20 verificada requerida')
    proof=json.loads(Path(report['source_report']).read_text())
    receipt=dict(schema=1,version=20,private=True,promoted=False,public_rates_changed=False,
                 identity=report['private_identity'],source_report=report['source_report'],
                 source_report_sha256=report['source_report_sha256'],memory_contract=report['memory_contract'],
                 v20_sources=report['v20_sources'],relay_sources=proof['relay_sources'],
                 activation_report=str(path),activation_report_sha256=digest(path))
    checked_local(receipt,serial)
    return receipt


def working_identity(serial,runner,*,path=None):
    receipt=json.loads((RECEIPT if path is None else Path(path)).read_text())
    expected=checked_local(receipt,serial)
    activation=Path(receipt['activation_report']).resolve()
    if (not activation.is_relative_to(ROOT/'diagnosticos/resultados_v20')
            or digest(activation)!=receipt.get('activation_report_sha256')
            or receipt_from_report(activation,serial)!=receipt):
        raise RuntimeError('Informe de activación V20 cambió')
    verify_runner(serial,runner)
    return expected
