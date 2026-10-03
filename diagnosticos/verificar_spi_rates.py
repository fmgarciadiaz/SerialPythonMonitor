#!/usr/bin/env python3
"""Ensayo físico de tasas SPI, continuidad y rango; restaura el perfil inicial."""
import argparse,json,sys,time
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from transport.unoq_acquisition import Configuration
from transport.unoq_config_receiver import OutputReceiver
from transport.unoq_usb import Connection
from transport.unoq_switch import Mode,Phase,Reason,switch_request

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--rates',type=int,nargs='+',default=[40000,50000,62500])
 p.add_argument('--bits',type=int,nargs='+',default=[14]);p.add_argument('--seconds',type=float,default=15)
 a=p.parse_args();rows=[];last=None;count=0;lo=65535;hi=0;config=None
 def consume(samples):
  nonlocal last,count,lo,hi
  for item in samples:
   if last is not None:
    assert (item[0]-last[0])&0xffffffff==config.period,'timestamp discontinuo'
    assert (item[3]-last[3])&0xffffffff==1,'índice discontinuo'
   assert max(item[1:3])<=config.maximum,'rango ADC inválido'
   lo=min(lo,*item[1:3]);hi=max(hi,*item[1:3]);count+=1;last=item
 error=None
 try:
  with Connection('1060031107') as c:
   c.socket.settimeout(.01);r=OutputReceiver(c,consume)
   try:
    for bits in a.bits:
     for rate in a.rates:
      # Disable cross-profile continuity while configure flushes the old node.
      r.on_samples=lambda samples:None
      config=Configuration(bits,rate);r.configure(config);r.select(Mode.SPI)
      last=None;count=0;lo=65535;hi=0;r.on_samples=consume;started=time.monotonic()
      while time.monotonic()-started<a.seconds:r.pump()
      elapsed=time.monotonic()-started
      row=dict(bits=bits,rate=rate,period_us=config.period,sampling_cycles=config.sampling_cycles,sampling_us=config.sampling_us,pairs=count,elapsed_seconds=elapsed,received_pairs_per_second=count/elapsed,min_adc=lo,max_adc=hi,passed=count>=rate*(a.seconds-2))
      if rate>31250:
       rid=0xfffe0000+rate
       c.socket.sendall(switch_request(rid,Mode.UART));deadline=time.monotonic()+2;rejected=False
       while time.monotonic()<deadline and not rejected:
        r.pump()
        rejected=any(reply.request_id==rid and reply.phase==Phase.REJECTED and reply.reason==Reason.UNSUPPORTED and reply.active==Mode.SPI for reply in r.decoder.replies)
       row['uart_rejected']=rejected
       row['passed'] &= rejected
      rows.append(row);print(json.dumps(row),flush=True)
      if not row['passed']:raise RuntimeError('Caudal insuficiente')
   finally:
    r.on_samples=lambda samples:None
    try:r.configure(Configuration());r.select(Mode.SPI)
    finally:r.close()
 except Exception as exc:error=str(exc)
 report=dict(profiles=rows,error=error,passed=error is None)
 folder=ROOT/'diagnosticos/resultados_usb';folder.mkdir(exist_ok=True)
 path=folder/(datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'_spi_rates.json');path.write_text(json.dumps(report,indent=2)+'\n')
 print(path);print(json.dumps(report),flush=True);return int(error is not None)
if __name__=='__main__':raise SystemExit(main())
