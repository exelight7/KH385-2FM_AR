"""Read-only proof of what the installed 0.2.0 patch changed."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = Path('C:/Program Files (x86)/Steam/steamapps/common/KINGDOM HEARTS -HD 1.5+2.5 ReMIX-/Image')

def audit():
    manifest = json.loads((ROOT / 'technical/verification/v0.2.0-manifest.json').read_text(encoding='utf-8'))
    before = (IMAGE / '.days-arabic-backup/Mare.hed').read_bytes()
    after = (IMAGE / 'Mare.hed').read_bytes()
    assert hashlib.sha256(before).hexdigest() == manifest['source']['Mare.hed']['sha256']
    assert hashlib.sha256(after).hexdigest() == manifest['target']['Mare.hed']['sha256']
    offsets = [i for i in range(0, len(before), 32) if before[i:i+32] != after[i:i+32]]
    assert offsets == [change['offset'] for change in manifest['hedChanges']]
    built = json.loads((ROOT / 'out/first-dialogue/manifest.json').read_text(encoding='utf-8'))
    paths = [file['path'].removeprefix('original/') for file in built['files']]
    assert {after[i:i+16] for i in offsets} == {hashlib.md5(p.encode()).digest() for p in paths}
    assert all(p.endswith(('.ctd', '.cod', '.tm2', '.exia2')) for p in paths)
    full, prefix = hashlib.sha256(), hashlib.sha256()
    remaining = manifest['source']['Mare.pkg']['bytes']
    with (IMAGE / 'Mare.pkg').open('rb') as stream:
        while block := stream.read(4 * 1024 * 1024):
            full.update(block)
            prefix.update(block[:remaining])
            remaining = max(0, remaining - len(block))
    assert full.hexdigest() == manifest['target']['Mare.pkg']['sha256']
    assert prefix.hexdigest() == manifest['source']['Mare.pkg']['sha256']
    report = {'version': '0.2.0', 'installed_archive_hashes_match_release': True,
              'original_pkg_prefix_byte_identical': True, 'changed_archive_paths': paths,
              'unmodified_hed_records': len(before)//32 - len(offsets),
              'movie_files_written_by_installer': [],
              'movie_reencoding_in_pipeline': False,
              'visual_quality_cause_confirmed': False,
              'limit': 'No before/after full-frame movie comparison supplied. User has not tested the same scene after uninstall.'}
    (ROOT / 'technical/verification/video-integrity.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'installed': '0.2.0', 'unchanged_records': report['unmodified_hed_records'], 'video_reencoded': False}))

if __name__ == '__main__':
    audit()
