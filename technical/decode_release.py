"""Rebuild a published release's changed files from its frozen patch and the owned original.

The 1.0.2 builder never reached the repository, so its font and day-96 handling
can only be read back this way. Writes under out/; the game files stay read-only.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

from original_archive import original_archive

ROOT = Path(__file__).resolve().parents[1]
IDXIMG = Path(os.environ.get('OPENKH_IDXIMG', str(ROOT / 'technical/tools/openkh/openkh/Apps/OpenKh.Command.IdxImg.exe')))


def main(version, patch_dir):
    manifest = json.loads((ROOT / f'technical/verification/v{version}-manifest.json').read_text(encoding='utf-8'))
    assert manifest['version'] == version
    game = original_archive()
    source_hed = (game / 'Mare.hed').read_bytes()
    assert hashlib.sha256(source_hed).hexdigest() == manifest['source']['Mare.hed']['sha256'], 'different game build'
    delta = gzip.decompress((patch_dir / 'tail.gz').read_bytes())
    assert hashlib.sha256(delta).hexdigest() == manifest['delta']['sha256']
    # XOR with original bytes, as big integers: the segments are megabytes long.
    tail = bytearray(delta)
    with (game / 'Mare.pkg').open('rb') as stream:
        for segment in manifest['delta']['baseSegments']:
            stream.seek(segment['sourceOffset'])
            base = stream.read(segment['bytes'])
            assert len(base) == segment['bytes']
            start, end = segment['tailOffset'], segment['tailOffset']+segment['bytes']
            mixed = int.from_bytes(tail[start:end], 'little') ^ int.from_bytes(base, 'little')
            tail[start:end] = mixed.to_bytes(segment['bytes'], 'little')
    assert hashlib.sha256(tail).hexdigest() == manifest['tail']['sha256'], 'tail does not match the release'
    size = manifest['source']['Mare.pkg']['bytes']
    out = ROOT / f'out/v{version}'
    scratch = out / 'decode'
    scratch.mkdir(parents=True, exist_ok=True)
    index = bytearray()
    for change in manifest['hedChanges']:
        record = bytes.fromhex(change['after'])
        offset, *_ = struct.unpack_from('<QII', record, 16)
        assert offset >= size
        index.extend(record[:16]+struct.pack('<Q', offset-size)+record[24:])
    (scratch / 'Mare.pkg').write_bytes(tail)
    (scratch / 'Mare.hed').write_bytes(index)
    subprocess.run([str(IDXIMG), 'hed', 'extract', str(scratch / 'Mare.hed'), '-o', str(out / 'payload')], check=True)
    print(json.dumps({'version': version, 'files': len(manifest['hedChanges']), 'payload': str(out / 'payload')}))
    recover_allocation(version, out)


def recover_allocation(version, out):
    """Read the release's glyph table back by aligning its CTD rows with the reviewed text."""
    from build_v030 import visual, TAG
    rows = [r for p in sorted((ROOT / 'translation/v1.0.1').glob('ct*.json')) for r in json.loads(p.read_text(encoding='utf-8')) if r['arabic'] != r['english']]
    script = r"""
const fs=require('fs'),c=require('./technical/tools/kh-localization-tool/tools/lib/ddd-ctd');const out={};
for(const rel of JSON.parse(fs.readFileSync(0,'utf8')).files)out[rel]=c.parseDddCtd(fs.readFileSync(rel)).entries.map(e=>e.text);
console.log(JSON.stringify(out));"""
    rel = lambda row: (out / 'payload/original' / row['file']).relative_to(ROOT).as_posix()
    shipped = json.loads(subprocess.run(['node', '-e', script], cwd=ROOT, input=json.dumps({'files': sorted({rel(r) for r in rows})}), text=True, encoding='utf-8', capture_output=True, check=True).stdout)
    seen, conflicts, unaligned = {}, [], []
    for row in rows:
        # This row's word order was wrong in every release before 2.0.0.
        if '{BTN_Y}' in row['arabic']:
            continue
        text = TAG.sub('', shipped[rel(row)][row['index']])
        expected = TAG.sub('', visual(row['arabic']))
        if len(text) != len(expected):
            unaligned.append(row['id'])
            continue
        for code, char in zip(text, expected):
            if ord(char) > 127 or char in ' .!:/()':
                if seen.setdefault(char, code) != code:
                    conflicts.append([row['id'], f'U+{ord(char):04X}'])
    (out / 'allocation.json').write_text(json.dumps([{'form': f'U+{ord(c):04X}', 'id': ord(d)} for c, d in seen.items()], indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'forms': len(seen), 'conflicts': len(conflicts), 'conflictExamples': conflicts[:10], 'unalignedRows': len(unaligned), 'unalignedExamples': unaligned[:10]}))


if __name__ == '__main__':
    main(sys.argv[1], Path(sys.argv[2]))
