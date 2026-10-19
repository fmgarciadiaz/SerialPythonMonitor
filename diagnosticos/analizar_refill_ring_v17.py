"""Summarize bounded refill diagnostics; no hardware operations."""
import sys,json
from pathlib import Path
from collections import Counter

def summarize(path):
 report=json.loads(Path(path).read_text());events=report.get('refill_ring',[])
 result=dict(report=str(path),ok=report['ok'],restored=report['restored'],errors=report['errors'],events=dict(Counter(e[0] for e in events)),diagnostics_deferred=report.get('diagnostics_deferred'),host_buffer_minimum=report.get('source_buffer_minimum'),transport_max=report.get('transport_max_ms'),pump_gap_max_ms=report.get('pump_gap_max_ms'))
 for kind in ('feed','chunk','service'):
  times=[e[2] if kind=='feed' else e[1] for e in events if e[0]==kind]
  gaps=[b-a for a,b in zip(times,times[1:])]
  result[kind]=dict(span_s=times[-1]-times[0] if times else 0,max_gap_ms=max(gaps)*1000 if gaps else None)
 result['codes_none_reasons']=dict(Counter(e[3] for e in events if e[0]=='codes_none'))
 result['service_reasons']=dict(Counter(e[2] for e in events if e[0]=='service'))
 active=[e for e in events if e[0]=='service' and e[3]==2]
 rate=report['audio_transport']['rate']
 result['ring_dac_reserve_min_ms']=min((e[4]-e[5])*1000/rate for e in active) if active else None
 return result
if __name__=='__main__':
 output=[summarize(path) for path in sys.argv[1:]]
 print(json.dumps(output,indent=2))
