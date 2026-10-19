"""Bounded WORD experiment with Zephyr byte-based burst lengths corrected."""
import hashlib
import signal
from run import WordProbe, HEADER, interrupted, optimized

TICKS = (114, 112, 110, 108, 106, 104)


class FixedWordProbe(WordProbe):
    def run_probe(self):
        self.variant = 'WORD'
        self.report.update(revision='adc8_spi_word_burst_bytes_fixed_v17',
            plan=dict(bits=[8], nodes=[3456], ticks=list(TICKS), screen_seconds=10,
                      qualification_seconds=[60,120,120,120], max_finalists=3),
            changes=['WORD widths, one beat = four bytes in Zephyr burst fields',
                     'SPI byte frames, FIFO four frames, CRC32 and all validators retained'],
            winners={}, qualification_attempts=[])
        self.save()
        try:
            self.prepare()
            self.report['variants']['WORD'] = self.report['candidate_source_hashes']
            self.save()
            self.candidate.start()
            try:
                optimized.send.start_experimental_relay(self.candidate,self.deployment['candidate_relay'])
            except Exception as exc:
                self.report['first_start_error']=str(exc)
                self.logs('first_start_failure.log')
                self.save()
                self.fast_reset()
            passing=[]
            for ticks in TICKS:
                row=self.trial(8,ticks,3456,10,'word_fixed_screen')
                if not row['ok']:
                    self.trial(8,ticks,3456,10,'word_fixed_repeat_failure',restart=True)
                    break
                passing.append(row)
            integrity=None
            for row in sorted(passing,key=lambda row:row['ticks']):
                if len(self.report['qualification_attempts'])>=3:break
                ticks=row['ticks']
                self.report['qualification_attempts'].append(ticks)
                self.save()
                result=self.qualify(8,ticks,3456)
                if result:
                    integrity=result
                    self.report['winners']['8']={'maximum_tested_integrity':result,
                        'qualified_headroom':result if result['headroom_accepted'] else None}
                    self.save()
                    break
            if integrity and not integrity['headroom_accepted']:
                # Prefer a slower candidate with screening reserve. This is a
                # bounded follow-up, not an exhaustive maximum-headroom search.
                choices=[r for r in passing if r['ticks']>integrity['ticks'] and
                         r.get('headroom_ok')]
                choices.sort(key=lambda r:(r['metrics']['mean_send_headroom']<.14,r['ticks']))
                for row in choices:
                    if len(self.report['qualification_attempts'])>=3:break
                    ticks=row['ticks']
                    self.report['qualification_attempts'].append(ticks)
                    self.save()
                    result=self.qualify(8,ticks,3456)
                    if result and result['headroom_accepted']:
                        self.report['winners']['8']['qualified_headroom']=result
                        break
            self.report['screening_complete']=True
            self.report['ok']=integrity is not None
        except BaseException as exc:
            self.report['error']=str(exc) or type(exc).__name__
            print('EXPERIMENT ERROR',repr(exc),flush=True)
        finally:
            if self.switched:
                try:self.restore()
                except BaseException as exc:self.report['restore_error']=str(exc)
            else:self.report['restored']=True
            self.save()
        print('REPORT',self.folder/'report.json','OK',self.report['ok'],
              'RESTORED',self.report['restored'],flush=True)
        return 0 if self.report['restored'] and self.report['ok'] else 1


if __name__=='__main__':
    signal.signal(signal.SIGTERM,interrupted)
    signal.signal(signal.SIGINT,interrupted)
    if 'SPI_DMA_BYTES = 4;' not in HEADER.read_text():
        raise SystemExit('WORD header required')
    raise SystemExit(FixedWordProbe().run_probe())
