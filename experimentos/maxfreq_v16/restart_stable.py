import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from unoq import Board,config_path
import usb_stream
from experimentos.megaboom_ch1_3584_v16.run import start_relay
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
require_exclusive_monitor()
b=Board(json.loads(config_path('v16').read_text()))
target=usb_stream.binary(b,p992=True,audio=True)
usb_stream.stop(b);b.stop();b.start();start_relay(b,target)
