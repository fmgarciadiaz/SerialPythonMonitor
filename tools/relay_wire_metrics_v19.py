"""Opt-in bounded observer of existing native counters; never changes wire bytes."""
from contextlib import contextmanager
from collections import deque
import os
import json
import struct
import time
import zlib
from monitor.v19.q_support.prepare import atomic_report
from tools.spi_batch_timing_v19 import BatchTiming
from tools.ack_batch_timing_v19 import AckBatchTiming

ENV='ARDUSCOPIO_PRIVATE_WIRE_METRICS'
PROFILE_ENV='ARDUSCOPIO_PRIVATE_WIRE_PROFILE'
ACK_LATENCY_ENV='ARDUSCOPIO_PRIVATE_RAW_ACK_LATENCY'


def set_metrics_profile(bits,rate,*,configuration=None,allow_non_native=False):
    if configuration is None:
        from monitor.v19.receiver.unoq_acquisition import Configuration
    else:Configuration=configuration
    config=Configuration(bits,rate)
    if config._native is None and not allow_non_native:raise ValueError('Native profile required for wire metrics')
    os.environ[PROFILE_ENV]=json.dumps([bits,rate])
    return (bits,rate,config.period,config.node_pairs,config.channels)


def selected_metrics_profile(configuration=None,*,allow_non_native=False):
    raw=os.environ.get(PROFILE_ENV)
    if raw is None:return (8,1860465,86,3488,1)
    target=json.loads(raw)
    if (not isinstance(target,list) or len(target)!=2 or
            any(type(value) is not int for value in target)):raise ValueError('Invalid metrics target')
    return set_metrics_profile(*target,configuration=configuration,allow_non_native=allow_non_native)



class WireMetrics:
    def __init__(self,bits=8,rate=1860465,period=86,node_pairs=3488,channels=1,*,raw_ack_latency=False,wav_timing=False):
        from tools.wav_timing_metrics_v19 import WavTimingMetrics
        self.wav_timing=WavTimingMetrics() if wav_timing else None
        self.profile=(bits,rate,period,node_pairs,channels)
        self.buffer=bytearray();self.playing=False;self.epochs={}
        self.frame_kinds={};self.playing_frame_kinds={}
        self.sent_commands={};self.playing_sent_commands={}
        self.phase='acquisition';self.last_rf=None;self.phase_events=[];self.events_omitted=0
        self.chunk_timing={}
        self.batch_half=None;self.batch_mix={};self.batch_mix_omitted=0
        self.final_rf_idle={};self.wav_rf_streak={};self.last_wav_rf_phase=None;self.wav_rf_run=0
        self.stop_pending={};self.stop_roundtrips=[];self.stop_omitted=0
        self.completed_batches=deque(maxlen=3);self.batch_timing=BatchTiming()
        self.native_batches=deque(maxlen=3)
        self.node_tails=[];self.tail_last_node=None
        self.recent_chunks=deque(maxlen=8)
        self.ack_batch_timing=AckBatchTiming()
        self.raw_ack_latency=raw_ack_latency;self.raw_pending={}
        self.raw_ack_count=0;self.raw_ack_max_ms=0.;self.raw_ack_total_ms=0.
        self.raw_ack_slow=deque(maxlen=32);self.raw_ack_omitted=0
        self.raw_receipts={};self.raw_decoded_count=0;self.raw_decode_max_ms=0.

    def tag_native_batch(self,batch,signature):
        if self.native_batches and self.native_batches[-1][0]==batch:
            previous=self.native_batches.pop()[1]
            self.native_batches.append((batch,signature if previous==signature else None))
        else:self.native_batches.append((batch,signature))

    def observe_batch(self,sequence,kind,count,final=False):
        # MCU sequence starts at zero and advances two per physical exchange.
        # A TCP read can begin at either half; pair only adjacent even/odd seq.
        category='wav' if kind==12 else 'rf' if kind==20 and count else 'idle' if kind==20 else 'other'
        if not sequence&1:
            self.batch_half=(sequence,category,self.phase,final)
        else:
            first=self.batch_half;self.batch_half=None
            if first is not None and ((first[0]+1)&0xffffffff)==sequence:
                key=f'{first[2]}:{first[1]}+{category}'
                self.completed_batches.append((sequence//2,first[2],f'{first[1]}+{category}'))
                if key in self.batch_mix or len(self.batch_mix)<64:
                    self.batch_mix[key]=self.batch_mix.get(key,0)+1
                else:self.batch_mix_omitted+=1
                if first[1]=='rf' and category=='idle' and first[3]:
                    self.final_rf_idle[first[2]]=self.final_rf_idle.get(first[2],0)+1
                if first[1]=='wav' and category=='rf':
                    self.wav_rf_run=self.wav_rf_run+1 if self.last_wav_rf_phase==first[2] else 1
                    self.last_wav_rf_phase=first[2]
                    self.wav_rf_streak[first[2]]=max(self.wav_rf_streak.get(first[2],0),self.wav_rf_run)
                else:self.last_wav_rf_phase=None;self.wav_rf_run=0

    def event(self,kind,**details):
        if len(self.phase_events)<128:self.phase_events.append(dict(kind=kind,phase=self.phase,**details))
        else:self.events_omitted+=1

    def set_phase(self,phase):
        if phase!=self.phase:
            previous=self.phase;self.phase=phase
            self.event('phase',previous=previous,last_observed_rf=self.last_rf)

    def sent(self,data):
        """Observe successful whole SCP commands; never retry or split a send."""
        if len(data)!=992 or data[:4]!=b'SCP1':return
        kind=struct.unpack_from('<H',data,6)[0]
        if kind in (11,13):
            label='chunk' if kind==13 else {0:'query',1:'begin',2:'play',3:'stop'}.get(data[20],'other')
            self.ack_batch_timing.sent(struct.unpack_from('<I',data,8)[0],struct.unpack_from('<I',data,16)[0],label)
        if kind==13:
            now=time.monotonic()
            self.recent_chunks.append(dict(sent_at=now,phase=self.phase,
                request_id=struct.unpack_from('<I',data,8)[0]))
            if self.raw_ack_latency:
                rid=struct.unpack_from('<I',data,8)[0]
                if len(self.raw_pending)>=64:
                    self.raw_pending.pop(next(iter(self.raw_pending)));self.raw_ack_omitted+=1
                self.raw_pending[rid]=(now,struct.unpack_from('<I',data,16)[0])
            timing=self.chunk_timing.setdefault(self.phase,dict(count=0,last=None,max_gap_ms=0.,
                gaps={'lt1ms':0,'1to3ms':0,'3to6ms':0,'6to12ms':0,'ge12ms':0}))
            if timing['last'] is not None:
                gap=(now-timing['last'])*1000
                bucket='lt1ms' if gap<1 else '1to3ms' if gap<3 else '3to6ms' if gap<6 else '6to12ms' if gap<12 else 'ge12ms'
                timing['gaps'][bucket]+=1;timing['max_gap_ms']=max(timing['max_gap_ms'],gap)
            timing['count']+=1;timing['last']=now
        if kind==11 and data[20] in (1,2,3):
            self.set_phase({1:'preparing',2:'starting',3:'stopping'}[data[20]])
            if data[20]==3:
                if len(self.stop_pending)<16:
                    self.stop_pending[struct.unpack_from('<I',data,8)[0]]=time.monotonic()
                else:self.stop_omitted+=1
        key=f'11:{data[20]}' if kind==11 else str(kind)
        self.sent_commands[key]=self.sent_commands.get(key,0)+1
        if self.playing:
            self.playing_sent_commands[key]=self.playing_sent_commands.get(key,0)+1

    @staticmethod
    def empty():
        return dict(frames=0,samples=0,queue_peak=0,min_slack_ticks=None,send_nodes=0,send_ticks_total=0,last_node=None,
                    sampled_queue_max=0,send_ticks_max=0,send_over_budget_nodes=0,empty_status_frames=0)

    def feed(self,data,received_at=None):
        if self.raw_ack_latency and received_at is None:received_at=time.monotonic()
        self.buffer.extend(data);offset=0
        while offset+992<=len(self.buffer):
            packet=bytes(self.buffer[offset:offset+992]);offset+=992
            magic,version,kind,_sequence,length=struct.unpack_from('<4sHHII',packet)
            if (magic,version,length)!=(b'SCP1',4,972) or zlib.crc32(packet[:988])!=struct.unpack_from('<I',packet,988)[0]:
                raise ValueError('Invalid frame in diagnostic metrics observer')
            count=struct.unpack_from('<H',packet,64)[0] if kind==20 else 0
            n=struct.unpack_from('<I',packet,84)[0] if kind==20 else 0
            index=struct.unpack_from('<I',packet,52)[0] if kind==20 else 0
            node=struct.unpack_from('<I',packet,72)[0] if kind==20 else 0
            self.observe_batch(_sequence,kind,count,bool(count and n and ((index-node*n)&0xffffffff)+count==n))
            if kind==12:
                request=struct.unpack_from('<I',packet,16)[0]
                self.ack_batch_timing.replied(_sequence,request,struct.unpack_from('<I',packet,20)[0],packet[25])
                pending=self.raw_pending.get(request) if self.raw_ack_latency else None
                if pending is not None and struct.unpack_from('<I',packet,20)[0]==pending[1]:
                    del self.raw_pending[request]
                    elapsed=(received_at-pending[0])*1000
                    self.raw_ack_count+=1;self.raw_ack_total_ms+=elapsed
                    self.raw_ack_max_ms=max(self.raw_ack_max_ms,elapsed)
                    if len(self.raw_receipts)>=64:
                        self.raw_receipts.pop(next(iter(self.raw_receipts)));self.raw_ack_omitted+=1
                    self.raw_receipts[request]=dict(request_id=request,sent_at=pending[0],received_at=received_at,
                        raw_roundtrip_ms=elapsed,state=packet[24],reason=packet[25],
                        accepted=struct.unpack_from('<I',packet,28)[0],played=struct.unpack_from('<I',packet,32)[0])
                sent_at=self.stop_pending.pop(request,None)
                if sent_at is not None:
                    if len(self.stop_roundtrips)<16:
                        self.stop_roundtrips.append(dict(request_id=request,
                            roundtrip_ms=(time.monotonic()-sent_at)*1000,state=packet[24],reason=packet[25]))
                    else:self.stop_omitted+=1
                self.playing=packet[24]==2 and struct.unpack_from('<I',packet,40)[0]==40000
                if self.playing:self.set_phase('playing')
                elif packet[24] in (0,3,4,5):self.set_phase('stopped')
            # Count existing replies without adding clocks to the MCU/relay.
            # Kind 12 includes CHUNK and QUERY replies: these counts alone do
            # not establish which command caused the control traffic.
            key=str(kind)
            self.frame_kinds[key]=self.frame_kinds.get(key,0)+1
            if self.playing:
                self.playing_frame_kinds[key]=self.playing_frame_kinds.get(key,0)+1
            if kind!=20:continue  # kind21 contains stack counters, not send ticks.
            rate,index,dropped,fatal,count,bits,channels,period,node,flags=struct.unpack_from('<IIIIHBBIII',packet,48)
            n,queue,peak,copy,poll,slack,send,produced=struct.unpack_from('<8I',packet,84)
            batch=_sequence//2;signature=(flags>>1,bits,rate,period,n,channels)
            self.tag_native_batch(batch,signature)
            if (bits,rate,period,n,channels)!=self.profile:continue
            if dropped or fatal or flags&1:raise ValueError('Invalid acquisition in metrics observer')
            previous_id=(batch-1)&0x7fffffff
            previous=next((b for b in self.completed_batches if b[0]==previous_id),None)
            signatures=[b[1] for b in self.native_batches if b[0]==previous_id]
            origin=('same_epoch_profile' if signatures[0]==signature else 'different_epoch_profile') if signatures and signatures[0] is not None else 'unknown'
            prepare,check=struct.unpack_from('<II',packet,40)
            if self.wav_timing is not None:
                self.wav_timing.native(flags>>1,_sequence,self.phase,prepare,check)
                prepare=check=None
            else:
                if prepare&0xff000000==0xd7000000:raise ValueError('Private WAV timing requires exact diagnostic binding')
                self.ack_batch_timing.native(flags>>1,_sequence,self.phase,prepare,check)
                self.batch_timing.observe(flags>>1,batch,self.phase,prepare,check,previous,origin)
            key=str(flags>>1)
            if key not in self.epochs:
                if len(self.epochs)>=32:raise ValueError('Too many epochs for bounded metrics observation')
                self.epochs[key]=dict(all=self.empty(),radio_playing=self.empty(),phases={},last_peak=None)
            epoch=self.epochs[key]
            snapshot=dict(epoch=key,node=node,index=index,queue=queue,queue_peak=peak,slack_min_ticks=slack)
            # Copy/poll are cumulative maxima, not timings of this node. The
            # batch preparation/check fields describe the previous exchange.
            new_peak=epoch['last_peak'] is None or peak>epoch['last_peak']
            node_start=count and ((index-node*n)&0xffffffff)==0 and send and self.tail_last_node!=(key,node)
            keep_tail=node_start and (len(self.node_tails)<8 or send>self.node_tails[-1]['previous_node_send_ticks'])
            if new_peak or keep_tail:
                context=dict(snapshot,copy_max_ticks=copy,poll_max_ticks=poll,
                             previous_node_send_ticks=send,previous_batch_prepare_us=prepare,
                             previous_batch_check_us=check,previous_batch_origin=origin)
            self.last_rf=snapshot
            phase=epoch['phases'].get(self.phase)
            if phase is None:
                phase=epoch['phases'][self.phase]=self.empty()
                self.event('first_rf_in_phase',snapshot=snapshot)
            if new_peak:
                self.event('cumulative_peak',previous_peak=epoch['last_peak'],snapshot=context,
                    host_observed_at=time.monotonic(),recent_chunks=list(self.recent_chunks))
            epoch['last_peak']=peak
            if node_start:
                self.tail_last_node=(key,node)
                if keep_tail:
                    self.node_tails.append(dict(context,phase=self.phase))
                    self.node_tails.sort(key=lambda item:item['previous_node_send_ticks'],reverse=True)
                    del self.node_tails[8:]
            groups=[epoch['all'],phase]
            if self.playing:groups.append(epoch['radio_playing'])
            for group in groups:
                group['frames']+=int(bool(count));group['empty_status_frames']+=int(not count)
                group['samples']+=count;group['queue_peak']=max(group['queue_peak'],peak)
                group['sampled_queue_max']=max(group['sampled_queue_max'],queue)
                if slack!=0xffffffff:
                    group['min_slack_ticks']=slack if group['min_slack_ticks'] is None else min(group['min_slack_ticks'],slack)
                if count and ((index-node*n)&0xffffffff)==0 and send and group['last_node']!=node:
                    group['last_node']=node;group['send_nodes']+=1;group['send_ticks_total']+=send
                    group['send_ticks_max']=max(group['send_ticks_max'],send)
                    group['send_over_budget_nodes']+=int(send>self.profile[2]*self.profile[3])
        if offset:del self.buffer[:offset]

    def decoded_events(self,receiver):
        for kind,value in receiver.decoder.events:
            if kind!='wav' or value.request_id not in receiver.wav_inflight:continue
            record=self.raw_receipts.pop(value.request_id,None)
            if record is None:continue
            now=time.monotonic();delay=(now-record['received_at'])*1000
            record.update(decoded_at=now,decode_delay_ms=delay,
                          decoded_roundtrip_ms=(now-record['sent_at'])*1000)
            self.raw_decoded_count+=1;self.raw_decode_max_ms=max(self.raw_decode_max_ms,delay)
            if record['raw_roundtrip_ms']>=20 or delay>=20 or record['reason']:
                self.raw_ack_slow.append(record)

    def report(self):
        budget=self.profile[2]*self.profile[3]
        def summarize(groups):
            nodes=sum(g['send_nodes'] for g in groups);ticks=sum(g['send_ticks_total'] for g in groups)
            slack=min((g['min_slack_ticks'] for g in groups if g['min_slack_ticks'] is not None),default=None)
            peak=max((g['queue_peak'] for g in groups),default=0)
            margin=1-ticks/nodes/budget if nodes else None
            return dict(frames=sum(g['frames'] for g in groups),samples=sum(g['samples'] for g in groups),
                empty_status_frames=sum(g['empty_status_frames'] for g in groups),
                send_nodes=nodes,mean_send_margin=margin,mcu_queue_peak=peak,min_slack_ticks=slack,
                sampled_queue_max=max((g['sampled_queue_max'] for g in groups),default=0),
                send_ticks_max=max((g['send_ticks_max'] for g in groups),default=0),
                send_over_budget_nodes=sum(g['send_over_budget_nodes'] for g in groups),
                headroom_pass=self.wav_timing is None and nodes>0 and margin>=.10 and peak<4 and slack is not None and slack>0)
        return dict(profile=self.profile,node_budget_ticks=budget,epoch_count=len(self.epochs),
                    all=summarize([e['all'] for e in self.epochs.values()]),
                    radio_playing=summarize([e['radio_playing'] for e in self.epochs.values()]),
                    phases={p:summarize([e['phases'][p] for e in self.epochs.values() if p in e['phases']])
                            for p in sorted({p for e in self.epochs.values() for p in e['phases']})},
                    phase_events=self.phase_events,phase_events_omitted=self.events_omitted,
                    slowest_node_observations=self.node_tails,
                    node_timing_note='Eight largest previous-node sends, one observation per epoch/node start. Copy/poll are cumulative MCU maxima; prepare/check refer to previous physical batch. Same observation does not establish simultaneity or causality.',
                    chunk_timing={p:{k:v for k,v in t.items() if k!='last'} for p,t in self.chunk_timing.items()},
                    physical_batch_mix=dict(self.batch_mix),physical_batch_mix_omitted=self.batch_mix_omitted,
                    final_rf_followed_by_idle=dict(self.final_rf_idle),wav_rf_max_consecutive_batches=dict(self.wav_rf_streak),
                    stop_roundtrips=self.stop_roundtrips,stop_pending_count=len(self.stop_pending),stop_observations_omitted=self.stop_omitted,
                    wav_chunk_timing=self.wav_timing.report() if self.wav_timing is not None else None,
                    ordinary_timing_valid=self.wav_timing is None,
                    performance_acceptance_eligible=self.wav_timing is None,
                    spi_batch_timing=self.batch_timing.report(),
                    ack_batch_timing=self.ack_batch_timing.report(),
                    raw_chunk_ack_latency=dict(enabled=self.raw_ack_latency,matched=self.raw_ack_count,
                        raw_max_ms=self.raw_ack_max_ms,raw_mean_ms=self.raw_ack_total_ms/self.raw_ack_count if self.raw_ack_count else None,
                        decoded=self.raw_decoded_count,decode_max_ms=self.raw_decode_max_ms,
                        pending_sends=len(self.raw_pending),pending_decode=len(self.raw_receipts),
                        omitted=self.raw_ack_omitted,slow=list(self.raw_ack_slow),
                        note='Complete-frame socket read time versus entry to decoder event handling; correlated CHUNK ids/session, normal receiver validation unchanged'),
                    phase_caveat='Host observation boundaries, not MCU event timestamps. Sampled queue is a lower bound; cumulative peak remains acceptance gate. Send counters refer to previous node. Retune is not visible on this wire.',
                    pending_bytes=len(self.buffer),tcp_fifo_headroom_measured=False,
                    frame_kinds=dict(self.frame_kinds),radio_playing_frame_kinds=dict(self.playing_frame_kinds),
                    sent_commands=dict(self.sent_commands),radio_playing_sent_commands=dict(self.playing_sent_commands),
                    note='MCU queue/slack/send counters; send weighted once per complete node start. Cumulative MCU peak includes startup.')


@contextmanager
def observe_connection(connection,path,*,wav_timing=False,receiver_class=None,configuration=None,allow_non_native=False):
    observe_ack=os.environ.get(ACK_LATENCY_ENV)=='1'
    profile=selected_metrics_profile(configuration,allow_non_native=allow_non_native)
    native_expected=not (configuration is not None and configuration(profile[0],profile[1])._native is None)
    observer=WireMetrics(*profile,raw_ack_latency=observe_ack,wav_timing=wav_timing);original=connection.read
    original_socket=getattr(connection,'socket',None)
    class ObservedSocket:
        def __getattr__(self,name):return getattr(original_socket,name)
        def sendall(self,data,*args,**kwargs):
            result=original_socket.sendall(data,*args,**kwargs)
            observer.sent(data)
            return result
    def read():
        data=original();observer.feed(data);return data
    connection.read=read
    wrapped_socket=ObservedSocket() if original_socket is not None else None
    if wrapped_socket is not None:connection.socket=wrapped_socket
    if receiver_class is None:
        from monitor.v19.receiver.unoq_config_receiver import OutputReceiver
    else:OutputReceiver=receiver_class
    decoder_events=OutputReceiver._process_decoder_events
    if observe_ack:
        def process(receiver):
            observer.decoded_events(receiver)
            return decoder_events(receiver)
        OutputReceiver._process_decoder_events=process
    try:yield connection
    finally:
        if observe_ack:OutputReceiver._process_decoder_events=decoder_events
        connection.read=original
        # A normal close may already have set socket=None; never resurrect it.
        if wrapped_socket is not None and connection.socket is wrapped_socket:
            connection.socket=original_socket
        result=observer.report();result['native_counters_expected']=native_expected
        if not native_expected:
            result['performance_acceptance_eligible']=False
            result['note']='Non-native target: host ACK/service diagnostics only; native MCU counter qualification unavailable.'
        atomic_report(path,result)


@contextmanager
def accepted_metrics_connection(serial):
    from monitor.v19.io.live_connection import installed_connection
    with installed_connection(serial) as connection:
        with observe_connection(connection,os.environ[ENV]):yield connection
