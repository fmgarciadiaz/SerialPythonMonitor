import sys,time,json,faulthandler
from concurrent.futures import ProcessPoolExecutor,TimeoutError
import multiprocessing as mp
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
ROOT=Path('/Users/fmgarciadiaz/Documents/Development/Electronica/0Fergd/SerialPythonMonitor')
sys.path.insert(0,str(ROOT))

def main():
    from monitor.v20.fm_source import FMSource
    from monitor.v20.synth_process import prepare,render,initialize_worker
    from unittest.mock import patch
    from PySide6 import QtWidgets
    from monitor.v20.app import SerialMonitorWindow
    qt=QtWidgets.QApplication([])
    with patch('monitor.v20.app.usb_devices',return_value=[]),patch('monitor.v20.app.list_ports.comports',return_value=[]):
        window=SerialMonitorWindow()
    panel=window.fm_panel
    source=FMSource(rate=panel.output_rate.currentData(),parameters=panel.parameters(1))
    preset=panel.preset.currentText();window.close();qt.processEvents()
    pool=ProcessPoolExecutor(1,mp_context=mp.get_context('spawn'),initializer=initialize_worker)
    began=time.monotonic();report=dict(preset=preset,rate=source.rate,parameters=str(source.parameters))
    try:
        result=pool.submit(prepare,source.rate,source.parameters).result(timeout=18)
        report['prepare_s']=time.monotonic()-began
        codes,metrics=pool.submit(render,0,480,source.parameters,(2.,1.65)).result(timeout=2)
        report.update(ok=True,prepare_result=result,code_min=int(codes.min()),code_max=int(codes.max()),samples=len(codes),metrics=metrics)
    except Exception as exc:
        report.update(ok=False,error=repr(exc),elapsed=time.monotonic()-began)
    finally:
        processes=list(pool._processes.values())
        pool.shutdown(wait=False,cancel_futures=True)
        for process in processes:
            if not report.get('ok') and process.is_alive():process.terminate()
            process.join(2)
        report['processes_closed']=all(not p.is_alive() for p in processes)
    folder=ROOT/'diagnosticos/resultados_v20/synth_play_local_20261104';folder.mkdir(exist_ok=True)
    (folder/'prepare_panel_defaults.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    print(json.dumps(report,default=str),flush=True)

if __name__=='__main__':main()
