"""Pure helpers for isolated probe source adoption and durable operation journal.

Integration proposal only: this module does not contact Q or alter run_probe.py.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

APP='/home/arduino/ArduinoApps/scope-v18-rate-probe'
NAME='Scope V18 Rate Probe'
RECIPES={APP:NAME,APP+'-spi40':'Scope V18 Rate Probe SPI40',APP+'-wide8':'Scope V18 Rate Probe Wide8',APP+'-txclean':'Scope V18 Rate Probe TXClean',APP+'-word14':'Scope V18 Rate Probe Word14',APP+'-full8':'Scope V18 Rate Probe Full8',APP+'-wordping':'Scope V18 Rate Probe WordPing',APP+'-spi16':'Scope V18 Rate Probe SPI16',APP+'-batch2':'Scope V18 Rate Probe Batch2',APP+'-batchfast':'Scope V18 Rate Probe BatchFast',APP+'-batchnative':'Scope V18 Rate Probe BatchNative',APP+'-batchstack':'Scope V18 Rate Probe BatchStack',APP+'-batcharena':'Scope V18 Rate Probe BatchArena',APP+'-alignedping':'Scope V18 Rate Probe AlignedPing',APP+'-adc16':'Scope V18 Rate Probe ADC16'}
EXCLUDED={'.git','.cache','__pycache__','data','.venv'}

def source_manifest(folder):
    folder=Path(folder)
    return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob('*')) if p.is_file() and not p.is_symlink()
            and not any(part in EXCLUDED for part in p.relative_to(folder).parts)
            and p.name!='.DS_Store' and p.suffix!='.pyc'}

# Run once via board.shell('python3','-c',REMOTE_MANIFEST,APP,capture=True).
# Includes extra remote source files: equality must never silently ignore them.
REMOTE_MANIFEST="""import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1]);excluded={'.git','.cache','__pycache__','data','.venv'}
if root.as_posix() not in ('/home/arduino/ArduinoApps/scope-v18-rate-probe','/home/arduino/ArduinoApps/scope-v18-rate-probe-spi40','/home/arduino/ArduinoApps/scope-v18-rate-probe-wide8','/home/arduino/ArduinoApps/scope-v18-rate-probe-txclean','/home/arduino/ArduinoApps/scope-v18-rate-probe-word14','/home/arduino/ArduinoApps/scope-v18-rate-probe-full8','/home/arduino/ArduinoApps/scope-v18-rate-probe-wordping','/home/arduino/ArduinoApps/scope-v18-rate-probe-spi16','/home/arduino/ArduinoApps/scope-v18-rate-probe-batch2','/home/arduino/ArduinoApps/scope-v18-rate-probe-batchfast','/home/arduino/ArduinoApps/scope-v18-rate-probe-batchnative','/home/arduino/ArduinoApps/scope-v18-rate-probe-batchstack','/home/arduino/ArduinoApps/scope-v18-rate-probe-batcharena','/home/arduino/ArduinoApps/scope-v18-rate-probe-alignedping','/home/arduino/ArduinoApps/scope-v18-rate-probe-adc16') or not root.is_dir() or root.is_symlink():raise RuntimeError('Unexpected candidate root')
paths=[p for p in sorted(root.rglob('*')) if not any(x in excluded for x in p.relative_to(root).parts)]
if any(p.is_symlink() for p in paths):raise RuntimeError('Candidate source symlink')
print(json.dumps({p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file() and p.name!='.DS_Store' and p.suffix!='.pyc'},sort_keys=True))
"""

def adoption_decision(apps,containers,expected,remote,remote_app=APP):
    """Require stopped known application plus exact full source equality."""
    if remote_app not in RECIPES:raise ValueError('Unexpected app path')
    matches=[app for app in apps if app.get('name')==RECIPES[remote_app]]
    if not matches:return 'create'
    if len(matches)!=1:raise ValueError('Ambiguous candidate app')
    # Verify path using the actual app list field supplied by the adapter; never
    # infer ownership from a matching display name alone.
    if matches[0].get('path')!=remote_app:raise ValueError('Candidate app path unknown or changed')
    if matches[0].get('running') is not False:raise ValueError('Candidate app not confirmed stopped')
    for item in containers:
        labels=item.get('Config',{}).get('Labels') or {}
        name=item.get('Name','').lstrip('/')
        candidate=(name.startswith('scope-v18-rate-probe-') or
            labels.get('com.docker.compose.project')=='scope-v18-rate-probe')
        if candidate and item.get('State',{}).get('Running') is not False:
            raise ValueError('Candidate container is active or state unknown')
    if not expected or expected!=remote:raise ValueError('Candidate sources differ; refuse overwrite')
    return 'adopt'

class ProbeJournal:
    """Persist intent BEFORE a mutation; persist outcome after it, even failures."""
    def __init__(self,path,report):self.path=Path(path);self.report=report
    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        fd,name=tempfile.mkstemp(prefix=self.path.name+'.',dir=self.path.parent)
        try:
            with os.fdopen(fd,'w') as stream:
                json.dump(self.report,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
            os.replace(name,self.path)
            directory=os.open(self.path.parent,os.O_RDONLY)
            try:os.fsync(directory)
            finally:os.close(directory)
        finally:
            if os.path.exists(name):os.unlink(name)
    def capture(self,**evidence):
        self.report.update(evidence);self.report['snapshot_captured']=True;self.save()
    def mutate(self,name,operation):
        entry={'operation':name,'state':'intent'}
        self.report.setdefault('journal',[]).append(entry);self.save()
        try:
            result=operation();entry['state']='completed';self.save();return result
        except BaseException as exc:
            entry.update(state='failed',error=repr(exc));self.save();raise

def verified_identity(expected_firmware,expected_relay,actual):
    for value in (expected_firmware,expected_relay):
        if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value):raise ValueError('Expected SHA256 required')
    return actual.get('firmware_sha256')==expected_firmware and actual.get('relay_sha256')==expected_relay
