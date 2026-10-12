"""Extract a firmware whitelist only from complete physical acceptances."""
from dataclasses import dataclass


@dataclass(frozen=True)
class AcceptedProfile:
    bits: int
    ticks: int
    node_pairs: int
    channels: int
    headroom: bool

    @property
    def rate(self):
        return 160000000 // self.ticks

    @property
    def encoded(self):
        return (self.node_pairs << 16) | self.ticks | (0x80000000 if self.channels == 2 else 0)


def accepted_profiles(report):
    if not report.get('ok') or not report.get('restored'):
        raise ValueError('Campaign incomplete or board parameters not restored')
    selected = {}
    for bits, results in report['winners'].items():
        for name in ('maximum_integrity', 'maximum_headroom'):
            winner = results.get(name)
            if winner is None:
                continue
            if not winner.get('integrity_accepted'):
                raise ValueError('Winner lacks integrity acceptance')
            key = (int(bits), winner['ticks'], winner['node_pairs'])
            relevant = [r for r in report['cases'] if (r['bits'], r['ticks'], r['node_pairs']) == key]
            stages = [('finalist', 60), ('acceptance_1', 120), ('acceptance_2', 120),
                      ('acceptance_3', 120), ('endurance', 600)]
            for stage, seconds in stages:
                rows = [r for r in relevant if r['stage'] == stage and r.get('host_awake_control')]
                if not rows:
                    raise ValueError(f'Missing controlled {stage} for {key}')
                row = rows[-1]
                if (not row['ok'] or row.get('seconds', 0) < seconds
                        or abs(row.get('wall_monotonic_drift_seconds', 999)) > 2
                        or row['status']['dropped'] or row['status']['fatal']):
                    raise ValueError(f'Failed acceptance {stage} for {key}')
                if name == 'maximum_headroom' and not row.get('headroom_ok'):
                    raise ValueError(f'Failed headroom {stage} for {key}')
            headroom = winner.get('headroom_accepted', False)
            if name == 'maximum_headroom' and not headroom:
                raise ValueError('Headroom winner lacks headroom acceptance')
            selected[key] = AcceptedProfile(*key, winner.get('channels', report.get('channels', 1)), headroom)
    return sorted(selected.values(), key=lambda p: (p.channels, p.bits, p.rate))


def firmware_header(profiles):
    if not profiles:
        raise ValueError('No accepted profiles')
    maximum_node = max(3584, *(p.node_pairs for p in profiles))
    maximum_results = max(4096, *(p.node_pairs * p.channels for p in profiles))
    maximum_dual = max([3584] + [p.node_pairs for p in profiles if p.channels == 2])
    maximum_single = max([3584] + [p.node_pairs for p in profiles if p.channels == 1])
    rows = '\n'.join(f'    {{{p.bits}, {p.channels}, {p.ticks}, {p.node_pairs}}},' for p in profiles)
    return f'''// Generated from complete physical acceptances. Do not add untested rates.
#pragma once
#include <stdint.h>
typedef struct {{ uint8_t bits, channels; uint16_t ticks, node_pairs; }} ScopeNativeProfile;
#define SCOPE_NATIVE_MAX_NODE {maximum_node}U
#define SCOPE_NATIVE_MAX_RESULTS {maximum_results}U
#define SCOPE_NATIVE_MAX_DUAL {maximum_dual}U
#define SCOPE_NATIVE_MAX_SINGLE {maximum_single}U
static const ScopeNativeProfile scope_native_profiles[] = {{
{rows}
}};
static inline uint32_t scope_native_code(const ScopeNativeProfile *p) {{
    return ((uint32_t)p->node_pairs << 16) | p->ticks | (p->channels == 2 ? UINT32_C(0x80000000) : 0);
}}
static inline const ScopeNativeProfile *scope_native_find(unsigned bits, uint32_t encoded) {{
    for (unsigned i = 0; i < sizeof(scope_native_profiles)/sizeof(scope_native_profiles[0]); ++i)
        if (scope_native_profiles[i].bits == bits && scope_native_code(&scope_native_profiles[i]) == encoded)
            return &scope_native_profiles[i];
    return 0;
}}
'''
