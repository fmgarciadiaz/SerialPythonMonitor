"""Explicit supported WAV playback cases; does not open Qt or contact Q."""
import math


STABILITY_MATRIX = tuple((bits,100000,50000) for bits in (8,10,12,14)) + ((16,76226,50000),)


def select_window_configuration(window, config):
    """Expose a supported diagnostic legacy rate without selecting index -1."""
    bits_index = window.config_bits_combo.findData(config.bits)
    if bits_index<0: raise ValueError('Resolución ausente del selector')
    window.config_bits_combo.setCurrentIndex(bits_index)
    rate_index = window.config_rate_combo.findData(config.rate)
    if rate_index<0:
        window.config_rate_combo.addItem(f'{config.rate} Hz (diagnóstico)',config.rate)
        rate_index = window.config_rate_combo.findData(config.rate)
    window.config_rate_combo.setCurrentIndex(rate_index)
    window._auto_apply_timer.stop()
    if (window.config_bits_combo.currentData(),window.config_rate_combo.currentData())!=(config.bits,config.rate):
        raise ValueError('Selector de adquisición no coincide con el caso')


def near_eof_delta(duration, played, rate, tail=3.):
    """Relative seek to the final seconds of this file, independent of length."""
    if not math.isfinite(duration) or duration<=0 or rate<=0:
        raise ValueError('Duración y tasa válidas requeridas')
    return max(0.,duration-tail)-played/rate


def select_cases(argv):
    duration = float(argv[argv.index('--seconds')+1]) if '--seconds' in argv else 120 if '--long' in argv else 18
    matrix = ((16,76226,50000),(16,76226,40000),(16,76226,20000)) if '--adc16' in argv else ((14,100000,50000),) if '--long' in argv else tuple((bits,rate,audio) for bits,rate in ((8,40000),(14,100000)) for audio in (20000,40000,50000))
    if '--case16' in argv: matrix = ((16,76226,50000),)
    if '--critical-pair' in argv: matrix = ((16,76226,50000),(14,100000,50000))
    if '--qualify16' in argv: matrix,duration = ((16,76226,50000),)*3,120
    if '--controls' in argv: matrix,duration = ((16,76226,50000),),35
    if '--select-only' in argv: matrix,duration = ((8,1600000,50000),),10
    custom = '--case' in argv or '--stability-matrix' in argv
    if custom and any(flag in argv for flag in ('--adc16','--long','--case16','--critical-pair','--qualify16','--controls','--select-only')):
        raise ValueError('No combinar una matriz explícita con selectores anteriores')
    if '--case' in argv and '--stability-matrix' in argv:
        raise ValueError('Elegir --case o --stability-matrix')
    if '--stability-matrix' in argv: matrix = STABILITY_MATRIX
    if '--case' in argv:
        index = argv.index('--case')+1
        try:
            case = tuple(int(x) for x in argv[index:index+3])
            if len(case)!=3: raise ValueError()
        except ValueError as exc:
            raise ValueError('--case requiere BITS ADC_HZ AUDIO_HZ') from exc
        matrix = (case,)
    if not math.isfinite(duration) or duration<=0:
        raise ValueError('Duración positiva y finita requerida')
    for bits,rate,audio in matrix:
        if bits not in (8,10,12,14,16) or rate<=0 or audio not in (20000,40000,50000):
            raise ValueError('Caso WAV inválido')
        if rate>100000 and '--select-only' not in argv:
            raise ValueError('WAV público requiere adquisición hasta100kHz; no se omite la protección')
    return matrix,duration
