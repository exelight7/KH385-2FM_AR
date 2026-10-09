"""Locate verified owned originals, including backups after installing a patch."""
import hashlib
import os
from pathlib import Path

LIVE = Path(os.environ.get('DAYS_GAME_IMAGE', 'C:/Program Files (x86)/Steam/steamapps/common/KINGDOM HEARTS -HD 1.5+2.5 ReMIX-/Image'))
HASHES = {'Mare.hed': '1e5e8fb26cf0eb52e2c37a542bc3218fcf3c48b286c8495109af73c3777e420f',
          'Mare.pkg': '5a3a20283ce7dd2edcd9c96a898c4a6d00c03d5592f3e06f3caaafb7e32980b1'}

def original_archive():
    for folder in [LIVE / '.days-arabic-backup', LIVE]:
        if all((folder / n).is_file() for n in HASHES):
            valid = True
            for name, expected in HASHES.items():
                with (folder / name).open('rb') as stream:
                    valid &= hashlib.file_digest(stream, 'sha256').hexdigest() == expected
            if valid:
                return folder
    raise RuntimeError('No verified original Mare pair found; restore using Steam or a verified original backup.')
