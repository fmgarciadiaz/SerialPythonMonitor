#!/usr/bin/env python3
"""Compare host overhead and summarize existing FM logs; never connects to Q.

These timings do not measure keyboard-to-sound latency. MIDI timestamps start
at backend dequeue, render_start excludes synthesis, and queued_audio_ms is a
device status snapshot. Use a physical loopback for end-to-end acceptance.
"""
import argparse
import json
from pathlib import Path
import statistics
import struct
import sys
import time
import zlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def parse_old(payload):
    buffer=bytearray(payload);records=[]
    while b'\n' in buffer and len(records)<256:
        line,_,rest=buffer.partition(b'\n');buffer=bytearray(rest)
        records.append(json.loads(line))
    return records,buffer


def parse_batch(payload):
    lines=bytearray(payload).split(b'\n',256);rest=lines.pop()
    return [json.loads(line) for line in lines],rest


def measure(function,iterations=250):
    for _ in range(10):function()
    times=[]
    for _ in range(iterations):
        start=time.perf_counter_ns();function();times.append((time.perf_counter_ns()-start)/1000)
    return dict(median_us=round(statistics.median(times),3),p95_us=round(float(np.percentile(times,95)),3))


def summarize(path):
    records=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    playing=[r for r in records if r.get('state')==2]
    terminal=[dict(state=r['state'],reason=r['reason']) for r in records if r.get('state') in (3,4,5)]
    return dict(path=str(path),records=len(records),duration_s=round(records[-1]['time']-records[0]['time'],3),
                max_target_blocks=max(r.get('target_blocks',0) for r in records),
                max_render_ms=max(r.get('max_render_ms',0) for r in records),
                max_ack_gap_ms=max(r.get('max_ack_gap_ms',0) for r in records),
                playing_queue_ms=sorted(set(r.get('queued_audio_ms') for r in playing)),terminal=terminal)


def adc_payload(nodes):
    frames=[]
    for node in range(nodes):
        for offset in range(0,2048,226):
            count=min(226,2048-offset);index=node*2048+offset
            frame=bytearray(992)
            struct.pack_into('<4sHHII',frame,0,b'SCP1',4,3,len(frames),972)
            struct.pack_into('<i',frame,32,992)
            struct.pack_into('<IIIIHBBIII',frame,48,100000,index,0,0,count,14,2,10,node,0)
            struct.pack_into('<I',frame,80,index*10)
            for i in range(count):struct.pack_into('<HH',frame,84+4*i,i,16383-i)
            struct.pack_into('<I',frame,988,zlib.crc32(frame[:988]))
            frames.append(frame)
    return b''.join(frames)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log',type=Path,action='append',default=[])
    parser.add_argument('--output',type=Path)
    parser.add_argument('--decoder-baseline',type=Path,help='Optional saved pre-change unoq_config_decoder.py for A/B')
    args=parser.parse_args()
    report={'scope':'host microbenchmarks; no hardware or acoustic latency measurement','parsing':[]}
    line=(json.dumps({'message':dict(type='note_on',note=60,velocity=100),'received_ns':123456789000})+'\n').encode()
    for count in (1,256,4096):
        payload=line*count+b'{"partial":'
        assert parse_old(payload)==parse_batch(payload)
        before=measure(lambda:parse_old(payload));after=measure(lambda:parse_batch(payload))
        report['parsing'].append(dict(pending_records=count,processed_records=min(256,count),before=before,after=after))
    def old_levels():return np.linspace(.7,.7,480),np.linspace(1.65,1.65,480)
    def scalar_levels():return .7,1.65
    report['constant_levels']=dict(before=measure(old_levels),after=measure(scalar_levels))
    from monitor.v16.receiver.unoq_config_decoder import ConfigurationDecoder
    baseline=None
    if args.decoder_baseline:
        import importlib.util
        spec=importlib.util.spec_from_file_location('latency_decoder_baseline',args.decoder_baseline)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        baseline=module.ConfigurationDecoder
    report['adc_decode']=[]
    for nodes in (1,6):
        payload=adc_payload(nodes)
        entry=dict(samples=nodes*2048,tcp_bytes=len(payload),after=measure(lambda:ConfigurationDecoder().feed(payload),100))
        if baseline:
            assert baseline().feed(payload)==ConfigurationDecoder().feed(payload)
            entry['before']=measure(lambda:baseline().feed(payload),100)
        report['adc_decode'].append(entry)
    report['existing_logs']=[summarize(path) for path in args.log]
    encoded=json.dumps(report,indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(encoded)
    print(encoded,end='')


if __name__=='__main__':main()
