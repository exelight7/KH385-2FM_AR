"""Audit final changes against the frozen 0.3.0 text and both review passes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'translation/v0.4.0'


def main():
    reports = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((DEST / 'reviews').glob('*.json'))]
    changes = []
    counts = {}
    reviewed = 0
    for name in ('cthd000', 'cthd050', 'cthd100', 'cthd300', 'cthd800'):
        old = json.loads((ROOT / f'translation/v0.3.0/{name}.json').read_text(encoding='utf-8'))
        new = json.loads((DEST / f'{name}.json').read_text(encoding='utf-8'))
        assert len(old) == len(new)
        passes = [r for r in reports if name in r.get('files', {})]
        assert len(passes) == 2 and {r['pass'] for r in passes} == {1, 2}
        assert len({r['reviewer'] for r in passes}) == 2
        for report in passes:
            info = report['files'][name]
            assert report['status'] == 'complete' and not report.get('unresolved') and not info.get('unresolved')
            assert info['reviewedRows'] == len(new)
            if report['pass'] == 2:
                canonical = (DEST / f'{name}.json').read_text(encoding='utf-8').encode('utf-8')
                assert info['outputCanonicalSha256'] == hashlib.sha256(canonical).hexdigest()
        counts[name] = 0
        for before, after in zip(old, new):
            assert {k: v for k, v in before.items() if k != 'arabic'} == {k: v for k, v in after.items() if k != 'arabic'}
            reviewed += 1
            if before['arabic'] == after['arabic']:
                continue
            trail = [c for r in passes for c in r.get('corrections', []) if Path(c['file']).stem == name and c['id'] == after['id']]
            assert trail, (name, after['id'], 'unrecorded change')
            changes.append({'file': name, 'index': after['index'], 'id': after['id'], 'english': after['english'],
                            'before': before['arabic'], 'after': after['arabic'],
                            'reasons': [c['reason'] for c in trail], 'categories': sorted({c['category'] for c in trail})})
            counts[name] += 1
    assert reviewed == 1616
    report = {'version': '0.4.0', 'baseline': '0.3.0', 'reviewedEntriesPerPass': reviewed, 'independentPasses': 2,
              'changedRows': len(changes), 'changedRowsPerFile': counts, 'unresolved': [], 'changes': changes}
    (DEST / 'quality-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'changes'}))


if __name__ == '__main__':
    main()
