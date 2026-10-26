"""Compact acquisition catalogue; historical profiles remain addressable."""
import json
from pathlib import Path
from monitor.v18.receiver.unoq_acquisition import Configuration
_PATH=Path(__file__).with_name('rate_catalog.json')
def catalog_rates(bits):
 if not _PATH.exists():return None
 rows=json.loads(_PATH.read_text())['bits'].get(str(bits),[])
 result=set()
 for row in rows:
  try:config=Configuration(bits,row['rate'])
  except ValueError:continue
  if (config.channels,config.period,config.node_pairs)==(row['channels'],row['ticks'],row['node_pairs']):result.add(config.rate)
 return result

def label(config,number):
 nominal=(config._native or {}).get('nominal_rate')
 rate=nominal or config.actual_rate
 frequency=(f'{rate/1000000:.2f}'.replace('.',',')+' MHz'
            if rate>=1000000 else
            f'{rate/1000:.0f} kHz' if rate>=100000 else
            f'{number(rate/1000)} kHz')
 if config.channels==1:frequency+=' · CH1'
 def duration(us):
  if us<1:return f'{number(us*1000)} ns'
  if us>=1000:return f'{number(us/1000)} ms'
  return f'{number(us)} µs'
 return f'{frequency} · {duration(config.sampling_us)}'
