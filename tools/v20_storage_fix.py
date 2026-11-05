"""Bounded Storage lifetime patch anchored to an already restored V20 proof."""
import hashlib,json
from pathlib import Path
from monitor.v20.q_support.board import source_files
from monitor.v20.memory_contract import load_contract,verify_board
ROOT=Path(__file__).resolve().parents[1]
APP='/home/arduino/ArduinoApps/scope-v20-20261031-225916'


def validate(path):
    path=Path(path).resolve()
    if not path.is_relative_to(ROOT/'diagnosticos/resultados_v20'):raise ValueError('V20 diagnostic baseline required')
    proof=json.loads(path.read_text())
    if not(proof.get('private') is True and proof.get('promoted') is False and proof.get('ok') is True and proof.get('restoration',{}).get('ok') is True and proof.get('memory_contract')==load_contract()):
        raise ValueError('Exact restored SRAM-tail baseline required')
    old=proof['v20_sources'];folder=ROOT/'arduino/v20/oscilloscope'
    new={p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files(folder)}
    changed={name for name in old if name in new and old[name]!=new[name]}
    if old.keys()!=new.keys() or not changed or not changed<={'sketch/acquisition.h','sketch/acquisition_storage.h'}:
        raise ValueError('Only the bounded acquisition/Storage lifetime patch may be installed')
    return proof,old,new


def install(backend,app,stage,output,path):
    from tools.probe_v20_sram3 import MANIFEST
    from monitor.v19.q_support.prepare import atomic_report
    if app!=APP:raise ValueError('Exact V20 candidate app required')
    proof,old,new=validate(path);board=backend._board();contract=verify_board(board)
    actual=json.loads(board.shell('python3','-c',MANIFEST,app,json.dumps(list(old)),capture=True).stdout)
    if actual!=old or backend._hash(app+'/.cache/sketch/sketch.ino.bin')!=proof['firmware_before']:
        raise RuntimeError('Imported V20 differs from lifetime-patch baseline')
    board.shell('mkdir','-p',stage);archive=stage+'/v20_original.tar'
    board.shell('tar','-C',app,'-cf',archive,'app.yaml','python','sketch','.cache/sketch')
    board.run('pull',archive,str(output/'v20_original.tar'))
    saved=dict(kind='storage_lifetime',remote_archive=archive,sha256=hashlib.sha256((output/'v20_original.tar').read_bytes()).hexdigest(),
               previous_firmware=proof['firmware_before'],old_sources=old,new_sources=new,memory_contract=contract,
               baseline_report=str(Path(path).resolve()),baseline_report_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())
    from tools.v20_memory_fix import cache_inventory
    saved['old_cache_manifest']=cache_inventory(board,'archive',archive)
    atomic_report(output/'memory_fix_backup.json',saved)
    for relative in ('sketch/acquisition_storage.h','sketch/acquisition.h'):
        board.run('push',str(ROOT/'arduino/v20/oscilloscope'/relative),app+'/'+relative)
    return saved
