"""Decoder for the identity-bound private wav-chunk-cycles-v1 schema."""
from tools.wav_timing_candidate_v19 import FIELDS,MAGIC,SCHEMA


class WavTimingMetrics:
    def __init__(self):
        self.pending=None;self.records=[];self.completed=0;self.incomplete=0
        self.invalid=0;self.repeated=0;self.omitted=0;self.last_serial=None
        self.skipped=0;self.resets=0;self.seen_snapshots=0
        self.first_serial=None;self.last_completed_sample=None;self.irq_max=None

    def native(self,epoch,sequence,phase,tag,value):
        if tag & 0xff000000 != MAGIC:raise ValueError('Missing private WAV timing schema marker')
        page=(tag>>16)&255;snapshot=tag&65535
        if page>=len(FIELDS):raise ValueError('Invalid private WAV timing page')
        if page==0:
            if self.pending is not None:self.incomplete+=1
            self.pending=dict(epoch=epoch,snapshot=snapshot,sequence=sequence,phase=phase,values=[])
            self.seen_snapshots+=1
        row=self.pending
        if row is None:return
        if row['epoch']!=epoch or row['snapshot']!=snapshot or len(row['values'])!=page:
            self.incomplete+=1;self.pending=None;return
        # ACK frames consume sequence numbers too. The normal receiver checks
        # sequence continuity; this parser checks page/snapshot coherence.
        row['last_sequence']=sequence
        if row['phase']!=phase:row['phase']='mixed'
        row['values'].append(value)
        if page!=len(FIELDS)-1:return
        self.pending=None;self.completed+=1
        values=dict(zip(FIELDS,row.pop('values')))
        if not values['serial'] or not values['count_state']&(1<<24):self.invalid+=1;return
        if not values['clock_hz']:raise ValueError('Zero WAV timing clock')
        self.last_completed_sample=dict(values,phase=row['phase'],epoch=epoch,frame_sequence=sequence)
        if self.irq_max is None or values['max_irq']>self.irq_max['cycles']:
            self.irq_max=dict(cycles=values['max_irq'],request=values['max_irq_request'],clock_hz=values['clock_hz'])
        if self.last_serial==values['serial']:self.repeated+=1;return
        if self.first_serial is None:self.first_serial=values['serial']
        if self.last_serial is not None:
            delta=(values['serial']-self.last_serial)&0xffffffff
            if delta>=0x80000000:self.resets+=1
            else:self.skipped+=max(0,delta-1)
        self.last_serial=values['serial']
        values.update(phase=row['phase'],epoch=epoch,frame_sequence=sequence)
        if len(self.records)<4096:self.records.append(values)
        else:self.omitted+=1

    def report(self):
        timings=('irq','poll_main','validate','copy','cache','descriptor','publish','elapsed')
        groups=[]
        for phase,session in sorted({(r['phase'],r['session']) for r in self.records}):
            rows=[r for r in self.records if r['phase']==phase and r['session']==session]
            groups.append(dict(phase=phase,session=session,selected_chunks=len(rows),timing_us={
                field:dict(selected_mean=sum(r[field]*1e6/r['clock_hz'] for r in rows)/len(rows),
                           selected_max=max(r[field]*1e6/r['clock_hz'] for r in rows)) for field in timings}))
        return dict(schema=SCHEMA,groups=groups,records=self.records,completed=self.completed,
                    incomplete=self.incomplete+int(self.pending is not None),invalid=self.invalid,
                    repeated=self.repeated,skipped_serials=self.skipped,resets=self.resets,omitted=self.omitted,
                    first_seen_serial=self.first_serial,last_seen_serial=self.last_serial,
                    last_completed_sample=self.last_completed_sample,max_irq_since_boot=self.irq_max,
                    seen_snapshots=self.seen_snapshots,
                    note='Cadence-selected last accepted CHUNK snapshots, not an all-CHUNK distribution. IRQ is after-lock/before-unlock only; elapsed includes pending interrupts after unlock. Components are nested. Instrumentation perturbs execution. max_irq is cumulative over accepted CHUNKs since boot; per-phase sampled maxima are not global maxima. Relay prepare/check aggregates and ordinary SPI cost summaries are invalid for this private firmware.')
