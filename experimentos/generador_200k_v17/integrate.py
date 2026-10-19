"""Apply per-wave limits only after physical qualification has passed."""
import json,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent

def apply(evidence):
 r=json.loads(Path(evidence).read_text())
 assert r['ok'] and r['restored'] and r['final_identity']==r['prior_identity']
 for wave,hz in ((1,150000),(0,200000)):
  cases=[c for c in r['cases'] if c['wave']==wave and c['requested_hz']==hz]
  assert len(cases)==3 and all(c['reply_matches'] and c['running'] and r.get('qualification_requested_seconds',0)>=120 and c['adc_status'].get('dropped')==0 and c['adc_status'].get('fatal')==0 for c in cases)
 for name in ('generator_protocol.h','generator_timing.h'):shutil.copy2(EXP/'include'/name,ROOT/'arduino/v17/oscilloscope/sketch'/name)
 p=ROOT/'arduino/v17/tests/generator_timing.cpp';s=p.read_text();s=s.replace('c.frequency=50000001;assert(!scope_gen::valid(c));','''c.frequency=c.final_frequency=150000000;assert(scope_gen::valid(c));
 assert(generator::points_for(c)==6);
 c.frequency=150000001;assert(!scope_gen::valid(c));
 c.wave=0;c.frequency=c.final_frequency=200000000;assert(scope_gen::valid(c));
 assert(generator::points_for(c)==2);
 c.frequency=200000001;assert(!scope_gen::valid(c));''');p.write_text(s)
 p=ROOT/'monitor/v17/receiver/unoq_generator.py';s=p.read_text();s=s.replace('MAX_FREQUENCY_MHZ = 50000000','''MAX_FREQUENCY_MHZ = 200000000

def waveform_limit(wave):
    return 200000000 if wave == 0 else 150000000 if wave == 1 else 50000000''',1)
 s=s.replace('self.frequency <= MAX_FREQUENCY_MHZ','self.frequency <= waveform_limit(self.wave)').replace('self.final_frequency <= MAX_FREQUENCY_MHZ','self.final_frequency <= waveform_limit(self.wave)')
 s=s.replace('Generador: frecuencia 0,1 Hz–50 kHz,','Generador: frecuencia fuera del rango de la onda (cuadrada 200 kHz, seno 150 kHz, resto 50 kHz),')
 p.write_text(s)
 p=ROOT/'arduino/v17/relay/config_relay_protocol.h';s=p.read_text();s=s.replace('get32(c+4)>50000000','get32(c+4)>(c[2]==3?50000000U:c[0]==0?200000000U:c[0]==1?150000000U:50000000U)').replace('get32(c+8)>50000000','get32(c+8)>(c[2]==3?50000000U:c[0]==0?200000000U:c[0]==1?150000000U:50000000U)');p.write_text(s)
 p=ROOT/'monitor/v17/app.py';s=p.read_text()
 s=s.replace('.1*500000**(value/1000)', '.1*(self.generator_frequency.maximum()/.1)**(value/1000)')
 # Initial and final dial share the selected waveform limit.
 s=s.replace('math.log(500000)', 'math.log(self.generator_frequency.maximum()/.1)')
 anchor='    def _generator_availability(self):\n'
 new='''    def _generator_frequency_limits(self):
        from monitor.v17.receiver.unoq_generator import waveform_limit
        wave=4 if self.generator_mode.currentIndex()==3 else self.generator_wave.currentIndex()
        maximum=waveform_limit(wave)/1000.
        for control in (self.generator_frequency,self.generator_final_frequency):
            with QtCore.QSignalBlocker(control):control.setMaximum(maximum)
            control.setToolTip(f'0,1 Hz a {maximum/1000:g} kHz. Permite valores intermedios; el timer redondea la frecuencia efectiva.')
        for spin,dial in ((self.generator_frequency,self.generator_frequency_dial),(self.generator_final_frequency,self.generator_final_frequency_dial)):
            with QtCore.QSignalBlocker(dial):dial.setValue(round(1000*math.log(max(.1,spin.value())/.1)/math.log(maximum/.1)))
            dial.setToolTip(f'Dial logarítmico · 0,1 Hz → {maximum/1000:g} kHz. Ajuste preciso en el número.')

'''
 assert anchor in s;s=s.replace(anchor,new+anchor+'        self._generator_frequency_limits()\n',1);p.write_text(s)
if __name__=='__main__':apply(sys.argv[1])
