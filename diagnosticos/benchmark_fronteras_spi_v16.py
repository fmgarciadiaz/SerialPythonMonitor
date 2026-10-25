"""Comparación ABBA de recepción SPI validada, sin conectar al Q."""
import importlib.util,sys,time,json
from pathlib import Path
import numpy as np
from monitor.historico.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.historico.v16.receiver.unoq_acquisition import Configuration
from monitor.historico.v16.receiver.unoq_switch import Mode
from diagnosticos.benchmark_latencia_host_v16 import adc_payload

def main():
    spec=importlib.util.spec_from_file_location('receiver_reference','respaldos/synth/20261010_spi_emit/unoq_config_receiver.py')
    old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
    payload=adc_payload(8);expected=None;rows=[]
    for label in ('before','after','after','before'):
        cls=old.OutputReceiver if label=='before' else OutputReceiver
        timings=[]
        for trial in range(35):
            batches=[];r=cls(None,batches.append);r.visible=True
            r.config=Configuration(14,100000);r.mode=Mode.SPI;r.next_index=0
            began=time.perf_counter();r.decoder.feed(payload);r._process_decoder_events()
            elapsed=(time.perf_counter()-began)*1000
            if trial>=5:timings.append(elapsed)
            if expected is None:expected=batches
            else:assert batches==expected
            assert r.next_index==16384 and r.timestamp==163830
        rows.append(dict(variant=label,median_ms=float(np.median(timings)),p95_ms=float(np.percentile(timings,95)),samples=16384,exact=True))
    out=Path('diagnosticos/resultados_piano/eficiencia_v16/20261010_spi_emit.json')
    out.write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
