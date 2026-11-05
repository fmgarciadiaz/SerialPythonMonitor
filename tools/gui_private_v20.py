#!/usr/bin/env python3
"""GUI smoke with a separate exact firmware binding, never a receipt override."""
import argparse
from contextlib import nullcontext
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.private_v20_pair import ENV,expected_identity as binding_identity,connection as private_connection


def enable_internal_2m(module,bits,rate):
    """Expose only the existing ADC8/80-tick profile in this private process."""
    from monitor.v20.receiver.unoq_acquisition import Configuration
    if (bits,rate)!=(8,2000000):raise ValueError('Only the existing private ADC8/2MS/s profile is allowed')
    config=Configuration(bits,rate)
    if not (config._native.get('internal_only') and config.period==80
            and config.node_pairs==3488 and config.channels==1):
        raise ValueError('Private 2MS/s geometry changed')
    return expose_private_rate(module,bits,rate)


def expose_private_rate(module,bits,rate):
    old_rates,old_supported,old_catalog=module.RATES,module._configuration_supported,module.catalog_rates
    module.RATES=tuple(sorted(set(old_rates)|{rate}))
    module._configuration_supported=lambda b,r:(b,r)==(bits,rate) or old_supported(b,r)
    def catalog(b):
        rows=old_catalog(b)
        return rows if b!=bits or rows is None else set(rows)|{rate}
    module.catalog_rates=catalog
    def restore():
        module.RATES=old_rates;module._configuration_supported=old_supported;module.catalog_rates=old_catalog
    return restore


def enable_internal_audio_2m():
    """Permit the exact unqualified tuple solely for this private audio trial."""
    from monitor.v20 import radio_output,radio_output_panel
    originals=[(module,module.acquisition_error) for module in (radio_output,radio_output_panel)]
    def guard(config):
        native=getattr(config,'_native',None) or {}
        if (getattr(config,'bits',None),getattr(config,'rate',None),native.get('ticks'),
                native.get('node_pairs'),native.get('channels'))==(8,2000000,80,3488,1):
            return None
        return originals[0][1](config)
    for module,_ in originals:module.acquisition_error=guard
    def restore():
        for module,original in originals:module.acquisition_error=original
    return restore



def private_receiver_options(binding):
    options=dict(connection_factory=private_connection,capture_lifecycle=True,
                 snapshot_dir=str(Path(binding).resolve().parent/'private_gui_sessions'))
    recovery=os.environ.get('ARDUSCOPIO_PRIVATE_RECOVERY_SECONDS')
    if recovery is not None:
        if recovery!='10':raise ValueError('Private recovery override must be exactly 10 seconds')
        options['recovery_seconds']=10
    return options


def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--firmware-binding',required=True,type=Path)
    parser.add_argument('--legacy-cadence',action='store_true',help='Private baseline: disable balanced RF cadence')
    parser.add_argument('--allow-internal-2m',action='store_true',help='Private GUI only; does not change the public rate catalogue')
    parser.add_argument('--allow-private-adc',action='store_true',help='Only source-bound ADC10/12 diagnostic candidates')
    parser.add_argument('--trace-numpy-any',action='store_true',
                        help='Private native-crash callsite journal for main-thread NumPy any()')
    args,remaining=parser.parse_known_args()
    os.environ[ENV]=str(args.firmware_binding.resolve())
    from tools.relay_wire_metrics_v19 import ENV as METRICS_ENV
    os.environ[METRICS_ENV]=str(args.firmware_binding.resolve().parent/'wire_metrics.json')
    serial_parser=argparse.ArgumentParser(add_help=False);serial_parser.add_argument('--serial',required=True)
    serial,_=serial_parser.parse_known_args(remaining);binding_identity(serial.serial)
    target_parser=argparse.ArgumentParser(add_help=False)
    target_parser.add_argument('--bits',type=int,default=8)
    target_parser.add_argument('--rate',type=int,default=1600000)
    target,_=target_parser.parse_known_args(remaining)
    if args.allow_private_adc:
        import json
        from tools.private_rate_profiles_v20 import PRIVATE_PROFILES,diagnostic_profiles
        if not any(b==target.bits and 160000000//ticks==target.rate for b,ticks,_ in PRIVATE_PROFILES):
            raise ValueError('Unsupported private GUI ADC candidate')
        binding=json.loads(args.firmware_binding.read_text())
        if binding.get('private_profile')!={'bits':target.bits,'rate':target.rate}:
            raise ValueError('GUI target does not match private ADC binding')
        with diagnostic_profiles(target.bits,(target.rate,)):
            return run_smoke(args,remaining,target)
    return run_smoke(args,remaining,target)


def run_smoke(args,remaining,target):
    from tools.relay_wire_metrics_v19 import set_metrics_profile
    from monitor.v20.receiver.unoq_acquisition import Configuration
    set_metrics_profile(target.bits,target.rate,configuration=Configuration,allow_non_native=True)
    from monitor.v20.io import receiver_process
    original=receiver_process.ReceiverProcess
    class PrivateFirmwareReceiver(original):
        def __init__(self,*values,**options):
            options.update(private_receiver_options(args.firmware_binding))
            super().__init__(*values,**options)
    receiver_process.ReceiverProcess=PrivateFirmwareReceiver
    sys.argv=[str(ROOT/'tools/gui_live_smoke_v20.py'),*remaining]
    from tools.qt_timer_trace_v20 import install
    install(args.firmware_binding.resolve().parent/'qt_single_shot.jsonl')
    from tools.gui_live_smoke_v20 import main as smoke
    from monitor.v20 import app as app_module
    restore_internal=(enable_internal_2m(app_module,target.bits,target.rate) if args.allow_internal_2m else
                      expose_private_rate(app_module,target.bits,target.rate) if args.allow_private_adc else lambda:None)
    restore_audio=enable_internal_audio_2m() if args.allow_internal_2m else lambda:None
    from monitor.v20.app import SerialMonitorWindow
    original_eligible=SerialMonitorWindow._balanced_temporal_eligible
    if args.legacy_cadence:SerialMonitorWindow._balanced_temporal_eligible=lambda self:False
    from monitor.v20 import temporal_raster
    original_raster=temporal_raster.RasterProcess
    workers=int(os.environ.get('ARDUSCOPIO_PRIVATE_RASTER_WORKERS','1'))
    if workers not in (1,2,4):raise ValueError('Invalid private raster worker count')
    if workers!=1:
        from tools.private_raster_tiles_v20 import TiledRasterProcess
        temporal_raster.RasterProcess=lambda:TiledRasterProcess(workers,original_raster,int(os.environ.get('ARDUSCOPIO_PRIVATE_RASTER_NICE','0')))
    if args.trace_numpy_any:
        from tools.private_numpy_any_trace_v20 import trace_numpy_any
        trace_scope=trace_numpy_any(args.firmware_binding.resolve().parent/'numpy_any_trace.jsonl')
    else:trace_scope=nullcontext()
    try:
        with trace_scope:return smoke()
    finally:
        restore_audio()
        restore_internal()
        SerialMonitorWindow._balanced_temporal_eligible=original_eligible
        temporal_raster.RasterProcess=original_raster
        receiver_process.ReceiverProcess=original


if __name__=='__main__':raise SystemExit(main())
