"""Prueba física V15 sin GUI ni teclado MIDI; restaura ADC y apaga DAC."""
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
import json
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from monitor.historico.v15.receiver.unoq_usb import Connection
from monitor.historico.v15.receiver.unoq_config_receiver import OutputReceiver
from monitor.historico.v15.receiver.unoq_acquisition import Configuration
from monitor.historico.v15.receiver.unoq_switch import Mode
from monitor.historico.v15.receiver.unoq_generator import GeneratorConfig
from monitor.historico.v15.receiver.unoq_wav import State
from monitor.historico.v15.fm_source import FMSource, FMParameters
from monitor.historico.v15.fm_feedback import warmup


def main():
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    folder = ROOT / 'diagnosticos/resultados_cierre'
    folder.mkdir(exist_ok=True)
    report = dict(serial='1060031107', firmware='v13_pulse', gui=False,
                  midi='notas simuladas, sin teclado físico', cases=[], ok=False)
    path = folder / f'{stamp}_v15.json'
    warmup()
    count = 0
    last = []
    def collect(batch):
        nonlocal count, last
        count += len(batch)
        last = batch
    with Connection(report['serial']) as connection:
        receiver = OutputReceiver(connection, collect, print)
        receiver.select(Mode.SPI)
        prior = receiver.config
        report['adc_inicial'] = asdict(prior)
        report['generador_inicial'] = asdict(receiver.generator())
        try:
            def await_audio_ack():
                deadline = time.monotonic() + 5
                while receiver.wav_pending and time.monotonic() < deadline:
                    receiver.pump()
                if receiver.wav_pending:
                    raise TimeoutError('Sin ACK de audio')
            receiver.configure(Configuration(14, 100000))
            receiver.wav_request()
            await_audio_ack()
            for rate in (20000, 40000):
                n = rate * 120
                codes = np.rint((1.65 + np.sin(2*np.pi*997*np.arange(n)/rate)) * 4095/3.3).astype('<u2')
                entry = dict(kind='wav', rate=rate, adc=asdict(receiver.config))
                report['cases'].append(entry)
                before = count
                start = time.monotonic()
                receiver.wav_request(1, codes, rate)
                while time.monotonic()-start < 135:
                    receiver.pump()
                    status = receiver.wav_status
                    if status and status.state in (State.DONE, State.UNDERRUN, State.FAULT):
                        break
                status = receiver.wav_status
                entry.update(state=status.state.name, played=status.played, total=n,
                             adc_pairs=count-before, elapsed=time.monotonic()-start)
                if status.state != State.DONE or status.played != n:
                    raise RuntimeError(str(entry))
                entry['ok'] = True
                print(json.dumps(entry), flush=True)
                path.write_text(json.dumps(report, indent=2)+'\n')
            receiver.configure(Configuration(14, 40000))
            params = FMParameters(preset='DX Piano', waveform='fm', osc2_wave='fm',
                                  osc2_mix=.25, osc2_fm_ratio=14, osc2_fm_amount=.55,
                                  notes=tuple((note,100) for note in range(48,57)))
            source = FMSource(20000, params)
            source.diagnostic_path = folder / f'{stamp}_synth20.jsonl'
            receiver.on_wav = source.observe_status
            receiver.set_wav_levels(2.5, 1.65)
            receiver.wav_request(1, source, 20000)
            start = time.monotonic()
            before = count
            next_notes = start + 2
            next_print = start + 30
            generation = 0
            while time.monotonic()-start < 600:
                receiver.pump()
                status = receiver.wav_status
                if status and status.state in (State.DONE, State.UNDERRUN, State.FAULT):
                    raise RuntimeError('Synth interrumpido: '+str(status))
                now = time.monotonic()
                if now >= next_notes:
                    generation += 1
                    notes = tuple((note, 70+generation%50) for note in range(48+generation%12,57+generation%12)) if generation%3 else ()
                    source.update(replace(params, notes=notes, virtual_sustain=bool(generation%2)))
                    next_notes = now + 2
                if now >= next_print:
                    print(f'Synth20: {now-start:.0f}/600 s, ADC {count-before}, render máximo {source.max_render_ms:.2f} ms', flush=True)
                    next_print = now + 30
            report['cases'].append(dict(kind='synth', rate=20000, seconds=600,
                voices=9, adc=asdict(receiver.config), adc_pairs=count-before,
                max_render_ms=source.max_render_ms, min_queued=source._min_queued,
                max_ack_gap_ms=source._max_ack_gap*1000, ok=True))
            receiver.wav_request(3)
            await_audio_ack()
            receiver.on_wav = lambda status: None
            receiver.set_wav_levels(2, 1.65)
            for config in (GeneratorConfig(wave=1,frequency=997000,low=807,high=3288),
                           GeneratorConfig(wave=4,duration=100,duration_us=1,low=807,high=3288),
                           GeneratorConfig(wave=1,mode=1,frequency=20000,final_frequency=2000000,duration=2000,low=807,high=3288),
                           GeneratorConfig(wave=1,mode=2,frequency=20000,final_frequency=2000000,duration=2000,low=807,high=3288)):
                response = receiver.generator(config)
                start = time.monotonic()
                while time.monotonic()-start < (2.3 if config.mode else .3):
                    receiver.pump()
                report['cases'].append(dict(kind='generator', config=asdict(config), reply=asdict(response)))
            report['ok'] = True
        except Exception as exc:
            report['error'] = str(exc)
            raise
        finally:
            try:
                receiver.shutdown_output()
                report['salida_apagada_confirmada'] = True
                receiver.configure(prior)
                report['adc_restaurado'] = receiver.config == prior
            except Exception as exc:
                report['restoration_error'] = str(exc)
                report['ok'] = False
            receiver.close()
            path.write_text(json.dumps(report, indent=2)+'\n')
            print('Reporte: '+str(path), flush=True)


if __name__ == '__main__':
    main()
