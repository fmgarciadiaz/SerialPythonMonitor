"""Explicit diagnostic entry point; private profiles never persist to monitor files.

The coordinator sets SCOPE_V18_GUI_RECIPE and SCOPE_V18_GUI_TARGET (bits:ticks).
Spawn children repeat this bootstrap before unpickling acquisition objects.
"""
import os,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
RECIPE=os.environ.get('SCOPE_V18_GUI_RECIPE')
TARGET=os.environ.get('SCOPE_V18_GUI_TARGET')
APPS={'installed':'scope-v18-main-1',
      'rateonly':'scope-v18-rate-probe-rateonly-main-1',
      'rateonly2':'scope-v18-rate-probe-rateonly2-main-1',
      'catalog':'scope-v18-rate-probe-catalog-main-1',
      'adc16':'scope-v18-rate-probe-adc16-main-1',
      'spi40_10_12':'scope-v18-rate-probe-spi40-main-1',
      'word14':'scope-v18-rate-probe-word14-main-1',
      'full8':'scope-v18-rate-probe-full8-main-1',
      'wordping':'scope-v18-rate-probe-wordping-main-1',
      'spi16':'scope-v18-rate-probe-spi16-main-1',
      'batch2':'scope-v18-rate-probe-batch2-main-1',
      'batchfast':'scope-v18-rate-probe-batchfast-main-1',
      'batchstack':'scope-v18-rate-probe-batchstack-main-1',
      'batcharena':'scope-v18-rate-probe-batcharena-main-1',
      'batchquickack':'scope-v18-rate-probe-batcharena-main-1',
      'trace8':'scope-v18-rate-probe-wordping-main-1',
      'trace8time':'scope-v18-rate-probe-wordping-main-1'}

def selected_profile(recipe,target):
    if recipe not in APPS:raise ValueError('Unknown diagnostic recipe')
    bits,ticks=map(int,target.split(':'))
    folder=ROOT/'experimentos/fs_max_v18'
    if recipe!='installed':folder=folder/recipe
    profiles=json.loads((folder/'candidate_profiles.json').read_text())
    selected=[p for p in profiles if p['bits']==bits and p['ticks']==ticks and not p.get('purpose')]
    if len(selected)!=1:raise ValueError('Diagnostic profile must be unique')
    return dict(selected[0],internal_only=False,integration_pending=False)

def experimental_connection(port):
    from monitor.v18.io.live_connection import installed_connection,installed_identity
    return installed_connection(port,identity=lambda serial:installed_identity(serial,expected_app=APPS[RECIPE]))

def check_child_profile(channel,factory):
    from monitor.v18.receiver.unoq_acquisition import Configuration
    config=Configuration(PROFILE['bits'],160000000//PROFILE['ticks'])
    channel.send(dict(bits=config.bits,ticks=config.period,node_pairs=config.node_pairs,
                      factory=factory.__name__))
    channel.close()

if RECIPE is not None:
    PROFILE=selected_profile(RECIPE,TARGET)
    from monitor.v18.receiver import unoq_native
    unoq_native.PROFILES=tuple(unoq_native.PROFILES)+(PROFILE,)
    from monitor.v18.io import receiver_process
    BaseReceiverProcess=receiver_process.ReceiverProcess
    class ExperimentalReceiverProcess(BaseReceiverProcess):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,connection_factory=experimental_connection,capture_lifecycle=True,**kwargs)
    receiver_process.ReceiverProcess=ExperimentalReceiverProcess
    # This test entry point can exercise only the exact selected private profile.
    from monitor.v18 import radio_output
    original_error=radio_output.acquisition_error
    def diagnostic_error(config):
        if (config.bits,config.period,config.node_pairs)==(PROFILE['bits'],PROFILE['ticks'],PROFILE['node_pairs']):return None
        return original_error(config)
    radio_output.acquisition_error=diagnostic_error
    if RECIPE in ('rateonly','rateonly2'):
        # Extend the private target only; retain production's fast auxiliaries.
        from monitor.v18 import radio_multiscan
        from monitor.v18.receiver.unoq_acquisition import Configuration
        original_scan_profiles=radio_multiscan.scan_profiles
        def diagnostic_scan_profiles(original):
            if (original.bits,original.period,original.node_pairs)==(PROFILE['bits'],PROFILE['ticks'],PROFILE['node_pairs']):
                anchors=({8:1860465,10:1333333,12:1095890,14:941176} if RECIPE=='rateonly2' else {8:1818181,10:1311475,12:1095890,14:909090})
                baseline_rate=anchors[original.bits]
                profiles=original_scan_profiles(Configuration(original.bits,baseline_rate))
                return [original,*profiles[1:]] if len(profiles)==3 else []
            return original_scan_profiles(original)
        radio_multiscan.scan_profiles=diagnostic_scan_profiles

if __name__=='__main__':
    if RECIPE is None:raise SystemExit('Use probe_gui_live_v18.py --run for exclusive setup and restoration')
    if sys.argv[1:]==['--check-bootstrap']:
        import multiprocessing
        ctx=multiprocessing.get_context('spawn');parent,child=ctx.Pipe(duplex=False)
        process=ctx.Process(target=check_child_profile,args=(child,experimental_connection))
        process.start();process.join(15)
        if process.is_alive():process.terminate();process.join();raise SystemExit('Bootstrap timeout')
        if process.exitcode:raise SystemExit(process.exitcode)
        print(json.dumps(parent.recv()));raise SystemExit(0)
    from tools.gui_live_smoke_v18 import main
    raise SystemExit(main())
