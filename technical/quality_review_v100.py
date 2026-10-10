"""Verify two fresh bilingual reviews of every row and their correction chain."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'translation/v1.0.0'
PREVIOUS = ROOT / 'translation/v0.4.1'
NAMES = ['ct00100', 'ctmn000', 'ctmn200', 'ctmn300', 'cthd000', 'cthd050', 'cthd100', 'cthd300', 'cthd800']
TAG = re.compile(r'(\{[^}]+\}|\[(?:BGTRANS|WAIT)[^]]*\])')

def canonical(path):
    return hashlib.sha256(path.read_text(encoding='utf-8').encode('utf-8')).hexdigest()

def main():
    reports = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((DIR / 'reviews').glob('*.json'))]
    assert len(reports) == 6
    files, keys, changes, events = {}, [], [], []
    for name in NAMES:
        path = DIR / f'{name}.json'
        rows = json.loads(path.read_text(encoding='utf-8'))
        old = json.loads((PREVIOUS / path.name).read_text(encoding='utf-8'))
        reviews = sorted([r for r in reports if name in r['files']], key=lambda r: r['pass'])
        assert [r['pass'] for r in reviews] == [1, 2]
        assert len({r['reviewer'] for r in reviews}) == 2
        expected = canonical(PREVIOUS / path.name)
        for review in reviews:
            assert review['status'] == 'complete' and not review.get('unresolved')
            item = review['files'][name]
            assert item['reviewedRows'] == len(rows) and not item.get('unresolved')
            assert item['reviewedIds'] == [r['id'] for r in rows]
            assert item['inputCanonicalSha256'] == expected, (name, review['pass'], 'broken review chain')
            expected = item['outputCanonicalSha256']
            for c in review.get('corrections', []):
                if Path(c['file']).stem == name:
                    events.append(dict(c, file=name, passNumber=review['pass'], reviewer=review['reviewer']))
        assert expected == canonical(path), (name, 'modified after final review')
        assert len(old) == len(rows)
        technical = 0
        for a, b in zip(old, rows):
            assert {k: v for k, v in a.items() if k != 'arabic'} == {k: v for k, v in b.items() if k != 'arabic'}
            if name == 'ct00100' and 491 <= b['index'] <= 585:
                assert b['arabic'] == b['english'] == a['arabic'] and b['english'].startswith('hd')
                keys.append(dict(id=b['id'], index=b['index'], value=b['english']))
                technical += 1
            else:
                assert b['arabic'].strip() and b['arabic'] != b['english']
                assert b['arabic'].count('\n') == b['english'].count('\n')
                assert [not s.strip() for s in b['arabic'].split('\n')] == [not s.strip() for s in b['english'].split('\n')]
                assert TAG.findall(b['arabic']) == TAG.findall(b['english'])
                assert not re.search('[\u064b-\u065f\u0640\u200e\u200f]', b['arabic'])
            row_events = [e for e in events if e['file'] == name and e['id'] == b['id']]
            current = a['arabic']
            for e in row_events:
                assert e['before'] == current and e['english'] == a['english']
                current = e['after']
            assert current == b['arabic'], (name, b['id'], 'unreported edit')
            if a['arabic'] != b['arabic']:
                changes.append(dict(file=name, id=b['id'], index=b['index'], english=b['english'], before=a['arabic'], after=b['arabic'], reasons=[e['reason'] for e in row_events]))
        files[name] = dict(reviewedRows=len(rows), translatedRows=len(rows)-technical, canonicalSha256=expected, passes=2, reviewers=[r['reviewer'] for r in reviews], freshFullReview=True)
    assert len(keys) == 95 and sum(f['translatedRows'] for f in files.values()) == 2461
    previous_report = json.loads((PREVIOUS / 'quality-report.json').read_text(encoding='utf-8'))
    proof = dict(version='1.0.0', status='complete', translatedEntries=2461, freshlyReviewedEntries=2461, reviewPasses=2, legacyInventoryEntries=2556, technicalResourceKeysPreserved=keys, files=files, correctionEvents=len(events), distinctCorrectedRows=len(changes), corrections=events, changesFrom041=changes, inGameVerified=False, unresolved=[], metric=previous_report['metric'], scopeExclusions=previous_report['scopeExclusions'], sharedContentIncluded=previous_report['sharedContentIncluded'], remainingVisualWork=previous_report['remainingVisualWork'])
    (DIR / 'quality-report.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: proof[k] for k in ['translatedEntries', 'freshlyReviewedEntries', 'reviewPasses', 'correctionEvents', 'distinctCorrectedRows']}))

if __name__ == '__main__':
    main()
