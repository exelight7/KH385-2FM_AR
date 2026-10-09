"""Build-only Day 7 and opening subtitles using LittleBitUA's CTD/font readers and writer."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unicodedata
import re
import html

import arabic_reshaper
from bidi.algorithm import get_display
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "technical/extracted_mare/original/uk"
TOOL = ROOT / "technical/tools/kh-localization-tool"
OUTPUT = ROOT / "out/first-dialogue"
FONT_REL = "uk/font/eventfont"
FONT = Path("C:/Windows/Fonts/segoeuib.ttf")


def node(code, data=None):
    result = subprocess.run(["node", "-e", code], cwd=ROOT,
                            input=json.dumps(data, ensure_ascii=True),
                            text=True, encoding="utf-8", capture_output=True, check=True)
    return json.loads(result.stdout)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build():
    rows = json.loads((ROOT / "translation/first_dialogue.json").read_text(encoding="utf-8"))
    metadata = node(r"""
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const ctd=require('./technical/tools/kh-localization-tool/tools/lib/ddd-ctd');
const font=require('./technical/tools/kh-localization-tool/tools/lib/bbs-font');
let pass=0,englishCodes=new Set();
function walk(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){
 const f=path.join(dir,e.name);if(e.isDirectory())walk(f);else if(/\.ctd$/i.test(f)){
 const b=fs.readFileSync(f),p=ctd.parseDddCtd(b);assert(ctd.composeDddCtd(p).equals(b),f);
 pass++;if(f.split(path.sep).includes('uk'))for(const e of p.entries)for(const c of e.codes)englishCodes.add(c);
}}}
walk('./technical/extracted_mare/original');walk('./technical/extracted/original');
const base='./technical/extracted_mare/original/uk/font/eventfont';
const cod=fs.readFileSync(base+'.cod'),entries=font.parseCod(cod);
assert(font.composeCod(entries).equals(cod));
console.log(JSON.stringify({roundtripPass:pass,englishCodes:[...englishCodes],entries,
 inf:font.parseInf(fs.readFileSync(base+'.inf'))}));
""")
    assert metadata["roundtripPass"] == 92
    inf = metadata["inf"]
    assert (inf["textureWidth"], inf["textureHeight"], inf["charWidth"], inf["charHeight"]) == (2048, 2048, 32, 32)
    entries = metadata["entries"]
    valid = entries[:inf["charCount"]]  # The final eight bytes are 0xCD padding, not a glyph.
    used = set(metadata["englishCodes"])
    visual = [get_display(arabic_reshaper.reshape(row["arabic"])) for row in rows]
    forms = sorted({c for line in visual for c in line if ord(c) > 127})
    donors = [e for e in valid if 0x3040 <= e["id"] < 0x3100 and e["id"] not in used]
    assert len(donors) >= len(forms)
    allocation = {char: dict(entry) for char, entry in zip(forms, donors)}
    mapped = ["".join(chr(allocation[c]["id"]) if c in allocation else c for c in line) for line in visual]
    inverse = {chr(e["id"]): c for c, e in allocation.items()}
    assert ["".join(inverse.get(c, c) for c in line) for line in mapped] == visual
    assert all(row["arabic"].count("\n") == row["english"].count("\n") for row in rows)

    original = (SOURCE / "font/eventfont.tm2").read_bytes()
    assert original[:4] == b"TIM2" and original[34:36] == bytes([3, 5])
    _, palette_size, image_size, header_size = struct.unpack_from("<IIIH", original, 16)
    width, height = struct.unpack_from("<HH", original, 36)
    assert (width, height, image_size, palette_size) == (2048, 2048, 2048 * 2048, 1024)
    start = 16 + header_size
    pixels = np.frombuffer(original[start:start + image_size], dtype=np.uint8).reshape(height, width).copy()
    before = pixels.copy()
    palette = np.frombuffer(original[start + image_size:start + image_size + palette_size], dtype=np.uint8).reshape(256, 4)
    order = [(i & ~31) | ((i & 8) << 1) | ((i & 16) >> 1) | (i & 7) for i in range(256)]
    rgba = palette[order].astype(np.int32)
    allowed = np.zeros((height, width), dtype=bool)
    font = ImageFont.truetype(str(FONT), 24 * 4, layout_engine=ImageFont.Layout.BASIC)
    glyphs = {}
    for char, entry in allocation.items():
        advance = round(font.getlength(char) / 4)
        assert 0 < advance <= 30
        mask = Image.new("L", (128, 128))
        draw = ImageDraw.Draw(mask)
        bbox = draw.textbbox((8, 100), char, font=font, anchor="ls")
        assert min(bbox[:2]) >= 0 and max(bbox[2:]) <= 128, (char, bbox)
        draw.text((8, 100), char, font=font, anchor="ls", fill=255)
        outline = np.array(mask.filter(ImageFilter.MaxFilter(9)).resize((32, 32), Image.Resampling.LANCZOS), dtype=np.int32)
        ink = np.array(mask.resize((32, 32), Image.Resampling.LANCZOS), dtype=np.int32)
        desired = np.zeros((32, 32, 4), dtype=np.int32)
        desired[:, :, :3] = (ink[:, :, None] * 128 + 127) // 255
        desired[:, :, 3] = np.maximum(outline, ink)
        # Connected sides share the same pen boundary; overlapping outlines cut the join.
        form = unicodedata.decomposition(char).split()[0]
        if form in ("<initial>", "<medial>"):
            desired[:, :2, :] = 0
        if form in ("<final>", "<medial>"):
            desired[:, advance + 2:, :] = 0
        distance = ((desired[:, :, None, :] - rgba[None, None, :, :]) ** 2).sum(axis=3)
        indices = distance.argmin(axis=2).astype(np.uint8)
        x, y = entry["posX"], entry["posY"]
        assert entry["palette"] == 0 and 0 <= x <= width - 32 and 0 <= y <= height - 32
        pixels[y:y + 32, x:x + 32] = indices
        allowed[y:y + 32, x:x + 32] = True
        entries[entry["index"]]["width"] = advance
        entry["width"] = advance
        glyphs[char] = Image.fromarray(rgba[indices].astype(np.uint8), "RGBA")
    assert np.array_equal(pixels[~allowed], before[~allowed])
    changed_tm2 = original[:start] + pixels.tobytes() + original[start + image_size:]
    assert len(changed_tm2) == len(original)

    result = node(r"""
const fs=require('fs'),assert=require('assert/strict');
const ctd=require('./technical/tools/kh-localization-tool/tools/lib/ddd-ctd');
const font=require('./technical/tools/kh-localization-tool/tools/lib/bbs-font');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
let files={},total=0,changed=0;
for(const rel of new Set(input.rows.map(r=>r.file))){
const original=fs.readFileSync('./technical/extracted_mare/original/'+rel);
const p=ctd.parseDddCtd(original),rep=new Map();
input.rows.forEach((r,i)=>{if(r.file!==rel)return;assert.equal(p.entries[r.index].text,r.english);assert.equal(p.entries[r.index].id,parseInt(r.id,16));assert(!rep.has(r.index));rep.set(r.index,input.mapped[i]);});
const output=ctd.composeDddCtd(p,rep),q=ctd.parseDddCtd(output);
assert.equal(p.entries.length,q.entries.length);assert(p.layouts.equals(q.layouts));
for(let i=0;i<p.entries.length;i++){
 assert.equal(p.entries[i].id,q.entries[i].id);assert.equal(p.entries[i].layout,q.entries[i].layout);
 if(rep.has(i))assert.equal(q.entries[i].text,rep.get(i));else assert.deepEqual(q.entries[i].codes,p.entries[i].codes);
}
assert(ctd.composeDddCtd(q,rep).equals(output));
files[rel]=output.toString('base64');total+=p.entries.length;changed+=rep.size;
}
const cod=font.composeCod(input.entries);assert.deepEqual(font.parseCod(cod),input.entries);
console.log(JSON.stringify({files,cod:cod.toString('base64'),entries:total,unchanged:total-changed}));
""", {"rows": rows, "mapped": mapped, "entries": entries})
    import base64
    cod_bytes = base64.b64decode(result["cod"])
    source_cod = (SOURCE / "font/eventfont.cod").read_bytes()
    allowed_cod = {entry["index"] * 8 + 7 for entry in allocation.values()}
    assert len(cod_bytes) == len(source_cod)
    assert all(a == b or i in allowed_cod for i, (a, b) in enumerate(zip(cod_bytes, source_cod)))
    payloads = {
        **{f"original/{rel}": base64.b64decode(data) for rel, data in result['files'].items()},
        f"original/{FONT_REL}.cod": cod_bytes,
        f"original/{FONT_REL}.tm2": changed_tm2,
    }
    # Movie schedules also embed localized strings. Keep timing, IDs and every
    # other language byte-identical; numeric references keep the ASCII/SJIS XML
    # declaration usable with our existing donor glyph encoding.
    by_message = {int(row['id'], 16): (row, text) for row, text in zip(rows, mapped)}
    inline_ids = set()
    for movie in ['hd000', 'hd003', 'hd004', 'hd803']:
        rel = f'uk/event/en/hd/{movie}/{movie}.exia2'
        source = ROOT / 'technical/extracted_mare/original' / rel
        raw = source.read_bytes()
        end = raw.index(b'</EXUSIA2_XML>') + len(b'</EXUSIA2_XML>')
        xml = raw[:end].decode('utf-8')
        def schedule(match):
            block = match.group()
            if not re.search(r'<PARAM[^>]+Language="LANGUAGE_EN"', block):
                return block
            def data(match):
                ident = int(match['id'], 16)
                if ident not in by_message:
                    return match.group()
                row, text = by_message[ident]
                assert html.unescape(match['text']).replace('\r\n', '\n') == row['english'], (rel, ident)
                inline_ids.add(ident)
                value = ''.join(f'&#x{ord(c):04X};' if ord(c) > 127 else html.escape(c, quote=True) for c in text)
                value = value.replace('\n', '&#10;')
                return match['prefix'] + value + match['suffix']
            return re.sub(r'(?P<prefix><DATA\b[^>]*TextID="(?P<id>[0-9A-Fa-f]+)"[^>]*Text=")(?P<text>.*?)(?P<suffix>"\s*/>)', data, block, flags=re.S)
        updated = re.sub(r'<SCHEDULE_CATEGORY\b[^>]*>.*?</SCHEDULE_CATEGORY>', schedule, xml, flags=re.S)
        # Removing only Text attribute values must produce identical schedules.
        strip = lambda s: re.sub(r' Text=".*?"', ' Text=""', s, flags=re.S)
        assert strip(xml) == strip(updated)
        import xml.etree.ElementTree as ET
        ET.fromstring(updated)
        encoded = updated.encode('utf-8') + b'\r\n'
        encoded += bytes([0xCD]) * (-len(encoded) % 16)
        payloads[f'original/{rel}'] = encoded
    assert inline_ids == set(by_message), ('uncovered movie subtitles', set(by_message) - inline_ids)
    manifest = []
    for rel, data in payloads.items():
        dest = OUTPUT / "payload" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        stage = "font-only" if "/font/" in rel else "dialogue-only"
        staged = OUTPUT / stage / rel
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(data)
        source = ROOT / "technical/extracted_mare" / rel
        manifest.append({"path": rel, "bytes": len(data), "source_sha256": digest(source.read_bytes()), "sha256": digest(data)})

    by_id = {e["id"]: e for e in valid}
    widths = []
    join_peaks = []
    preview = Image.new("RGBA", (1200, 60 + sum(len(v.splitlines()) for v in visual) * 60), (24, 27, 33, 255))
    preview_y = 60
    ImageDraw.Draw(preview).text((24, 16), "OFFLINE ATLAS PREVIEW - IN-GAME DISPLAY UNVERIFIED", fill="white")
    for row_index, (row, line, game_line) in enumerate(zip(rows, visual, mapped)):
        for line, game_line, english_line in zip(line.split("\n"), game_line.split("\n"), row["english"].split("\n")):
            def advance(c):
                return by_id[ord(c)]["width"] if ord(c) in by_id else 16
            ar_width = sum(advance(c) for c in game_line)
            en_width = sum(advance(c) for c in english_line)
            assert ar_width <= max(en_width * 1.3, 160), (row["index"], ar_width, en_width)
            widths.append({"index": row["index"], "english_pixels": en_width, "arabic_pixels": ar_width, "ratio": round(ar_width / en_width, 3)})
            rendered = Image.new("RGBA", (ar_width + 32, 32))
            positions = []
            x = 0
            for char, code in zip(line, game_line):
                positions.append(x)
                if char in glyphs:
                    image = glyphs[char]
                elif ord(code) in by_id:
                    e = by_id[ord(code)]
                    x0, y0 = e["posX"], e["posY"]
                    image = Image.fromarray(rgba[pixels[y0:y0 + 32, x0:x0 + 32]].astype(np.uint8), "RGBA")
                else:
                    image = Image.new("RGBA", (32, 32))
                rendered.alpha_composite(image, (x, 0))
                x += advance(code)
            actual = np.array(rendered, dtype=np.int32)
            visible_ink = actual[:, :, :3].max(axis=2) * actual[:, :, 3] // 255
            for index, (left, right) in enumerate(zip(line, line[1:])):
                left_form = unicodedata.decomposition(left).split(" ")[0]
                right_form = unicodedata.decomposition(right).split(" ")[0]
                if left_form in ("<final>", "<medial>") and right_form in ("<initial>", "<medial>"):
                    boundary = positions[index + 1] + 2
                    peak = int(np.minimum(visible_ink[:, boundary - 1], visible_ink[:, boundary]).max())
                    assert peak >= 0.9 * 128, ("dark seam at Arabic join", row_index, index, peak)
                    join_peaks.append(peak)
            preview.alpha_composite(rendered, ((1200 - ar_width) // 2, preview_y))
            preview_y += 60
    preview.convert("RGB").save(OUTPUT / "preview.png")
    (OUTPUT / "allocation.json").write_text(json.dumps([
        {"form": f"U+{ord(c):04X}", "donor": f"U+{e['id']:04X}", **e} for c, e in allocation.items()
    ], ensure_ascii=False, indent=2), encoding="utf-8")
    report = {"round": "DAYS-DAY7-V020", "tool_commit": subprocess.check_output(["git", "-C", str(TOOL), "rev-parse", "HEAD"], text=True).strip(),
              "roundtrip_original_files": metadata["roundtripPass"], "changed_messages": len(rows),
              "unchanged_messages": result["unchanged"], "arabic_glyphs": len(allocation),
              "font": "Segoe UI Bold 24px", "join_fix": "clip connecting edges at shared pen boundary, preserving terminal outlines",
              "join_checks": len(join_peaks), "minimum_join_ink": min(join_peaks),
              "unmodified_pixels_outside_donor_cells": True,
              "donor_codepoints_unused_in_all_english_ctd": True, "widths": widths,
              "rows": [{**row, "visual": v, "game_text": g} for row, v, g in zip(rows, visual, mapped)],
              "installed": False, "screenshot_verified": False, "files": manifest}
    (OUTPUT / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["roundtrip_original_files", "changed_messages", "unchanged_messages", "arabic_glyphs", "widths"]}))


if __name__ == "__main__":
    build()
