"""Private BatchStack profile transitions; print plan unless --run is explicit.

One setup/restart, one continuous measurement connection, exact rollback.
This screens transitions and integrity; it does not qualify public rates.
"""
import argparse
import hashlib
import json
from pathlib import Path
import signal
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from experimentos.fs_max_v18.run_probe import EXP, FrameMetrics, Hardware, private_profiles
from experimentos.fs_max_v18.probe_journal import ProbeJournal


class TransitionHardware(Hardware):
    def final_identity(self):
        from monitor.v18.io.live_connection import installed_identity
        return installed_identity(self.original.serial)


def plan():
    """Fixed, bounded 3 x 5 x 5-second campaign, with exact wire requests."""
    stages = (
        ('CH1 ADC8/88 N3488 Word', 8, 1, 88, 3488),
        ('dual ADC8/253 N3888', 8, 2, 253, 3888),
        ('normal ADC14/31250', 14, 2, None, 2048),
        ('dual ADC10/308 N4176', 10, 2, 308, 4176),
        ('CH1 ADC8/88 N3488 Word', 8, 1, 88, 3488),
    )
    rows = []
    for cycle in range(1, 4):
        for position, (label, bits, channels, ticks, node_pairs) in enumerate(stages, 1):
            encoded = ((node_pairs << 16) | ticks | (0x80000000 if channels == 2 else 0)) if ticks else 32
            rows.append(dict(cycle=cycle, position=position, label=label, bits=bits,
                             channels=channels, ticks=ticks, node_pairs=node_pairs,
                             wire_period=encoded, seconds=5, native=ticks is not None,
                             rate=160000000 / ticks if ticks else 31250))
    return rows


def wire_config(config):
    return dict(bits=config.bits, rate=config.rate, channels=config.channels,
                request_period=config.request_period, node_pairs=config.node_pairs,
                actual_rate=config.actual_rate)


def validate_status(status, config, epoch):
    if not status or status.get('epoch') != epoch:
        raise ValueError('Missing current-epoch ADC status')
    if status.get('bits') != config.bits or status.get('rate') != config.rate:
        raise ValueError('ADC status differs from requested configuration')
    if status.get('dropped') != 0 or status.get('fatal') != 0:
        raise ValueError('ADC dropped/fatal counters are not zero')


def configure_confirmed(receiver, config):
    """A stale decoder.status after APPLIED is not proof of new-epoch data.

    The last stage and next cycle's first stage are identical. A genuine
    receiver no-op reuses the last matching APPLIED ACK, without forcing a
    hidden bridge or changing the requested transition sequence.
    """
    from monitor.v18.receiver.unoq_switch import Phase, Reason
    changed = receiver.configure(config)
    reply = receiver.config_applied
    if (reply is None or reply.phase != Phase.APPLIED or reply.reason != Reason.OK
            or reply.active != config or reply.requested_bits != config.bits
            or reply.requested_period != config.request_period
            or receiver.config != config or receiver.decoder.config != config
            or receiver.decoder.epoch != reply.epoch):
        raise ValueError('Complete matching APPLIED configuration ACK required')
    return dict(changed=bool(changed), reused_ack=not changed,
                request_id=reply.request_id, epoch=reply.epoch,
                phase=reply.phase.name, reason=reply.reason.name,
                requested_bits=reply.requested_bits,
                requested_period=reply.requested_period, active=wire_config(reply.active))


def measure_stage(receiver, profile, row, save, clock=time.monotonic):
    from monitor.v18.receiver.unoq_acquisition import Configuration
    config = Configuration.from_wire(profile['bits'], profile['wire_period'])
    row['failure_stage'] = 'configuration'
    row['requested'] = wire_config(config)
    row['ack'] = configure_confirmed(receiver, config)
    epoch = row['ack']['epoch']
    row['epoch'] = epoch
    save()
    # configure() can return on a read whose final frame is APPLIED and whose
    # last ADC status still belongs to the previous configuration. Wait until
    # current-epoch samples have actually been decoded, then take the baseline.
    row['failure_stage'] = 'first_current_epoch_status'
    deadline = clock() + 3
    while not receiver.decoder.status or receiver.decoder.status.get('epoch') != epoch:
        if clock() >= deadline:
            raise TimeoutError('No ADC status after configuration ACK')
        receiver.pump()
    validate_status(receiver.decoder.status, config, epoch)
    row.update(status_before=dict(receiver.decoder.status), pairs_before=receiver.decoder.pairs,
               measured=True, failure_stage='integrity')
    metrics = FrameMetrics()
    start = clock()
    try:
        while clock() - start < profile['seconds']:
            receiver.pump()
            for status in receiver.decoder.statuses:
                validate_status(status, config, epoch)
                if profile['native']:
                    if not {'queue_peak', 'send_ticks', 'slack_ticks'} <= status.keys():
                        raise ValueError('Missing native frame metrics')
                    metrics.observe([status])
            validate_status(receiver.decoder.status, config, epoch)
    finally:
        elapsed = clock() - start
        pairs = receiver.decoder.pairs - row['pairs_before']
        row.update(elapsed=elapsed, pairs_after=receiver.decoder.pairs, pairs_delta=pairs,
                   observed_rate=pairs / elapsed if elapsed else None,
                   status=dict(receiver.decoder.status) if receiver.decoder.status else None)
        if profile['native']:
            row['native_metrics'] = dict(metric_frames=metrics.frames,
                queue_peak=metrics.queue_peak, min_slack_ticks=metrics.min_slack,
                mean_send_margin=metrics.margin(profile['node_pairs'] * profile['ticks']),
                send_margin_weighting='frames')
    relative_error = abs(row['observed_rate'] / profile['rate'] - 1)
    row['relative_rate_error'] = relative_error
    if relative_error > .02:
        raise ValueError('Observed pair rate differs by more than 2%')
    if profile['native'] and not metrics.frames:
        raise ValueError('No native metric frames during measurement')
    row.update(ok=True, failure_stage=None)


def orchestrate(backend, rows, report, save, measure=measure_stage):
    """Injectable transaction; always close measurement socket before Q admin."""
    captured = restarted = False
    try:
        backend.capture()
        captured = True
        report['identity_start'] = report.get('identity', getattr(backend, 'identity', None))
        save()
        backend.prepare()
        backend.restart()
        restarted = True
        report['candidate_identity_start'] = backend.candidate_identity()
        save()
        with backend.receiver() as receiver:
            receiver.select(0)
            receiver.generator()  # Query only; capture already requires OFF.
            for profile in rows:
                row = dict(profile, ok=False, measured=False)
                report['stages'].append(row)
                save()
                try:
                    measure(receiver, profile, row, save)
                except BaseException as exc:
                    row['error'] = repr(exc)
                    row['last_valid_status'] = dict(receiver.decoder.status) if receiver.decoder.status else None
                    row['last_pairs'] = receiver.decoder.pairs
                    report['stopped_on_failure'] = True
                    raise
                finally:
                    save()
        report['measurement_ok'] = len(report['stages']) == len(rows) and all(r['ok'] for r in report['stages'])
    except BaseException as exc:
        report['error'] = repr(exc)
    finally:
        # receiver.__exit__ has run, including when configure/pump/save raised.
        if restarted:
            try:
                report['candidate_identity_final'] = backend.candidate_identity()
                report['candidate_identity_equal'] = report['candidate_identity_final'] == report['candidate_identity_start']
            except BaseException as exc:
                report['candidate_identity_error'] = repr(exc)
        if captured:
            try:
                report['restoration'] = backend.restore()
                report['identity_final'] = backend.final_identity()
                report['identity_final_equal'] = report['identity_final'] == report['identity_start']
            except BaseException as exc:
                report['restore_error'] = repr(exc)
        report['ok'] = bool(report.get('measurement_ok') and report.get('candidate_identity_equal')
                            and report.get('identity_final_equal')
                            and report.get('restoration', {}).get('hardware_restored'))
        save()
    return report['ok']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Explicitly acquire Q and run the private transaction')
    parser.add_argument('--recipe',choices=('batchstack','batcharena'),default='batchstack')
    args = parser.parse_args(argv)
    rows = plan()
    if not args.run:
        print(json.dumps(dict(private=True, recipe=args.recipe, transport='SPI',
                              continuous_receiver=True, restarts=1, measurement_seconds=75,
                              acceptance='transition integrity only; no public rate promotion', stages=rows), indent=2))
        return 0
    from monitor.v18.board_owner import board_owner
    folder = EXP / 'resultados' / ('transitions_' + time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6])
    folder.mkdir(parents=True)
    (folder / 'runner.py').write_bytes(Path(__file__).read_bytes())
    report = dict(ok=False, measurement_ok=False, private=True, recipe=args.recipe, stages=[], plan=rows,
                  acceptance='transition integrity only; no public rate promotion',
                  runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    journal = ProbeJournal(folder / 'report.json', report)
    backend = TransitionHardware(folder, report)
    def interrupted(signum, frame):
        raise KeyboardInterrupt(f'signal {signum}')
    signal.signal(signal.SIGTERM, interrupted)
    with board_owner(backend.original.serial, 'V18 private BatchStack transitions'), private_profiles(backend.source):
        ok = orchestrate(backend, rows, report, journal.save)
    print(folder / 'report.json')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
