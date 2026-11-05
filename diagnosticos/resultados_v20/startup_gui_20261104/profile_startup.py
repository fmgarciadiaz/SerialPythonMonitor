import subprocess,sys,os
from pathlib import Path
code='''import cProfile,pstats,time,importlib,sys,faulthandler
faulthandler.dump_traceback_later(5,repeat=True)
from unittest.mock import patch
t=time.perf_counter()
m=importlib.import_module('monitor.v'+sys.argv[1]+'.app')
print('import_s',time.perf_counter()-t,flush=True)
a=m.QtWidgets.QApplication([])
p=cProfile.Profile();p.enable();t=time.perf_counter()
with patch.object(m,'usb_devices',return_value=[]),patch.object(m.list_ports,'comports',return_value=[]):
 w=m.SerialMonitorWindow()
print('constructor_s',time.perf_counter()-t,flush=True)
p.disable();pstats.Stats(p).sort_stats('cumtime').print_stats(22)
w.render_timer.stop();w.close()
'''
folder=Path('diagnosticos/resultados_v20/startup_gui_20261104')
for v in (19,20):
 try:
  r=subprocess.run([sys.executable,'-c',code,str(v)],capture_output=True,text=True,timeout=20,env=dict(os.environ,QT_QPA_PLATFORM='offscreen'))
  print(v,r.stdout,r.stderr[-1000:],flush=True)
  (folder/f'profile_v{v}.txt').write_text(r.stdout+r.stderr)
 except subprocess.TimeoutExpired as e:
  text=(e.stdout or b'').decode()+(e.stderr or b'').decode()
  (folder/f'profile_v{v}_timeout.txt').write_text(text)
  print(v,'TIMEOUT',text[-3000:],flush=True)
