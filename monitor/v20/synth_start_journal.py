"""Bounded startup metadata only; never records PCM, notes or parameters."""
from datetime import datetime
import json,time
from pathlib import Path
from threading import Lock


class SynthStartJournal:
    def __init__(self, folder=None):
        folder=Path(folder) if folder is not None else Path(__file__).resolve().parents[2]/'diagnosticos/resultados_v20/synth_start'
        self.path=folder/('play_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.jsonl')
        self.started=time.monotonic();self.lock=Lock();self.seen=set();self.count=0

    def event(self,stage,**fields):
        # Every distinct milestone/state is written once, at most64 per click.
        safe={k:(v[:240] if isinstance(v,str) else v) for k,v in fields.items()
              if v is None or type(v) in (str,int,float,bool)}
        key=(stage,json.dumps(safe,sort_keys=True))
        with self.lock:
            if key in self.seen or self.count>=64:return
            self.seen.add(key);self.count+=1
            try:
                self.path.parent.mkdir(parents=True,exist_ok=True)
                with self.path.open('a') as stream:
                    stream.write(json.dumps(dict(stage=stage,elapsed=time.monotonic()-self.started,**safe))+'\n')
            except OSError:pass  # Diagnostic I/O must not prevent playback.


def record(source,stage,**fields):
    journal=getattr(source,'_start_journal',None)
    if journal is not None:journal.event(stage,**fields)
