"""Inspect shipped pixels the way a GPU samples them: bilinear, scaled, straight alpha.

The Days engine has not been instrumented, so these are offline checks; user
screenshots remain necessary for runtime approval. Decode the release to compare
first: python technical/decode_release.py 1.0.2 installer/patch
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
import unicodedata

import numpy as np
from PIL import Image, ImageDraw
from build_v030 import visual, TAG
from font_atlas import cod_entries

ROOT = Path(__file__).resolve().parents[1]
CURRENT = '2.0.0'
SCALES = (1.0, 1.5, 2.0, 2.25)
OFFSETS = (0.0, 0.25, 0.5)
SEAM_MINIMUM = 0.8
# Letters that differ only by dots or a hamza; a weak mark reads as a misspelling.
LOOKALIKES = [(0xFE94, 0xFEEA), (0xFE93, 0xFEE9), (0xFEF2, 0xFEF0), (0xFEF1, 0xFEEF), (0xFE84, 0xFE8E), (0xFE83, 0xFE8D), (0xFE88, 0xFE8E), (0xFE87, 0xFE8D),
              (0xFED3, 0xFED7), (0xFED4, 0xFED8), (0xFE91, 0xFE97), (0xFE97, 0xFE9B), (0xFE91, 0xFEE7), (0xFE97, 0xFEE7), (0xFE92, 0xFE98), (0xFE98, 0xFE9C), (0xFE92, 0xFEE8),
              (0xFE9F, 0xFEA3), (0xFEA3, 0xFEA7), (0xFEA0, 0xFEA4), (0xFEA4, 0xFEA8), (0xFEAD, 0xFEAF), (0xFEA9, 0xFEAB), (0xFEB3, 0xFEB7), (0xFEBB, 0xFEBF), (0xFEC3, 0xFEC7), (0xFECB, 0xFECF)]
BACKGROUNDS = {'dark': 0.12, 'bright': 0.9}


def form(char):
    return unicodedata.decomposition(char).split(' ')[0]


def atlas(version, name):
    """Return the texture as straight RGBA in 0..1, with COD entries by id."""
    out = ROOT / f'out/v{version}'
    data = (out / f'payload/original/uk/font/{name}.tm2').read_bytes()
    if version == CURRENT:
        manifest = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
        for ext in ('cod', 'tm2'):
            relative = f'original/uk/font/{name}.{ext}'
            expected = next(item['sha256'] for item in manifest['files'] if item['path'] == relative)
            assert hashlib.sha256((out / 'payload' / relative).read_bytes()).hexdigest() == expected
    _, palette_size, image_size, header = struct.unpack_from('<IIIH', data, 16)
    offset = 16 + header
    if palette_size:
        pixels = np.frombuffer(data[offset:offset+image_size], np.uint8).reshape(2048, 2048)
        palette = np.frombuffer(data[offset+image_size:offset+image_size+palette_size], np.uint8).reshape(256, 4)
        order = [(i & ~31) | ((i & 8) << 1) | ((i & 16) >> 1) | (i & 7) for i in range(256)]
        rgba = palette[order].astype(np.float32)
        rgba[:, :3] = np.minimum(rgba[:, :3]*2, 255)
        texture = rgba[pixels]/255
    else:
        texture = np.frombuffer(data[offset:offset+image_size], np.uint8).reshape(2048, 2048, 4).astype(np.float32)
        texture = np.minimum(texture*2, 255)/255
    count = struct.unpack_from('<H', (ROOT / f'technical/extracted_mare/original/uk/font/{name}.inf').read_bytes())[0]
    entries = {e['id']: e for e in cod_entries((out / f'payload/original/uk/font/{name}.cod').read_bytes(), count)}
    return texture, entries


def sample(texture, entry, u, v):
    """Bilinear lookup at texel coordinates relative to the glyph's COD origin."""
    x, y = entry['x']+u-0.5, entry['y']+v-0.5
    x0, y0 = np.floor(x).astype(np.int32), np.floor(y).astype(np.int32)
    fx, fy = (x-x0)[..., None].astype(np.float32), (y-y0)[..., None].astype(np.float32)
    x1, y1 = np.minimum(x0+1, 2047), np.minimum(y0+1, 2047)
    return (texture[y0, x0]*(1-fx)*(1-fy)+texture[y0, x1]*fx*(1-fy)+texture[y1, x0]*(1-fx)*fy+texture[y1, x1]*fx*fy)


def light(pixels):
    return pixels[..., :3].mean(axis=-1)*pixels[..., 3]


def seam_score(texture, left, right, rows, scale, offset):
    """Weakest stroke brightness across a seam, relative to the strongest nearby."""
    seam = offset+left['width']*scale
    first = int(np.floor(seam-min(2, left['width'])*scale))+1
    last = int(np.ceil(seam+min(2, right['width'])*scale))-1
    columns = np.arange(first, last+1)
    centres = columns+0.5
    y = np.arange(int(np.floor(rows[0]*scale)), int(np.ceil(rows[1]*scale)))
    v = (y+0.5)/scale
    best = np.zeros(columns.size)
    for side, entry, origin in ((centres < seam, left, offset), (centres >= seam, right, seam)):
        if side.any():
            u, w = np.meshgrid((centres[side]-origin)/scale, v)
            best[side] = light(sample(texture, entry, u, w)).max(axis=0)
    return float(best.min()/max(best.max(), 1e-6))


def draw_line(canvas, texture, entries, codes, x, y, scale, whole_cells=False):
    """Draw quads onto a float canvas; pixel centres decide which quad owns a pixel."""
    for code in codes:
        if code not in entries:
            x += 16*scale
            continue
        entry = entries[code]
        end = x+entry['width']*scale
        columns = np.arange(int(np.ceil(x-0.5)), int(np.ceil((x+32*scale if whole_cells else end)-0.5)))
        rows = np.arange(int(np.ceil(y-0.5)), int(np.ceil(y+32*scale-0.5)))
        if columns.size and rows.size:
            u, v = np.meshgrid((columns+0.5-x)/scale, (rows+0.5-y)/scale)
            pixels = sample(texture, entry, u, v)
            region = canvas[rows[0]:rows[-1]+1, columns[0]:columns[-1]+1]
            region[:] = pixels[..., :3]*pixels[..., 3:4]+region*(1-pixels[..., 3:4])
        x = end


def check_font(version, name, pairs, donors, join_rows):
    texture, entries = atlas(version, name)
    glyph = {char: entries[donor] for char, donor in donors.items()}
    if join_rows is None:
        # An older release has no report: find its stroke from the connecting edges.
        edges = [light(texture[e['y']:e['y']+32, e['x']+e['width']-1]) for char, e in glyph.items() if form(char) in ('<final>', '<medial>')]
        strength = np.mean(edges, axis=0)
        rows = np.where(strength >= 0.6*strength.max())[0]
        join_rows = int(rows[0]), int(rows[-1])+1
    seams = {}
    if version == CURRENT:
        # Nothing may show if the engine draws whole cells instead of cropping.
        for char, entry in glyph.items():
            assert texture[entry['y']:entry['y']+32, entry['x']+entry['width']+1:entry['x']+32, 3].max(initial=0) == 0, (name, char, 'ink past the edge repeat')
    # A release built for overlapping cells cannot be scored by cropped seams.
    for scale in SCALES if version == CURRENT else ():
        scores = [(seam_score(texture, glyph[a], glyph[b], join_rows, scale, offset), a, b) for a, b in pairs for offset in OFFSETS]
        weak = [s for s in scores if s[0] < SEAM_MINIMUM]
        worst = min(scores)
        seams[str(scale)] = dict(checked=len(scores), weak=len(weak), worst=round(worst[0], 3), worstPair=[f'U+{ord(worst[1]):04X}', f'U+{ord(worst[2]):04X}'])
    cells = {}
    for char, entry in glyph.items():
        v, u = np.meshgrid(np.arange(32)+0.5, np.arange(entry['width'])+0.5, indexing='ij')
        cells[char] = sample(texture, entry, u, v)
    inked = {char: light(cell).max() for char, cell in cells.items() if cell[..., 3].max() > 0}
    weakest = min(inked, key=inked.get)
    marks = []
    for a, b in LOOKALIKES:
        a, b = chr(a), chr(b)
        if a not in cells or b not in cells:
            continue
        width = max(cells[a].shape[1], cells[b].shape[1])
        contrast = 1.0
        for shade in BACKGROUNDS.values():
            seen = [np.pad(c[..., :3].mean(axis=-1)*c[..., 3]+shade*(1-c[..., 3]), ((0, 0), (0, width-c.shape[1])), constant_values=shade) for c in (cells[a], cells[b])]
            contrast = min(contrast, float(np.abs(seen[0]-seen[1]).max()))
        marks.append(dict(pair=[f'U+{ord(a):04X}', f'U+{ord(b):04X}'], contrast=round(contrast, 3)))
    bright = BACKGROUNDS['bright']
    darkest = {char: float((cell[..., :3].mean(axis=-1)*cell[..., 3]+bright*(1-cell[..., 3])).min()) for char, cell in cells.items() if char in inked}
    return dict(seams=seams, weakestCore=dict(form=f'U+{ord(weakest):04X}', light=round(float(inked[weakest]), 3)),
                weakestMarks=sorted(marks, key=lambda m: m['contrast'])[:5], palestRimOnBright=round(max(darkest.values()), 3)), texture, entries


def main(baseline):
    out = ROOT / f'out/v{CURRENT}'
    rows = []
    for p in sorted((ROOT / f'translation/v{CURRENT}').glob('ct*.json')):
        rows.extend(r for r in json.loads(p.read_text(encoding='utf-8')) if r['arabic'] != r['english'])
    pairs = set()
    for row in rows:
        for part in TAG.split(visual(row['arabic'])):
            if not TAG.fullmatch(part):
                pairs.update((a, b) for a, b in zip(part, part[1:]) if form(a) in ('<final>', '<medial>') and form(b) in ('<initial>', '<medial>'))
    pairs = sorted(pairs)
    fonts = json.loads((out / 'font-report.json').read_text())
    versions = [CURRENT]+([baseline] if baseline and (ROOT / f'out/v{baseline}/payload').is_dir() else [])
    report = dict(version=CURRENT, sampling='bilinear straight-alpha quads, offline', scales=SCALES, offsets=OFFSETS, runtimeVerified=False, distinctAdjacentJoinPairs=len(pairs), fonts={})
    samples = ['هل حفظت ذلك يا روكساس؟', 'أتى إلى المدينة بعد المهمة الأولى.', 'يسرني الإعلان عن اختيار رفيق جديد', 'لماذا تحمر الشمس عند الغروب؟']
    canvas = np.empty((30+len(versions)*len(fonts)*len(samples)*52, 1240, 3), np.float32)
    canvas[:, :620], canvas[:, 620:] = BACKGROUNDS['dark'], BACKGROUNDS['bright']
    y = 30
    labels = []
    for name in fonts:
        report['fonts'][name] = {}
        for version in versions:
            table = {chr(int(e['form'][2:], 16)): e['id'] for e in json.loads((ROOT / f'out/v{version}/allocation.json').read_text())}
            checked = [(a, b) for a, b in pairs if a in table and b in table]
            result, texture, entries = check_font(version, name, checked, table, fonts[name]['join_rows'] if version == CURRENT else None)
            report['fonts'][name][version] = result
            if version == CURRENT:
                assert all(s['weak'] == 0 for s in result['seams'].values()), (name, result['seams'])
            labels.append((y, f'{name} / {version}'))
            for sample_text in samples:
                codes = [table.get(c, ord(c)) for c in visual(sample_text)]
                # 1.0.2 draws ink past COD.width, so show it as overlapping cells.
                for left in (14.25, 634.25):
                    draw_line(canvas, texture, entries, codes, left, y, 1.5, version != CURRENT)
                y += 52
    image = Image.fromarray((np.clip(canvas, 0, 1)*255+0.5).astype(np.uint8))
    draw = ImageDraw.Draw(image)
    draw.text((14, 8), 'BILINEAR QUADS AT 1.5x / OFFLINE, NOT A GAME CAPTURE', fill='white')
    for label_y, label in labels:
        draw.text((14, label_y), label, fill='white')
    image.save(out / 'font-comparison.png')
    (out / 'font-rendering-verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({name: {v: d['seams'] for v, d in versions_.items()} for name, versions_ in report['fonts'].items()}))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '1.0.2')
