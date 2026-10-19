"""Qualify the BYTE candidate screened by the A/B campaign; preserve its evidence."""
import signal
from run import WordProbe, HEADER, interrupted, optimized


class ByteQualification(WordProbe):
    def run_probe(self):
        self.report.update(revision='adc8_spi_byte_crcsize7_qualification_v17',
            screening_reference='probe_1400_20261015_182804/report.json',
            qualification_variant='BYTE',
            word_status='READY timeout before first frame; no rate conclusion')
        self.save()
        try:
            self.prepare()
            self.report['variants']['BYTE']=self.report['candidate_source_hashes']
            self.save()
            self.candidate.start()
            optimized.send.start_experimental_relay(self.candidate,self.deployment['candidate_relay'])
            for ticks in (112,113):
                winner=self.qualify(8,ticks,3456)
                if winner:
                    self.report['winners']['8']=winner
                    break
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
        return 0 if self.report['restored'] and self.report['ok'] else 1


if __name__=='__main__':
    signal.signal(signal.SIGTERM,interrupted)
    signal.signal(signal.SIGINT,interrupted)
    if 'SPI_DMA_BYTES = 1;' not in HEADER.read_text():
        raise SystemExit('BYTE header required')
    raise SystemExit(ByteQualification().run_probe())
