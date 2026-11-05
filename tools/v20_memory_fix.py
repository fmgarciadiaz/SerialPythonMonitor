"""Install only the reviewed two-file V20 memory repair; preserve old sources/cache."""
import hashlib
import json
from pathlib import Path
from monitor.v20.q_support.board import source_files
from monitor.v20.memory_contract import verify_board

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'respaldos/parejas/v20_gemini_before_memory_fix_20261101/arduino/v20/oscilloscope'
NEW=ROOT/'arduino/v20/oscilloscope'


def manifests():
    old={p.relative_to(OLD).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files(OLD)}
    new={p.relative_to(NEW).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files(NEW)}
    changed={p for p in old.keys()&new.keys() if old[p]!=new[p]}
    if set(new)-set(old)!={'sketch/acquisition_memory.h'} or set(old)-set(new) or changed!={'sketch/acquisition.h'}:
        raise ValueError('Only the reviewed acquisition.h + acquisition_memory.h repair may be installed')
    return old,new


def install(backend,app,stage,output):
    from tools.probe_v20_sram3 import MANIFEST
    contract=verify_board(backend._board());old,new=manifests();board=backend._board()
    current=json.loads(board.shell('python3','-c',MANIFEST,app,json.dumps(list(old)),capture=True).stdout)
    if current!=old:raise RuntimeError('Original V20 sources differ from paired backup')
    board.shell('mkdir','-p',stage)
    backup=stage+'/v20_original.tar'
    board.shell('tar','-C',app,'-cf',backup,'app.yaml','python','sketch','.cache/sketch')
    board.run('pull',backup,str(output/'v20_original.tar'))
    saved=dict(remote_archive=backup,sha256=hashlib.sha256((output/'v20_original.tar').read_bytes()).hexdigest(),
               previous_firmware=backend._hash(app+'/.cache/sketch/sketch.ino.bin'),old_sources=old,new_sources=new,
               memory_contract=contract)
    # The archive is complete before the first source replacement.
    from monitor.v19.q_support.prepare import atomic_report
    saved['old_cache_manifest']=cache_inventory(board,'archive',backup)
    atomic_report(output/'memory_fix_backup.json',saved)
    for relative in ('sketch/acquisition_memory.h','sketch/acquisition.h'):
        board.run('push',str(NEW/relative),app+'/'+relative)
    return saved


def undo(backend,app,saved):
    if app!='/home/arduino/ArduinoApps/scope-v20-20261031-225916':raise ValueError('Exact V20 candidate root required')
    board=backend._board()
    if backend._hash(saved['remote_archive'])!=saved['sha256']:raise RuntimeError('Original V20 archive changed')
    expected_cache=saved.get('old_cache_manifest') or cache_inventory(board,'archive',saved['remote_archive'])
    board.shell('python3','-c',_REMOVE_OWNED_DIRS,app)
    board.shell('tar','-C',app,'-xf',saved['remote_archive'])
    if backend._hash(app+'/.cache/sketch/sketch.ino.bin')!=saved['previous_firmware']:
        raise RuntimeError('Original V20 cache restoration failed')

    from tools.probe_v20_sram3 import MANIFEST
    restored=json.loads(board.shell('python3','-c',MANIFEST,app,json.dumps(list(saved['old_sources'])),capture=True).stdout)
    if restored!=saved['old_sources']:raise RuntimeError('Original V20 source restoration failed')
    if cache_inventory(board,'directory',app)!=expected_cache:raise RuntimeError('Original complete V20 cache restoration failed')
    return dict(sources_exact=True,firmware_exact=True,cache_exact=True)


_CACHE_INVENTORY=r'''
import hashlib,json,pathlib,sys,tarfile
mode,location=sys.argv[1:];result={};prefix='.cache/sketch'
if mode=='archive':
 with tarfile.open(location) as archive:
  for entry in archive.getmembers():
   name=entry.name.removeprefix('./').rstrip('/')
   if name!=prefix and not name.startswith(prefix+'/'):continue
   if name in result:raise RuntimeError('Duplicate cache archive entry')
   if entry.isdir():value=['directory']
   elif entry.issym():value=['symlink',entry.linkname]
   elif entry.isfile() or entry.islnk():value=['file',hashlib.sha256(archive.extractfile(entry).read()).hexdigest()]
   else:raise RuntimeError('Unsupported cache archive entry')
   result[name]=value
else:
 root=pathlib.Path(location);folder=root/prefix
 if folder.is_symlink() or not folder.is_dir():raise RuntimeError('Cache directory required')
 for entry in [folder,*folder.rglob('*')]:
  name=entry.relative_to(root).as_posix()
  if entry.is_symlink():value=['symlink',str(entry.readlink())]
  elif entry.is_dir():value=['directory']
  elif entry.is_file():value=['file',hashlib.sha256(entry.read_bytes()).hexdigest()]
  else:raise RuntimeError('Unsupported cache entry')
  result[name]=value
if prefix not in result:raise RuntimeError('Complete cache archive required')
print(json.dumps(result,sort_keys=True))
'''


def cache_inventory(board,mode,path):
    return json.loads(board.shell('python3','-c',_CACHE_INVENTORY,mode,path,capture=True).stdout)


_REMOVE_OWNED_DIRS=r"""
import pathlib,shutil,sys
root=pathlib.Path(sys.argv[1])
for name in ('.cache/sketch','sketch'):
 try:shutil.rmtree(root/name)
 except FileNotFoundError:pass
"""
