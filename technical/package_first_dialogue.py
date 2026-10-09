"""Preserve every Mare archive entry; transplant only OpenKH-encoded replacements."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out/first-dialogue"
GAME = Path("C:/Program Files (x86)/Steam/steamapps/common/KINGDOM HEARTS -HD 1.5+2.5 ReMIX-/Image")
IDXIMG = Path(os.environ.get("OPENKH_IDXIMG", str(ROOT / "technical/tools/OpenKh.Command.IdxImg.exe")))


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def records(path):
    data = path.read_bytes()
    assert len(data) % 32 == 0
    entries = [data[i:i + 32] for i in range(0, len(data), 32)]
    assert len({e[:16] for e in entries}) == len(entries)
    return entries


def build():
    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    original_entries = records(GAME / "Mare.hed")
    assert len(original_entries) == 2024
    encoded_entries = {e[:16]: e for e in records(OUT / "patched/Mare.hed")}
    wanted = {hashlib.md5(f["path"].removeprefix("original/").encode()).digest(): f for f in manifest["files"]}
    assert len(wanted) == 3 and wanted.keys() <= encoded_entries.keys()
    blocks = {}
    with (OUT / "patched/Mare.pkg").open("rb") as stream:
        for key in wanted:
            entry = encoded_entries[key]
            offset, size, _ = struct.unpack_from("<QII", entry, 16)
            stream.seek(offset)
            data = stream.read(size)
            assert len(data) == size
            blocks[key] = (entry, data)

    # Extract the three transplanted encrypted blocks before trusting any package.
    scratch = OUT / "verify-blocks"
    scratch.mkdir(exist_ok=True)
    index = bytearray()
    with (scratch / "Mare.pkg").open("wb") as stream:
        for key, (entry, block) in blocks.items():
            offset = stream.tell()
            index.extend(key + struct.pack("<Q", offset) + entry[24:])
            stream.write(block)
    (scratch / "Mare.hed").write_bytes(index)
    result = subprocess.run([str(IDXIMG), "hed", "extract", str(scratch / "Mare.hed"),
                             "-o", str(scratch / "extracted")], capture_output=True, text=True, check=True)
    (scratch / "extract.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    for file in manifest["files"]:
        extracted = scratch / "extracted" / file["path"]
        assert extracted.is_file(), str(extracted)
        assert sha(extracted) == file["sha256"], str(extracted)

    source_hashes = {name: sha(GAME / name) for name in ["Mare.hed", "Mare.pkg"]}
    stages = {}
    for stage in ["font-only", "first-dialogue"]:
        selected = {k for k, f in wanted.items() if stage == "first-dialogue" or "/font/" in f["path"]}
        dest = OUT / "archives" / stage
        dest.mkdir(parents=True, exist_ok=True)
        package = dest / "Mare.pkg"
        # Original compressed/encrypted data remains byte-identical, even for unknown names.
        shutil.copyfile(GAME / "Mare.pkg", package)
        updated = []
        with package.open("ab") as stream:
            for entry in original_entries:
                key = entry[:16]
                if key in selected:
                    replacement, block = blocks[key]
                    stream.write(bytes((-stream.tell()) % 16))
                    offset = stream.tell()
                    stream.write(block)
                    updated.append(key + struct.pack("<Q", offset) + replacement[24:])
                else:
                    updated.append(entry)
        (dest / "Mare.hed").write_bytes(b"".join(updated))
        assert len(updated) == len(original_entries)
        assert [e[:16] for e in updated] == [e[:16] for e in original_entries]
        assert sum(a != b for a, b in zip(original_entries, updated)) == len(selected)
        assert all(a == b for a, b in zip(original_entries, updated) if a[:16] not in selected)
        with package.open("rb") as stream:
            prefix_hash = hashlib.sha256()
            remaining = (GAME / "Mare.pkg").stat().st_size
            while remaining:
                chunk = stream.read(min(4 * 1024 * 1024, remaining))
                assert chunk
                prefix_hash.update(chunk)
                remaining -= len(chunk)
            assert prefix_hash.hexdigest() == source_hashes["Mare.pkg"]
            for entry in updated:
                if entry[:16] in selected:
                    offset, size, _ = struct.unpack_from("<QII", entry, 16)
                    stream.seek(offset)
                    assert stream.read(size) == blocks[entry[:16]][1]
        stages[stage] = {"entry_count": len(updated), "changed_entries": len(selected),
                         "files": {name: {"bytes": (dest / name).stat().st_size, "sha256": sha(dest / name)} for name in source_hashes}}
    assert {name: sha(GAME / name) for name in source_hashes} == source_hashes
    report = {"source": source_hashes, "stages": stages, "unknown_entries_preserved": 57,
              "payload_extract_hashes_match": True, "original_game_unchanged": True,
              "warning": "OpenKH hed patch output under patched/ loses 57 entries; never install that intermediate output.",
              "installed": False, "in_game_verified": False}
    (OUT / "package-manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["unknown_entries_preserved", "payload_extract_hashes_match", "original_game_unchanged"]}))


if __name__ == "__main__":
    build()
