"""Reuse only complete ordered high-rate + normal-policy evidence pairs."""
def accepted_prefix(report, bits, stages, normal_policy, minimum_normal_seconds=10):
    cases=[];checks=[];accepted=[]
    for stage,seconds in stages:
        name=f'adc{bits}_{stage}'
        high=[r for r in report['cases'] if r['stage']==name]
        low=[r for r in report['cases'] if r['stage']==name+'_normal']
        policy=[r for r in report.get('normal_policy_checks',[]) if r['stage']==name+'_normal']
        if any(len(rows)>1 for rows in (high,low,policy)):
            raise ValueError('Duplicate evidence stage: '+name)
        if not high or not low or not policy:break
        h,l,p=high[0],low[0],policy[0]
        if not (h['ok'] and h.get('headroom_ok') and h['requested_seconds']==seconds
                and h['seconds']>=seconds and not h['status']['dropped'] and not h['status']['fatal']
                and l['ok'] and l['requested_seconds']>=minimum_normal_seconds
                and l['seconds']>=l['requested_seconds'] and p['policy']==normal_policy):break
        cases.extend((h,l));checks.append(p);accepted.append(stage)
    return cases,checks,accepted
