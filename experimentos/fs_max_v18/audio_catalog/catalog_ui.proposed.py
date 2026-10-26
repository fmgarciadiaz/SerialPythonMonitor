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
 if nominal:
  return f'≈ {number(nominal/1000)} kHz · '+('CH1' if config.channels==1 else 'dual')
 value=config.actual_rate/1000
 return f'{number(value)} kHz'+(' (CH1)' if config.channels==1 else '')
