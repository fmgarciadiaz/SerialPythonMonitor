"""Isolated ADC8 BYTE/WORD SPI DMA A/B, preserving the live V17 installation."""
import json
import hashlib
from pathlib import Path
import signal
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
import experimentos.maxfreq_optimized_v17.run as optimized
from tools.unoq import Board

EXP=Path(__file__).resolve().parent
optimized.EXP=EXP
optimized.send.EXP=EXP
HEADER=EXP/'arduino/historico/v16/oscilloscope/sketch/spi_word_experiment.h'


class WordProbe(optimized.OptimizedSweep):
    def __init__(self):
        super().__init__()
        config=dict(self.candidate.config)
        config['local_app']='experimentos/adc8_spi_word_v17/arduino/historico/v16/oscilloscope'
        self.candidate=Board(config)
        self.report.update(revision='adc8_spi_dma_byte_word_ab_v17',variants={},
            plan={'bits':[8],'nodes':[3456],'ticks':[114,113,112],
                  'screen_seconds':10,'qualification_seconds':[60,120,120,120]},
            production_sources_modified=False,analog='Not measured')
        self.variant='BYTE'

    def trial(self,*args,**kwargs):
        result=super().trial(*args,**kwargs)
        result['variant']=self.variant
        self.save()
        return result

    def load_word(self):
        # Stop both acquisition and relay before rebuilding the disposable app.
        optimized.send.usb_stream.stop(self.candidate);self.candidate.stop()
        text=HEADER.read_text()
        if 'SPI_DMA_BYTES = 1;' not in text:raise RuntimeError('Unexpected baseline header')
        HEADER.write_text(text.replace('SPI_DMA_BYTES = 1;','SPI_DMA_BYTES = 4;'))
        files=self.candidate.check_sources()
        self.candidate.push_sources(files,self.candidate.remote)
        self.report['variants']['WORD']={p.relative_to(self.candidate.local).as_posix():
            hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        self.variant='WORD';self.save()
        self.candidate.start()
        optimized.send.start_experimental_relay(self.candidate,self.deployment['candidate_relay'])
        self.dirty=False

    def run_probe(self):
        self.save()
        try:
            self.prepare()
            self.report['variants']['BYTE']=self.report['candidate_source_hashes']
            self.save()
            self.candidate.start()
            optimized.send.start_experimental_relay(self.candidate,self.deployment['candidate_relay'])
            for ticks in (114,113,112):
                result=self.trial(8,ticks,3456,10,'byte_screen')
                if not result['ok']:
                    self.trial(8,ticks,3456,10,'byte_repeat_failure',restart=True)
                    break
            self.load_word()
            passing=[]
            for ticks in (114,113,112):
                result=self.trial(8,ticks,3456,10,'word_screen')
                if not result['ok']:
                    self.trial(8,ticks,3456,10,'word_repeat_failure',restart=True)
                    break
                passing.append(ticks)
            for ticks in sorted(t for t in passing if t<114):
                winner=self.qualify(8,ticks,3456)
                if winner:
                    self.report['winners']['8']=winner
                    break
            self.report['screening_complete']=True
            self.report['ok']=bool(self.report['winners'])
        except BaseException as exc:
            self.report['error']=str(exc) or type(exc).__name__
            print('EXPERIMENT ERROR',repr(exc),flush=True)
        finally:
            if self.switched:
                try:self.restore()
                except BaseException as exc:self.report['restore_error']=str(exc)
            else:self.report['restored']=True
            self.save()
        print('REPORT',self.folder/'report.json','GAIN_ACCEPTED',self.report['ok'],
              'RESTORED',self.report['restored'],flush=True)
        return 0 if self.report['restored'] else 1


def interrupted(signum,frame):
    raise KeyboardInterrupt(f'signal {signum}')


if __name__=='__main__':
    signal.signal(signal.SIGTERM,interrupted)
    signal.signal(signal.SIGINT,interrupted)
    if 'SPI_DMA_BYTES = 1;' not in HEADER.read_text():
        raise SystemExit('Restore experimental BYTE header before starting a new A/B run')
    raise SystemExit(WordProbe().run_probe())
