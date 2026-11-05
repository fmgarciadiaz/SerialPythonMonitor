"""Local, read-only observer for one owned GUI process and its descendants."""
import json
import statistics
import time
import psutil

class ProcessResources:
    def __init__(self,pid,path):
        self.root=psutil.Process(pid);self.identity=(pid,self.root.create_time())
        self.path=path;self.previous={};self.last_at=None;self.rows=[]
    def sample(self):
        began=time.monotonic();errors=[];processes=[]
        try:
            if self.root.create_time()!=self.identity[1]:raise RuntimeError('GUI pid reused')
            owned=[self.root,*self.root.children(recursive=True)]
        except psutil.NoSuchProcess:return
        except psutil.AccessDenied:
            owned=[self.root];errors.append('descendants_access_denied')
        cpu_delta=0.;rss=0;current={}
        for process in owned:
            try:
                with process.oneshot():
                    identity=(process.pid,process.create_time());cpu=process.cpu_times();memory=process.memory_info().rss
                seconds=cpu.user+cpu.system
                cpu_delta+=max(0.,seconds-self.previous.get(identity,seconds if self.last_at is None else 0.))
                current[identity]=seconds;rss+=memory
                processes.append(dict(pid=identity[0],created=identity[1],cpu_seconds=seconds,rss_bytes=memory))
            except psutil.NoSuchProcess:pass
            except psutil.AccessDenied:errors.append('process_access_denied')
        interval=began-self.last_at if self.last_at is not None else None
        row=dict(monotonic=began,interval_seconds=interval,cpu_cores=cpu_delta/interval if interval else None,
                 rss_sum_bytes=rss,process_count=len(processes),processes=processes,errors=errors,
                 observer_ms=(time.monotonic()-began)*1000)
        # Remember identities across transient absences; PID reuse is separated.
        self.previous.update(current);self.last_at=began;self.rows.append(row)
        with self.path.open('a') as stream:stream.write(json.dumps(row)+'\n')
    def summary(self,start=None,end=None):
        rows=[row for row in self.rows if (start is None or row['monotonic']>=start) and (end is None or row['monotonic']<=end)]
        cpu=[row['cpu_cores'] for row in rows if row['cpu_cores'] is not None]
        return dict(samples=len(rows),cpu_cores_median=statistics.median(cpu) if cpu else None,
                    cpu_cores_peak=max(cpu,default=None),rss_sum_peak_bytes=max((row['rss_sum_bytes'] for row in rows),default=None),
                    observer_ms_max=max((row['observer_ms'] for row in rows),default=None),
                    partial_samples=sum(bool(row['errors']) for row in rows),
                    scope='GUI and descendants only; one CPU core=1.0. Sampled CPU can miss exited children. Summed RSS double-counts shared pages, not unique physical memory.')
