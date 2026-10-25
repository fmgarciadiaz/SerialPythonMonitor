"""Run a private high-rate GUI against an isolated Q app; restore production V18."""
import argparse,json,os,signal,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

def main():
    from experimentos.fs_max_v18.run_probe import Hardware,plan
    from experimentos.fs_max_v18.probe_journal import ProbeJournal
    from monitor.v18.board_owner import board_owner
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',action='store_true')
    p.add_argument('--recipe',choices=('spi40_10_12','word14','full8','wordping','spi16','batch2','batchfast','batchstack','batcharena','batchquickack','trace8','trace8time'),required=True)
    p.add_argument('--bits',type=int,required=True);p.add_argument('--ticks',type=int,required=True)
    p.add_argument('--hold',type=float,default=60)
    p.add_argument('--keep-display-awake',action='store_true',
        help='Diagnostic scoped display/user activity assertions; no preferences changed')
    p.add_argument('--render-interval-ms',type=int,choices=range(16,251))
    p.add_argument('--profile-render',action='store_true')
    p.add_argument('--macos-activity',choices=('user','critical'))
    p.add_argument('--occlusion-test',action='store_true',help='Hide test GUI at 45 s, show again at 85 s')
    args=p.parse_args()
    if not 0<args.hold<=120:raise ValueError('hold must be in (0,120]')
    rows=plan([args.bits],15,[args.ticks],args.recipe)
    if len(rows)!=1:raise ValueError('Select exactly one profile')
    if not args.run:print(json.dumps(rows,indent=2));return 0
    folder=ROOT/'diagnosticos/resultados_v18'/time.strftime('gui_private_%Y%m%d_%H%M%S');folder.mkdir(parents=True)
    report=dict(recipe=args.recipe,profile=rows[0],gui_ok=False,hardware_restored=False)
    report['activity_overrides']={role:os.environ.get('MONITOR_V18_'+role.upper()+'_ACTIVITY','default')
                                  for role in ('parent','receiver','synth')}
    report['occlusion_test']=args.occlusion_test
    report['compact_adc8_ipc']=os.environ.get('MONITOR_V18_COMPACT_ADC8_IPC')=='1'
    journal=ProbeJournal(folder/'report.json',report);hw=Hardware(folder,report);captured=False;child=None;display_guard=None
    try:
        with board_owner(hw.original.serial,'private GUI setup'):
            hw.capture();captured=True;hw.prepare();hw.restart()
            report['candidate_identity']=hw.candidate_identity();journal.save()
        # No administrative Q I/O while the GUI child holds the acquisition lock.
        env=dict(os.environ,SCOPE_V18_GUI_RECIPE=args.recipe,
                 SCOPE_V18_GUI_TARGET=f'{args.bits}:{args.ticks}')
        rate=int(rows[0]['rate']);duration=max(50,args.hold+25)
        command=[sys.executable,str(ROOT/'tools/gui_experimental_v18.py'),
                 '--serial',hw.original.serial,'--output',str(folder/'gui.json'),
                 '--bits',str(args.bits),'--rate',str(rate),'--frequency-khz','400',
                 '--duration',str(duration),'--hold-radio-seconds',str(args.hold),
                 '--scan','--wav','--fm','--voices','20']
        if args.render_interval_ms:command+=['--render-interval-ms',str(args.render_interval_ms)]
        if args.profile_render:command+=['--profile-render']
        if args.macos_activity:command+=['--macos-activity',args.macos_activity]
        if args.occlusion_test:command+=['--hide-at-seconds','45','--show-at-seconds','85']
        if args.keep_display_awake:
            if sys.platform!='darwin':raise RuntimeError('Display comparison requires macOS')
            display_guard=subprocess.Popen(['caffeinate','-du','-t','600'])
            time.sleep(.1)
            if display_guard.poll() is not None:raise RuntimeError('Display assertion could not start')
            report['display_guard']=dict(pid=display_guard.pid,timeout_seconds=600,
                purpose='prevent display idle sleep and declare user activity for bounded comparison')
            display_state=subprocess.run(['pmset','-g','assertions'],capture_output=True,timeout=5)
            (folder/'display_assertions_start.bin').write_bytes(display_state.stdout)
            report['display_assertions_start']=display_state.stdout.decode('utf-8',errors='replace')
        report['gui_command']=command;report['phase']='gui';journal.save()
        with (folder/'gui.log').open('w') as log:
            child=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT)
            child.wait(timeout=duration+120)
        report['gui_exit_code']=child.returncode
        if (folder/'gui.json').exists():
            evidence=json.loads((folder/'gui.json').read_text())
            report['gui_ok']=child.returncode==0 and not evidence['errors'] and all(evidence['assertions'].values())
    except BaseException as exc:report['error']=repr(exc)
    finally:
        if child is not None and child.poll() is None:
            child.send_signal(signal.SIGINT)
            try:child.wait(timeout=90)
            except subprocess.TimeoutExpired:report['gui_close_error']='GUI still owns Q; no forced hardware takeover'
        if display_guard is not None:
            guard_report=report.setdefault('display_guard',{})
            guard_report['exit_code_before_release']=display_guard.poll()
            try:
                display_guard.terminate();display_guard.wait(timeout=5)
                guard_report['released']=True
            except Exception as exc:guard_report['release_error']=repr(exc)
        if captured:
            try:
                with board_owner(hw.original.serial,'private GUI restore'):
                    try:
                        logs=hw.original.run('shell','docker logs serialmonitor-usb-stream-v18 2>&1',capture=True).stdout
                        (folder/'candidate_relay.log').write_text(logs)
                    except Exception as exc:report['candidate_log_error']=repr(exc)
                    report['restoration']=hw.restore()
                    report['hardware_restored']=report['restoration']['hardware_restored']
            except BaseException as exc:report['restore_error']=repr(exc)
        report['phase']='closed';report['ok']=report['gui_ok'] and report['hardware_restored'];journal.save()
    print(folder/'report.json',flush=True)
    return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
