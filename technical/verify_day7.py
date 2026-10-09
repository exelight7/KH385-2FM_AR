"""Independently trace Day 7 chapters and verify built subtitle coverage."""
import hashlib
import html
import json
from pathlib import Path
import re
import struct
import subprocess
import xml.etree.ElementTree as ET

import arabic_reshaper
from bidi.algorithm import get_display

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "technical/extracted_mare/original"
PAYLOAD = ROOT / "out/first-dialogue/payload/original"
OUTPUT = ROOT / "technical/verification/day7-scope.json"
CATEGORY = re.compile(r'<SCHEDULE_CATEGORY\b[^>]*>.*?</SCHEDULE_CATEGORY>', re.S)
DATA = re.compile(r'<DATA\b[^>]*TextID="(?P<id>[0-9a-fA-F]+)"[^>]*Text="(?P<text>.*?)"\s*/>', re.S)


def xml(path):
    raw = path.read_bytes()
    end = raw.index(b"</EXUSIA2_XML>") + len(b"</EXUSIA2_XML>")
    value = raw[:end].decode("utf-8")
    ET.fromstring(value)
    assert raw[end:].startswith(b"\r\n")
    assert set(raw[end + 2:]) <= {0xCD}
    assert len(raw) % 16 == 0
    return value


def english_data(value):
    result = []
    for category in CATEGORY.finditer(value):
        if re.search(r'<PARAM[^>]+Language="LANGUAGE_EN"', category.group()):
            for match in DATA.finditer(category.group()):
                result.append((int(match["id"], 16), html.unescape(match["text"]).replace("\r\n", "\n")))
    return result


def read_ctds(paths):
    code = r"""
const fs=require('fs'), c=require('./technical/tools/kh-localization-tool/tools/lib/ddd-ctd');
const assert=require('assert/strict');
let input=JSON.parse(fs.readFileSync(0,'utf8')),out={};
for(const [key,path] of Object.entries(input)){
 const b=fs.readFileSync(path), p=c.parseDddCtd(b);
 assert(c.composeDddCtd(p).equals(b),key+' roundtrip');
 out[key]=p.entries.map(e=>({index:e.index,id:e.id,layout:e.layout,text:e.text}));
}
console.log(JSON.stringify(out));
"""
    run = subprocess.run(["node", "-e", code], cwd=ROOT,
                         input=json.dumps({k: str(v) for k, v in paths.items()}),
                         text=True, encoding="utf-8", capture_output=True, check=True)
    return json.loads(run.stdout)


def verify():
    chp = (SOURCE / "data/DaysTheater.chp").read_bytes()
    thd = (SOURCE / "data/DaysTheater.thd").read_bytes()
    assert chp[:4] == b"CHP@" and thd[:4] == b"THD@"
    chapters = struct.unpack_from("<H", chp, 6)[0]
    candidates = [i for i in range(chapters)
                  if chp[8 + i * 96:8 + i * 96 + 2] == b"\0\0"
                  and struct.unpack_from("<H", chp, 8 + i * 96 + 2)[0] == 7]
    assert candidates == [2], candidates
    chapter = 8 + candidates[0] * 96
    sequence_count = struct.unpack_from("<I", chp, chapter + 32)[0]
    sequences = struct.unpack_from("<" + "H" * sequence_count, chp, chapter + 36)
    assert sequences == (2, 3, 188)
    strings = 16 + struct.unpack_from("<H", thd, 6)[0] * 28
    sources = []
    day_ids = set()
    for sequence in sequences:
        record = 16 + sequence * 28
        string_offset = struct.unpack_from("<I", thd, record + 8)[0]
        movie = thd[strings + string_offset:].split(b"\0", 1)[0].decode("ascii")
        path = "uk/event/en/hd/" + movie
        rows = english_data(xml(SOURCE / path))
        day_ids.update(ident for ident, _ in rows)
        sources.append({"sequence": sequence, "thd_record_offset": record,
                        "path": path, "visible_english_rows": len(rows),
                        "message_ids": [f"{ident:08x}" for ident, _ in rows]})
    assert day_ids == {0x02018000, 0x02018100, 0x02018200, 0x02018300,
                       0x03918000, 0x03918100, 0x03918200, 0x03918300}
    translations = json.loads((ROOT / "translation/first_dialogue.json").read_text(encoding="utf-8"))
    by_id = {int(row["id"], 16): row for row in translations}
    assert len(by_id) == len(translations) and day_ids <= by_id.keys()
    allocation = json.loads((ROOT / "out/first-dialogue/allocation.json").read_text(encoding="utf-8"))
    glyphs = {chr(int(entry["form"][2:], 16)): chr(entry["id"]) for entry in allocation}
    reverse = {value: key for key, value in glyphs.items()}
    expected = {}
    for ident, row in by_id.items():
        visual = get_display(arabic_reshaper.reshape(row["arabic"]))
        expected[ident] = "".join(glyphs.get(char, char) for char in visual)
    paths = {"menu": SOURCE / "uk/ctd/ct00100.ctd"}
    for relative in {row["file"] for row in translations}:
        paths["source:" + relative] = SOURCE / relative
        paths["built:" + relative] = PAYLOAD / relative
    ctds = read_ctds(paths)
    selector_id = struct.unpack_from("<I", chp, chapter + 4)[0]
    selector = next(entry["text"] for entry in ctds["menu"] if entry["id"] == selector_id)
    assert selector == "Number XIV"
    for relative in {row["file"] for row in translations}:
        original, built = ctds["source:" + relative], ctds["built:" + relative]
        assert len(original) == len(built)
        for before, after in zip(original, built):
            assert before["id"] == after["id"] and before["layout"] == after["layout"]
            ident = before["id"]
            if ident in by_id:
                row = by_id[ident]
                assert row["file"] == relative and row["index"] == before["index"]
                assert before["text"] == row["english"]
                assert after["text"] == expected[ident]
                assert "".join(reverse.get(char, char) for char in after["text"]) == get_display(arabic_reshaper.reshape(row["arabic"]))
            else:
                assert after == before
    covered = set()
    xml_files = []
    for movie in ["hd000", "hd003", "hd004", "hd803"]:
        relative = f"uk/event/en/hd/{movie}/{movie}.exia2"
        before, after = xml(SOURCE / relative), xml(PAYLOAD / relative)
        strip_text = lambda s: re.sub(r' Text=".*?"', ' Text=""', s, flags=re.S)
        assert strip_text(before) == strip_text(after), relative + " non-text/timing change"
        before_categories, after_categories = list(CATEGORY.finditer(before)), list(CATEGORY.finditer(after))
        assert len(before_categories) == len(after_categories)
        for left, right in zip(before_categories, after_categories):
            if not re.search(r'<PARAM[^>]+Language="LANGUAGE_EN"', left.group()):
                assert left.group() == right.group(), relative + " non-English change"
        original_rows, built_rows = english_data(before), english_data(after)
        assert [ident for ident, _ in original_rows] == [ident for ident, _ in built_rows]
        for (ident, english), (_, mapped) in zip(original_rows, built_rows):
            assert ident in by_id and english == by_id[ident]["english"]
            assert mapped == expected[ident], (relative, ident)
            covered.add(ident)
        xml_files.append({"path": relative, "verified_rows": len(built_rows),
                          "timing_and_other_languages_unchanged": True})
    assert covered == set(by_id)
    for source in sources:
        for ident, english in english_data(xml(SOURCE / source["path"])):
            assert english == by_id[ident]["english"]
    proof = {"version": "0.2.0", "day": 7, "chapter_selector": selector,
             "chp_record_index": candidates[0], "chp_record_offset": chapter,
             "day7_visible_rows": len(day_ids), "day7_translated_rows": len(day_ids),
             "day7_message_ids": [f"{ident:08x}" for ident in sorted(day_ids)],
             "sequences": sources, "cumulative_translated_rows": len(translations),
             "ctd_payload_roundtrip_and_expected_glyphs": True,
             "xml_payload_expected_glyphs": True, "xml_files": xml_files,
             "original_chp_sha256": hashlib.sha256(chp).hexdigest(),
             "original_thd_sha256": hashlib.sha256(thd).hexdigest(),
             "runtime_text_attribute_usage_confirmed": False,
             "in_game_verified": False}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"day": 7, "chapter": selector, "covered": len(day_ids), "cumulative": len(translations), "result": "PASS"}))


if __name__ == "__main__":
    verify()
