"""Compare trigger search only; offline, no hardware or visible-FPS claims."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from monitor.v17.trigger import last_trigger_crossing
from tests.v17.test_trigger import reference_crossing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = {'scope': __doc__, 'pairs': 60, 'warmup_pairs': 5,
              'source_sha256': hashlib.sha256(inspect.getsource(last_trigger_crossing).encode()).hexdigest(),
              'reference_sha256': hashlib.sha256(inspect.getsource(reference_crossing).encode()).hexdigest(),
              'cases': {}}
    for count in (3000, 12000):
        t = np.arange(count)
        for case in ('AM', 'noise', 'noise_outlier'):
            values = .3*np.sin(t*.17)*(1+.5*np.sin(t*.003))
            if case != 'AM':
                values = 1e-6*np.sin(t)
            if case == 'noise_outlier':
                values[count//4] = -.5
                values[count//4+20] = .5
            for rising in (False, True):
                timings = {'before': [], 'after': []}
                for pair in range(60):
                    order = (('before', reference_crossing), ('after', last_trigger_crossing))
                    results = []
                    for name, fn in order if pair % 2 == 0 else reversed(order):
                        start = time.perf_counter_ns()
                        result = fn(values, 0., rising, .015)
                        timings[name].append((time.perf_counter_ns()-start)/1e6)
                        results.append(result)
                    assert results[0] == results[1]
                report['cases'][f'{case}_{count}_{"rising" if rising else "falling"}'] = {
                    name: {'median_ms': float(np.median(samples[5:])),
                           'p95_ms': float(np.percentile(samples[5:], 95))}
                    for name, samples in timings.items()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
