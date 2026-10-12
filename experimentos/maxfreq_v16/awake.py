"""Repeat acceptances with a awake host; retain the unchanged firmware grid.

Run with caffeinate -i -s. Old acceptance runs are never reused by finalists().
Wall/monotonic drift detects sleep or a wall-clock jump during each new case.
"""
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from experimentos.maxfreq_v16.sweep import Sweep


class AwakeSweep(Sweep):
    def __init__(self):
        super().__init__()
        self.report['host_sleep_control'] = {
            'required_command': 'caffeinate -i -s',
            'previous_acceptance_reused': False,
            'previous_campaign_archive': 'antes_control_suspension',
        }
        for row in self.report['cases']:
            if not row.get('host_awake_control') and 'más de 2 segundos' in row.get('error', ''):
                row['failure_scope'] = 'Host/transport interruption; not an ADC limit'
                row['host_sleep_contamination_possible'] = True

    def trial(self, *args, **kwargs):
        wall_start, mono_start = time.time(), time.monotonic()
        row = super().trial(*args, **kwargs)
        wall_elapsed = time.time() - wall_start
        mono_elapsed = time.monotonic() - mono_start
        row.update(host_awake_control=True, utc_finished=datetime.now(timezone.utc).isoformat(),
                   wall_elapsed=wall_elapsed, monotonic_elapsed=mono_elapsed,
                   wall_monotonic_drift_seconds=wall_elapsed-mono_elapsed)
        if abs(wall_elapsed-mono_elapsed) > 2:
            row.update(ok=False, error='Host sleep/clock discontinuity: repeat this case',
                       failure_scope='Host environment')
            self.dirty = True
        self.save()
        return row


if __name__ == '__main__':
    sweep = AwakeSweep()
    sweep.run()
    raise SystemExit(0 if sweep.report['ok'] and sweep.report['restored'] else 1)
