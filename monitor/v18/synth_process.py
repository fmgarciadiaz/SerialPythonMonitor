"""Dedicated Synth renderer: mutable controls cross as immutable parameters."""
_source = None

def initialize_worker():
    """Keep the audio renderer scheduled while its bounded pool is alive."""
    from multiprocessing.util import Finalize
    from monitor.v18.process_activity import MacActivity, acquisition_activity_mode
    mode = acquisition_activity_mode('synth')
    if mode == 'off':
        return
    activity = MacActivity(mode)
    # multiprocessing runs its finalizers on normal pool-worker shutdown.
    # This owns only this child; system/display idle sleep remains allowed.
    Finalize(None, activity.close, exitpriority=10)

def prepare(rate, parameters):
    global _source
    from monitor.v18.fm_source import FMSource
    _source=FMSource(rate,parameters)
    _source.prepare_audio()
    return True

def render(start,end,parameters,levels):
    if _source is None:raise RuntimeError('Synth renderer not prepared')
    if _source.parameters != parameters:_source.update(parameters)
    codes=(_source[start:end] if levels is None else
           _source.render_dac_codes(start,end,*levels))
    return codes,dict(position=_source.position,active_notes=tuple(_source.voices),
        max_render_ms=_source.max_render_ms,slow_render_blocks=_source.slow_render_blocks,
        compressor_gain=_source.compressor_gain)
