"""Correlate a frozen Q command trace with host sends without mixing clocks."""
import argparse
import json
from pathlib import Path


def audit(folder):
    parent = json.loads((folder / 'report.json').read_text())
    traces = [t for t in parent['command_trace_summaries'] if t['frozen']]
    if not traces:
        raise ValueError('No frozen failure trace')
    trace = traces[-1]
    records = {r['id']: r for r in trace['records']}
    fault = records[trace['fault_id']]
    previous = max((r for r in records.values()
                    if r['ack_state'] == 2 and r['complete_ns'] < fault['complete_ns']),
                   key=lambda r: r['complete_ns'])
    case = next(c for c in reversed(parent['cases']) if c.get('child', {}).get('report'))
    host = json.loads(Path(case['child']['report']).read_text())
    sends = {e[3]: e for e in host['transport_recent'] if e[0] == 'send'}
    before, after = sends[previous['id']], sends[fault['id']]
    begin, end = before[2], after[1]
    return {
        'previous_id': previous['id'], 'fault_id': fault['id'],
        'host_send_start_gap_ms': (after[1] - before[1]) * 1000,
        'host_between_send_calls_ms': (end - begin) * 1000,
        'q_command_complete_gap_ms': (fault['complete_ns'] - previous['complete_ns']) / 1e6,
        'previous_q_snapshot_reserve_samples': previous['accepted'] - previous['played'],
        'host_services_during_gap': [e for e in host['refill_ring']
                                     if e[0] == 'service' and begin < e[1] < end],
        'host_io_over_5ms_during_gap': [e for e in host['transport_recent']
                                       if e[0] in ('read', 'decode')
                                       and e[2] - e[1] > .005 and e[1] < end and e[2] > begin],
        'matched_ack': [
            {'id': a['request_id'], 'host_latency_ms': a['send_to_ack_seconds'] * 1000,
             'q_complete_to_ack_ms': (records[a['request_id']]['ack_rx_ns'] -
                                      records[a['request_id']]['complete_ns']) / 1e6}
            for a in host['host_timing']['ack_top'] if a['request_id'] in records
            and records[a['request_id']]['ack_rx_ns']],
        'limitation': 'Each duration uses one clock only. sendall return is not physical delivery. '
                      'Service samples are bounded observations, not continuous state. '
                      'Cannot separate ACK transport from host scheduling.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    result = audit(args.folder)
    target = args.folder / 'host_send_gap_audit.json'
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(target)
