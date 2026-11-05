"""Report measured batch costs without treating them as whole-cycle timings."""
import argparse
import json
from pathlib import Path


def summarize(metrics,phase='playing'):
    groups=[g for g in metrics['spi_batch_timing']['groups'] if g['observed_phase']==phase]
    stable=[g for g in groups if g.get('previous_origin')=='same_epoch_profile'
            and g['previous_batch'].startswith(phase+':')]
    observed=sum(g['prepare']['count'] for g in groups)
    count=sum(g['prepare']['count'] for g in stable)
    def cost(name):
        return dict(count=count,mean_us=sum(g[name]['total_us'] for g in stable)/count if count else None,
                    max_us=max((g[name]['max_us'] for g in stable),default=None),
                    zero_count=sum(g[name]['zero_count'] for g in stable))
    prepare=cost('prepare');check=cost('check')
    native=metrics.get('radio_playing',{}) if phase=='playing' else metrics.get('phases',{}).get(phase,{})
    margin=native.get('mean_send_margin');budget=metrics['node_budget_ticks']/160
    physical=sum(n for key,n in metrics['physical_batch_mix'].items() if key.startswith(phase+':'))
    return dict(phase=phase,timing_batches_observed=observed,stable_timing_batches=count,
        stable_fraction_of_timing_observations=count/observed if observed else None,
        physical_batches_observed=physical,prepare=prepare,check=check,
        nominal_wire_us_per_batch_at_40MHz=396.8,
        partial_nominal_us_per_covered_batch=prepare['mean_us']+check['mean_us']+396.8 if count else None,
        service_mean_us_per_node=(1-margin)*budget if margin is not None else None,
        service_budget_us_per_node=budget,
        caveat='Partial batch cost is not CPU utilization or total cycle duration. Node service has a different denominator. Phase boundaries are host observations; physical and timing phase counts can differ at boundaries.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('metrics',type=Path)
    args=parser.parse_args()
    print(json.dumps(summarize(json.loads(args.metrics.read_text())),indent=2))


if __name__=='__main__':main()
