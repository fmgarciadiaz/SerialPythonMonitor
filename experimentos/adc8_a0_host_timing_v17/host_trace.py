"""Bounded host wall/CPU observations; no clock reads or I/O in this observer."""
from collections import deque


class RollingTrace(deque):
    rolling=True


def cpu_description(wall,thread_cpu,process_cpu):
    return dict(wall_seconds=wall,thread_cpu_seconds=thread_cpu,process_cpu_seconds=process_cpu,
        wall_minus_thread_cpu_seconds=max(0.,wall-thread_cpu) if thread_cpu is not None else None,
        classification=('cpu_unavailable' if thread_cpu is None else
            'thread_cpu_dominant' if wall>0 and thread_cpu>=.7*wall else 'off_thread_wall_dominant'))


class HostTiming:
    def __init__(self,enabled=True):
        self.enabled=enabled;self.current_read=None;self.current_decode=None
        self.stages={name:dict(count=0,sum_wall_seconds=0.,sum_thread_cpu_seconds=0.,
            sum_process_cpu_seconds=0.,max_wall_seconds=0.,top=[]) for name in ('read','decode')}
        self.ack_count=0;self.ack_top=[]

    @staticmethod
    def _qualifies(top,key,value):return len(top)<8 or value>top[-1][key]

    @staticmethod
    def _insert(top,key,item):
        top.append(item);top.sort(key=lambda entry:entry[key],reverse=True)
        del top[8:]

    def observe(self,stage,start,end,rid=None,thread_cpu=None,process_cpu=None,sent=None):
        if not self.enabled:return
        if stage in self.stages:
            wall=max(0.,end-start);summary=self.stages[stage]
            summary['count']+=1;summary['sum_wall_seconds']+=wall
            summary['sum_thread_cpu_seconds']+=thread_cpu or 0.
            summary['sum_process_cpu_seconds']+=process_cpu or 0.
            summary['max_wall_seconds']=max(summary['max_wall_seconds'],wall)
            interval=(start,end,thread_cpu,process_cpu)
            if stage=='read':self.current_read=interval;self.current_decode=None
            else:self.current_decode=interval
            if self._qualifies(summary['top'],'wall_seconds',wall):
                self._insert(summary['top'],'wall_seconds',dict(start=start,end=end,
                    **cpu_description(wall,thread_cpu,process_cpu)))
        elif stage=='ack' and sent is not None:
            self.ack_count+=1;latency=end-sent
            if not self._qualifies(self.ack_top,'send_to_ack_seconds',latency):return
            def describe(interval):
                if interval is None:return None
                began,finished,thread,process=interval
                return dict(start=began,end=finished,**cpu_description(max(0.,finished-began),thread,process))
            read=self.current_read;decode=self.current_decode
            item=dict(request_id=rid,sent_monotonic=sent,ack_observed_monotonic=end,
                send_to_ack_seconds=latency,read_containing_completion=describe(read),
                decode_before_ack=describe(decode),
                read_completion_to_ack_seconds=end-read[1] if read else None)
            self._insert(self.ack_top,'send_to_ack_seconds',item)

    def snapshot(self):
        return dict(enabled=self.enabled,stages=self.stages,ack_observations=self.ack_count,
            ack_top=self.ack_top,limitations=[
                'read_containing_completion is the most recent completed recv; fragmented ACK bytes may span earlier reads.',
                'read/decode CPU spans are supplied by the existing receiver instrumentation; no extra observer clock reads.',
                'wall minus thread CPU includes blocking, scheduling and other causes; it is not proof of GIL contention.',
                'process CPU includes other threads in this process and excludes separate DSP child processes.',
                'No decoder byte offset is available through this callback; decode_before_ack identifies the last decode invocation.',
                'Host and Q monotonic clocks have independent origins; correlate request IDs and within-clock durations only.'])
