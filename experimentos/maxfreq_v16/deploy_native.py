"""Deploy the compiled native integration with a fresh exact firmware backup."""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from unoq import Board,config_path
from experimentos.megaboom_ch1_3584_v16.run import start_relay
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
import usb_stream


def main():
    require_exclusive_monitor()
    stable=Board(json.loads(config_path('v16').read_text()))
    target=usb_stream.binary(stable,p992=True,audio=True)
    manifest={'ready':False,'relay':target,'backup':str(stable.backup()),
              'source_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                              for folder in (stable.local,ROOT/'arduino/historico/v16/relay')
                              for p in sorted(folder.rglob('*')) if p.is_file() and
                              p.suffix in ('.h','.ino','.c','.py','.yaml')}}
    path=EXP/'production_deployment.json'
    def save():path.write_text(json.dumps(manifest,indent=2)+'\n')
    save()
    try:
        usb_stream.stop(stable);stable.stop()
        stable.push_sources(stable.check_sources(),stable.remote)
        stable.start();start_relay(stable,target)
        manifest['ready']=True;save()
    except BaseException as exc:
        manifest['error']=str(exc);save()
        # Restore the exact old sketch when deployment fails; keep local changes reviewable.
        for p in sorted((EXP/'production_before_native/sketch').rglob('*')):
            if p.is_file() and p.suffix in ('.h','.ino','.yaml'):
                relative=p.relative_to(EXP/'production_before_native/sketch')
                stable.run('push',str(p),stable.remote+'/sketch/'+relative.as_posix())
        stable.start()
        prior=json.loads((EXP/'deployment.json').read_text())
        start_relay(stable,prior['stable_relay'])
        manifest['previous_firmware_restored']=True;save()
        raise
    print(json.dumps(manifest,indent=2),flush=True)


if __name__=='__main__':
    main()
