"""Load the isolated tick-based contract without changing the stable module."""
import importlib.util,sys
from pathlib import Path
EXP=Path(__file__).resolve().parent

def load():
 name='monitor.v16.receiver.unoq_acquisition'
 import monitor.v16.receiver.unoq_acquisition as stable
 spec=importlib.util.spec_from_file_location(name,EXP/'acquisition.py')
 acquisition=importlib.util.module_from_spec(spec);sys.modules[name]=acquisition
 try:
  spec.loader.exec_module(acquisition)
  ds=importlib.util.spec_from_file_location('ch1_660_decoder',EXP/'decoder.py')
  decoder=importlib.util.module_from_spec(ds);ds.loader.exec_module(decoder)
 finally:sys.modules[name]=stable
 return acquisition,decoder.SingleDecoder
