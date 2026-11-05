"""Bounded summaries of existing MCU microsecond fields, one per batch."""
LIMITS=(5,10,20,50,100,200,500,1000,5000)


def empty():
    return dict(count=0,total_us=0,min_us=None,max_us=0,zero_count=0,
                histogram=[0]*(len(LIMITS)+1))


def add(summary,value):
    summary['count']+=1;summary['total_us']+=value
    summary['min_us']=value if summary['min_us'] is None else min(summary['min_us'],value)
    summary['max_us']=max(summary['max_us'],value)
    summary['zero_count']+=int(value==0)
    index=next((i for i,limit in enumerate(LIMITS) if value<limit),len(LIMITS))
    summary['histogram'][index]+=1


def report(summary):
    result=dict(summary)
    result['mean_us']=summary['total_us']/summary['count'] if summary['count'] else None
    return result


class BatchTiming:
    def __init__(self):
        self.last=None;self.groups={};self.omitted=0

    def observe(self,epoch,batch,phase,prepare,check,previous,origin='unknown'):
        key=(epoch,batch)
        if key==self.last:return
        self.last=key
        previous_key=f'{previous[1]}:{previous[2]}' if previous is not None else 'unknown'
        group_key=(phase,previous_key,origin)
        if group_key not in self.groups:
            if len(self.groups)>=128:self.omitted+=1;return
            self.groups[group_key]=dict(prepare=empty(),check=empty())
        group=self.groups[group_key]
        add(group['prepare'],prepare);add(group['check'],check)

    def report(self):
        return dict(histogram_upper_bounds_exclusive_us=LIMITS,groups=[
            dict(observed_phase=phase,previous_batch=previous,previous_origin=origin,
                 prepare=report(group['prepare']),check=report(group['check']))
            for (phase,previous,origin),group in sorted(self.groups.items())],
            omitted_batches=self.omitted,
            note='Fields describe previous physical batch. Dedup by epoch/sequence//2; only batches containing target native RF/status are covered. Phase/mix are host observations, not causal attribution.')
