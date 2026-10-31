"""Audit a corrective version against frozen 1.0.1 rows; claims no fresh bilingual review."""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'translation/v1.0.1'
NAMES = ['ct00100', 'ctmn000', 'ctmn200', 'ctmn300', 'cthd000', 'cthd050', 'cthd100', 'cthd300', 'cthd800']
TAG = re.compile(r'(\{[^}]+\}|\[(?:BGTRANS|WAIT)[^]]*\])')


def canonical(path):
    return hashlib.sha256(path.read_text(encoding='utf-8').encode('utf-8')).hexdigest()


def audit(version):
    folder = ROOT / f'translation/v{version}'
    log = json.loads((folder / 'corrections.json').read_text(encoding='utf-8'))
    assert log['version'] == version and log['freshBilingualReview'] is False
    pending = {(c['file'], c['id']): c for c in log['corrections']}
    assert len(pending) == len(log['corrections']), 'one log entry per corrected row'
    files, keys = {}, 0
    for name in NAMES:
        path = folder / f'{name}.json'
        rows = json.loads(path.read_text(encoding='utf-8'))
        old = json.loads((BASE / path.name).read_text(encoding='utf-8'))
        assert len(rows) == len(old)
        technical = 0
        for a, b in zip(old, rows):
            assert {k: v for k, v in a.items() if k != 'arabic'} == {k: v for k, v in b.items() if k != 'arabic'}
            if name == 'ct00100' and 491 <= b['index'] <= 585:
                assert b['arabic'] == b['english'] == a['arabic'] and b['english'].startswith('hd')
                technical += 1
                continue
            assert b['arabic'].strip() and b['arabic'] != b['english']
            assert b['arabic'].count('\n') == b['english'].count('\n')
            assert [not s.strip() for s in b['arabic'].split('\n')] == [not s.strip() for s in b['english'].split('\n')]
            assert TAG.findall(b['arabic']) == TAG.findall(b['english'])
            assert not re.search('[ً-ٟـ‎‏]', b['arabic'])
            if a['arabic'] != b['arabic']:
                entry = pending.pop((name, b['id']), None)
                assert entry, (name, b['id'], 'unlogged edit')
                assert entry['before'] == a['arabic'] and entry['after'] == b['arabic'], (name, b['id'])
        keys += technical
        files[name] = dict(translatedRows=len(rows) - technical, canonicalSha256=canonical(path))
    assert not pending, ('logged but not applied', sorted(pending))
    assert keys == 95 and sum(f['translatedRows'] for f in files.values()) == 2461
    return dict(version=version, status='complete', translatedEntries=2461, technicalResourceKeysPreserved=keys, base=log['base'], correctedRows=len(log['corrections']), corrections=log['corrections'], files=files, method=log['method'], inheritedReviewsFrom=log['inheritedReviewsFrom'], inheritedReviewPasses=2, freshBilingualReview=False, inGameVerified=False)


def main(version):
    proof = audit(version)
    (ROOT / f'translation/v{version}/quality-report.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: proof[k] for k in ['version', 'translatedEntries', 'correctedRows', 'freshBilingualReview']}))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '2.0.0')
