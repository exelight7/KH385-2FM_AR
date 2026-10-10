"""Export XOR differences against owned archive blocks, plus verified HED changes."""
import gzip
import hashlib
import json
import struct
import os
from pathlib import Path
import numpy as np
from original_archive import original_archive

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('DAYS_BUILD_DIR', str(ROOT / 'out/first-dialogue')))
GAME = original_archive()


def main():
    report = json.loads((OUT / 'package-manifest.json').read_text())
    translation = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
    archive = OUT / 'archives/first-dialogue'
    dest = ROOT / 'installer/patch'
    dest.mkdir(parents=True, exist_ok=True)
    source = {n: {'bytes': (GAME / n).stat().st_size, 'sha256': h} for n, h in report['source'].items()}
    target = report['stages']['first-dialogue']['files']
    before, after = (GAME / 'Mare.hed').read_bytes(), (archive / 'Mare.hed').read_bytes()
    changes = [{'offset': i, 'before': before[i:i+32].hex(), 'after': after[i:i+32].hex()}
               for i in range(0, len(before), 32) if before[i:i+32] != after[i:i+32]]
    assert len(changes) == len(translation['files']) and len(before) == len(after)
    with (archive / 'Mare.pkg').open('rb') as f:
        f.seek(source['Mare.pkg']['bytes'])
        tail = f.read()
    assert len(tail) == target['Mare.pkg']['bytes'] - source['Mare.pkg']['bytes']
    delta = bytearray(tail)
    segments = []
    with (GAME / 'Mare.pkg').open('rb') as f:
        for change in changes:
            old_offset, old_size, _ = struct.unpack_from('<QII', bytes.fromhex(change['before']), 16)
            new_offset, new_size, _ = struct.unpack_from('<QII', bytes.fromhex(change['after']), 16)
            count = min(old_size, new_size)
            tail_offset = new_offset - source['Mare.pkg']['bytes']
            assert old_offset + count <= source['Mare.pkg']['bytes'] and tail_offset >= 0
            f.seek(old_offset)
            base = f.read(count)
            assert len(base) == count
            view = np.frombuffer(delta, dtype=np.uint8, count=count, offset=tail_offset)
            view ^= np.frombuffer(base, dtype=np.uint8)
            segments.append({'sourceOffset': old_offset, 'tailOffset': tail_offset, 'bytes': count})
    segments.sort(key=lambda x: x['tailOffset'])
    compressed = gzip.compress(delta, compresslevel=9, mtime=0)
    (dest / 'tail.gz').write_bytes(compressed)
    previous = json.loads((ROOT / 'technical/verification/v0.4.0-manifest.json').read_text(encoding='utf-8'))['target']
    older = json.loads((ROOT / 'technical/verification/v0.3.0-manifest.json').read_text(encoding='utf-8'))['target']
    earlier = json.loads((ROOT / 'technical/verification/v0.2.0-manifest.json').read_text(encoding='utf-8'))['target']
    legacy = json.loads((ROOT / 'technical/verification/v0.1.0-manifest.json').read_text(encoding='utf-8'))['target']
    version = json.loads((ROOT / 'installer/package.json').read_text(encoding='utf-8'))['version']
    assert translation['version']==version, 'Build and installer versions must match'
    manifest = {'format': 2, 'version': version, 'title': 'KINGDOM HEARTS 358/2 Days',
                'previous': previous, 'older': older, 'earlier': earlier, 'legacy': legacy,
                'translatedEntries': translation['changed_messages'], 'totalVisibleEntries': translation['totalVisibleEntries'],
                'preservedTechnicalKeys': len(translation.get('technicalResourceKeysPreserved', [])),
                'translatedImageLabels': translation.get('uiArt', {}).get('count', 0),
                'inGameVerified': False, 'source': source, 'target': target,
                'tail': {'bytes': len(tail), 'sha256': hashlib.sha256(tail).hexdigest()},
                'delta': {'file': 'tail.gz', 'bytes': len(delta), 'sha256': hashlib.sha256(delta).hexdigest(), 'baseSegments': segments},
                'hedChanges': changes}
    (dest / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'translated': manifest['translatedEntries'], 'compressedBytes': len(compressed), 'rawBytes': len(tail)}))


if __name__ == '__main__':
    main()
