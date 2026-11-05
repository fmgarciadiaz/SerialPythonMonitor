"""Exercise the GUI Prepare Q verification on an already accepted pair only."""
import argparse,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    from monitor.v19.q_support.prepare import load_acceptance
    from monitor.v19.q_support.service import RECEIPT
    from monitor.v19.io.live_connection import installed_identity
    from monitor.v19.app import QtCore,QtWidgets,SerialMonitorWindow
    before=installed_identity(args.serial);acceptance=load_acceptance(RECEIPT)
    if any(before[key]!=value for key,value in acceptance['candidate_identity'].items()):
        raise RuntimeError('Verify-only test requires the already accepted pair; no installation allowed')
    app=QtWidgets.QApplication([]);window=SerialMonitorWindow()
    window.port_combo.addItem(args.serial,args.serial);window.port_combo.setCurrentIndex(window.port_combo.count()-1)
    report=dict(ok=False,firmware_installation_requested=False,before=before)
    began=time.monotonic();started=[False]
    def tick():
        if not started[0]:started[0]=True;window.prepare_q();return
        if window._q_preparation is None:
            report.update(status=window.status_label.text(),seconds=time.monotonic()-began)
            window.close();app.quit()
    timer=QtCore.QTimer();timer.timeout.connect(tick);timer.start(100)
    window.show();app.exec()
    after=installed_identity(args.serial)
    report.update(after=after,identity_unchanged=after==before)
    report['ok']='preparado' in report['status'].lower() and report['identity_unchanged']
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0 if report['ok'] else 1

if __name__=='__main__':raise SystemExit(main())
