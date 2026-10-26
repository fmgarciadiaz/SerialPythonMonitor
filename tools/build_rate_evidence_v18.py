"""Build compact display provenance from restored physical reports; never uses Q."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'monitor/v18'


def build():
    receipt = json.loads((BASE/'q_support/accepted/acceptance.json').read_text())
    assert receipt['accepted'] is True
    pair = dict(firmware_sha256=receipt['firmware']['sha256'],relay_sha256=receipt['relay']['sha256'])
    rows = {}
    def row(case):
        key = tuple(case[name] for name in ('bits','channels','ticks','node_pairs'))
        return rows.setdefault(key,dict(zip(('bits','channels','ticks','node_pairs'),key)))
    for source in ('experimentos/fs_max_v18/resultados/20261025_201421/report.json',
                   'experimentos/fs_max_v18/resultados/20261025_203801/report.json'):
        report = json.loads((ROOT/source).read_text())
        assert report['ok'] and report['restoration']['hardware_restored']
        for case in report['cases']:
            assert case['ok'] and all(case['candidate_identity'][k]==v for k,v in pair.items())
            row(case)['adc_only'] = dict(seconds=case['seconds'],headroom_measured=case['headroom_ok'],
                queue_peak=case['queue_peak'],mean_send_margin=case['mean_send_margin'],evidence=source)
    source = 'diagnosticos/resultados_v18/radio_rates_review_20261026_130257/report.json'
    report = json.loads((ROOT/source).read_text())
    assert report['complete'] and report['ok'] and len(report['cases'])==37
    for case in report['cases']:
        outer = json.loads((ROOT/case['evidence']).read_text())
        gui = json.loads((ROOT/case['evidence']).with_name('gui.json').read_text())
        assert case['functional_ok'] and outer['restoration']['hardware_restored'] and outer['identity_unchanged']
        assert all(outer['identity'][k]==v for k,v in pair.items())
        assert not gui['errors'] and all(gui['assertions'].values()) and gui['radio_hold_seconds']>=case['hold']
        # Bind geometry from the executed profile, not display-rounded frequency.
        profile = outer['profile']
        assert all(profile[k]==case[k] for k in ('bits','channels','ticks'))
        row(profile)['radio_a0'] = dict(seconds=case['hold'],visible=outer['visible_gui_ok'],evidence=case['evidence'])
    # A later accepted-pair run adds visible-load evidence for ADC8 maximum.
    source='diagnosticos/resultados_v18/radio_rate_check_20261026_152756/report.json'
    outer=json.loads((ROOT/source).read_text())
    gui=json.loads((ROOT/source).with_name('gui.json').read_text())
    assert outer['ok'] and outer['visible_gui_ok'] and outer['restoration']['hardware_restored'] and outer['identity_unchanged']
    assert all(outer['identity'][k]==v for k,v in pair.items())
    assert not gui['errors'] and all(gui['assertions'].values()) and gui['radio_hold_seconds']>=120
    row(outer['profile'])['radio_a0']=dict(seconds=120,visible=True,evidence=source)
    return dict(schema=1,pair=pair,profiles=[rows[key] for key in sorted(rows)])


if __name__ == '__main__':
    target=BASE/'rate_evidence.json'
    target.write_text(json.dumps(build(),indent=2)+'\n')
    print(target)
