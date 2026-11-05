"""Compare exact former refresh method and async refresh with identical fake USB latency."""
import ast,json,os,time,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT));os.environ['QT_QPA_PLATFORM']='offscreen'
from monitor.v20 import app as mod
qt=mod.QtWidgets.QApplication([])
with patch.object(mod,'usb_devices',return_value=[]),patch.object(mod.list_ports,'comports',return_value=[]):
 w=mod.SerialMonitorWindow()
w.render_timer.stop()
def drain(condition):
 deadline=time.monotonic()+2
 while not condition() and time.monotonic()<deadline:qt.processEvents();time.sleep(.002)
 assert condition()
drain(lambda:w.refresh_button.isEnabled())
tree=ast.parse((ROOT/'respaldos/host/v20_before_async_ports_20261104/app.py').read_text())
method=next(n for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='SerialMonitorWindow'
            for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='refresh_ports')
namespace=dict(mod.__dict__)
exec(compile(ast.Module(body=[method],type_ignores=[]),'<original-refresh>','exec'),namespace)
rows=[]
def devices():time.sleep(.35);return ['fake-q']
try:
 for mode in ('before','after','before','after'):
  ticks=[];timer=mod.QtCore.QTimer();timer.setInterval(5);timer.timeout.connect(lambda:ticks.append(time.monotonic()))
  with patch.object(mod,'usb_devices',side_effect=devices),patch.object(mod.list_ports,'comports',return_value=[]):
   namespace['usb_devices']=mod.usb_devices;namespace['list_ports']=mod.list_ports
   timer.start();started=time.monotonic()
   if mode=='before':namespace['refresh_ports'](w)
   else:w.refresh_ports()
   dispatch=time.monotonic()-started
   drain(lambda:time.monotonic()-started>=.4 and w.refresh_button.isEnabled())
   timer.stop();rows.append(dict(mode=mode,dispatch_ms=dispatch*1000,
      first_heartbeat_ms=(ticks[0]-started)*1000,heartbeats=len(ticks)))
finally:w.close()
p=Path(__file__).with_name('discovery_before_after.json');p.write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows))
