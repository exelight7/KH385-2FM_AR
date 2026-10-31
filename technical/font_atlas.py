"""Noto SemiBold glyphs in Days' existing cells; retain every other texel."""
import hashlib
import json
import math
from pathlib import Path
import struct
import unicodedata

from fontTools.ttLib import TTFont
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / 'font-rtl/fonts'
SOURCE = ROOT / 'technical/extracted_mare/original/uk/font'
SS, CELL, BASELINE = 8, 32, 22
# Whether the engine crops a quad to COD.width or draws the whole cell is not
# known: the original eventfont has ink past COD.width, but 1.0.0's joins past it
# looked broken. These cells look the same either way. All ink ends at COD.width,
# and each edge column repeats one texel outwards for the bilinear filter. The
# left repeat falls in an unused neighbouring cell, so no quad ever draws it.
# Thin strokes rarely reach full coverage at this size; lift them a little.
CORE_GAMMA = 0.85
CLIP_ALLOWED = 0.75
NOTO = dict(file='NotoSansArabic-SemiBold.ttf', sha256='c3fba0d014108e86247cf19ea2fd7f28e53b13f0f6180c755a2b4d7da404d18e', name='Noto Sans Arabic SemiBold')
# The engine adds its own shadow to menufont text, as it does for the original
# rimless glyphs; a rim there closes the gaps between dots and letters. At 21px
# no used glyph leaves the 32px cell; 22px clips a glyph's top by 0.6px.
SPECS = {'eventfont': dict(NOTO, pixels=21, rim=0.75), 'menufont': dict(NOTO, pixels=20, rim=0)}
# Noto Sans Arabic has no ( ) / or registered sign.
FALLBACK = dict(file='IBMPlexSansArabic-SemiBold.ttf', sha256='597bd5502e5997be4414e4c9c88834b30ff3784250c84f20bce2b20e53ebd467')


def cod_entries(data, count):
    return [dict(zip(['id', 'x', 'y', 'palette', 'width'], struct.unpack_from('<HHHBB', data, i*8)), index=i) for i in range(count)]


def coverage(mask):
    height, width = mask.shape
    return mask.reshape(height//SS, SS, width//SS, SS).mean(axis=(1, 3))


def dilate(mask, radius):
    out = mask.copy()
    height = mask.shape[0]
    for dy in range(-radius, radius+1):
        run = int(math.sqrt(radius*radius-dy*dy))
        row = np.zeros_like(mask)
        row[max(0, dy):height-max(0, -dy)] = mask[max(0, -dy):height-max(0, dy)]
        counts = np.cumsum(np.pad(row, ((0, 0), (run+1, run))), axis=1, dtype=np.int32)
        out |= counts[:, 2*run+1:] > counts[:, :-(2*run+1)]
    return out


def rasterize(char, font, band, rim):
    """Return ink and alpha coverage, each CELL rows by the glyph's advance."""
    form = unicodedata.decomposition(char).split(' ')[0]
    joins_left, joins_right = form in ('<initial>', '<medial>'), form in ('<final>', '<medial>')
    box = font.getbbox(char, anchor='ls')
    assert BASELINE*SS+box[1] >= 0 and BASELINE*SS+box[3] <= CELL*SS, (char, box)
    origin = 8*SS
    canvas = Image.new('L', ((CELL+16)*SS, CELL*SS))
    ImageDraw.Draw(canvas).text((origin, BASELINE*SS), char, font=font, anchor='ls', fill=255)
    mask = np.array(canvas) > 127
    top, bottom = band
    # The font runs join strokes past the origin and the advance so that glyphs
    # overlap. Counting those as ink stretched words by 2-3px a letter in game.
    rows = np.ones(CELL*SS, bool)
    rows[top-SS//2:bottom+SS//2] = False
    all_columns = np.where(mask.any(axis=0))[0]
    body_columns = np.where(mask[rows].any(axis=0))[0]
    left_columns = body_columns if joins_left else all_columns
    right_columns = body_columns if joins_right else all_columns
    ink_left = (left_columns[0]-origin)/SS if left_columns.size else 0
    ink_right = (right_columns[-1]+1-origin)/SS if right_columns.size else 0
    # Tails may lose a sliver: making room for it would open a gap beside them.
    pen = math.ceil(max(0, -ink_left-CLIP_ALLOWED))
    advance = max(round(font.getlength(char)/SS), math.ceil(ink_right-CLIP_ALLOWED)+pen)
    assert 0 < advance < CELL, (char, advance)
    start = origin-pen*SS
    glyph = mask[:, start:start+advance*SS].copy()
    if joins_left or joins_right:
        stroke = np.where(glyph[top:bottom].any(axis=0))[0]
        assert stroke.size, (char, 'no join stroke')
        if joins_left:
            assert stroke[0] <= (pen+4)*SS, (char, 'left join', stroke[0])
            glyph[top:bottom, :max(SS, stroke[0]+1)] = True
        if joins_right:
            assert advance*SS-stroke[-1] <= 4*SS, (char, 'right join', stroke[-1])
            glyph[top:bottom, min(advance*SS-SS, stroke[-1]):] = True
    ink = coverage(glyph)**CORE_GAMMA
    alpha = np.maximum(ink, coverage(dilate(glyph, round(rim*SS)))) if rim else ink
    return ink, alpha, advance


def free_slots(alpha, entries, count):
    """Find empty atlas cells whose left neighbour is empty too and stays unused."""
    side = alpha.shape[0]//CELL
    used = np.zeros((side, side), bool)
    for e in entries:
        used[e['y']//CELL:(e['y']+CELL-1)//CELL+1, e['x']//CELL:(e['x']+CELL-1)//CELL+1] = True
    empty = alpha.reshape(side, CELL, side, CELL).max(axis=(1, 3)) == 0
    usable = empty & ~used
    slots = []
    for row in range(side):
        col = 1
        while col < side:
            if usable[row, col] and usable[row, col-1]:
                slots.append((col*CELL, row*CELL))
                col += 2
            else:
                col += 1
    assert len(slots) >= count, (len(slots), count)
    return slots[:count]


def make_fonts(forms, used_codes, output):
    metadata = {}
    for name in SPECS:
        inf = (SOURCE / (name+'.inf')).read_bytes()
        count = struct.unpack_from('<H', inf)[0]
        data = (SOURCE / (name+'.cod')).read_bytes()
        metadata[name] = (data, cod_entries(data, count))
    common = set.intersection(*[{e['id'] for e in entries if 0x3040 <= e['id'] < 0x3100 and e['id'] not in used_codes} for _, entries in metadata.values()])
    assert len(forms) <= len(common), (len(forms), len(common))
    allocation = dict(zip(sorted(forms), sorted(common)))
    payloads, reports, previews, widths_by_font, advances_by_font = {}, {}, {}, {}, {}
    for name, (original_cod, entries) in metadata.items():
        spec = SPECS[name]
        path = FONTS / spec['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == spec['sha256']
        font = ImageFont.truetype(str(path), spec['pixels']*SS, layout_engine=ImageFont.Layout.BASIC)
        spare_path = FONTS / FALLBACK['file']
        assert hashlib.sha256(spare_path.read_bytes()).hexdigest() == FALLBACK['sha256']
        spare = ImageFont.truetype(str(spare_path), spec['pixels']*SS, layout_engine=ImageFont.Layout.BASIC)
        cmap, spare_cmap = TTFont(path).getBestCmap(), TTFont(spare_path).getBestCmap()
        assert all(ord(c) in cmap or ord(c) in spare_cmap for c in allocation), (name, 'glyph in neither font')
        stroke = font.getbbox('ـ', anchor='ls')
        band = BASELINE*SS+stroke[1], BASELINE*SS+stroke[3]
        # Rows the join stroke covers completely, where every glyph must meet.
        join_rows = math.ceil(band[0]/SS), band[1]//SS
        assert join_rows[1] > join_rows[0], (name, band)
        original = (SOURCE / (name+'.tm2')).read_bytes()
        _, palette_size, image_size, header_size = struct.unpack_from('<IIIH', original, 16)
        off = 16+header_size
        assert struct.unpack_from('<HH', original, 36) == (2048, 2048)
        if palette_size:
            assert image_size == 2048*2048 and palette_size == 1024
            pixels = np.frombuffer(original[off:off+image_size], np.uint8).reshape(2048, 2048).copy()
            palette = np.frombuffer(original[off+image_size:off+image_size+palette_size], np.uint8).reshape(256, 4)
            order = [(i & ~31) | ((i & 8) << 1) | ((i & 16) >> 1) | (i & 7) for i in range(256)]
            rgba = palette[order].astype(np.float32)
            palette_alpha = rgba[:, 3]
            palette_light = rgba[:, :3]*rgba[:, 3:4]/255
            atlas_alpha = palette_alpha[pixels]
        else:
            assert image_size == 2048*2048*4
            pixels = np.frombuffer(original[off:off+image_size], np.uint8).reshape(2048, 2048, 4).copy()
            atlas_alpha = pixels[:, :, 3]
        slots = dict(zip(allocation, free_slots(atlas_alpha, entries, len(allocation))))
        before = pixels.copy()
        allowed = np.zeros((2048, 2048), bool)
        cod = bytearray(original_cod)
        by_id = {e['id']: e for e in entries}
        rendered, advances, errors = {}, {}, []
        for char, donor in allocation.items():
            e = by_id[donor]
            x, y = slots[char]
            ink, alpha, advance = rasterize(char, font if ord(char) in cmap else spare, band, spec['rim'])
            coverage_ink = np.zeros((CELL, CELL), np.float32)
            coverage_alpha = np.zeros((CELL, CELL), np.float32)
            coverage_ink[:, :advance] = ink
            coverage_alpha[:, :advance] = alpha
            # Straight colour, as the native textures store it: full white is 128.
            colour = np.where(coverage_alpha > 0, 128*coverage_ink/np.maximum(coverage_alpha, 1e-6), 128)
            if palette_size:
                # Judge entries by what they look like over black and over white.
                want_alpha = coverage_alpha*255
                want_light = (colour*coverage_alpha)[:, :, None, None]
                distance = ((palette_light[None, None]-want_light)**2).sum(axis=3)+3*(palette_alpha[None, None]-want_alpha[:, :, None])**2
                cell = distance.argmin(axis=2).astype(np.uint8)
                errors.append(float(np.sqrt(distance.min(axis=2)/4).max()))
                cell[:, advance] = cell[:, advance-1]
                visual = rgba[cell].astype(np.uint8)
            else:
                # Native menu texture uses straight RGB and alpha0..128.
                cell = np.zeros((CELL, CELL, 4), np.uint8)
                cell[:, :, :3] = np.round(colour)[:, :, None].astype(np.uint8)
                cell[:, :, 3] = np.round(coverage_alpha*128).astype(np.uint8)
                cell[:, advance] = cell[:, advance-1]
                visual = cell.copy()
                visual[:, :, 3] = np.minimum(255, visual[:, :, 3].astype(np.int32)*2).astype(np.uint8)
            pixels[y:y+CELL, x:x+CELL] = cell
            pixels[y:y+CELL, x-1] = cell[:, 0]
            allowed[y:y+CELL, x-1:x+CELL] = True
            struct.pack_into('<HH', cod, e['index']*8+2, x, y)
            cod[e['index']*8+7] = advance
            e['x'], e['y'], e['width'] = x, y, advance
            advances[char] = advance
            rendered[char] = visual
        assert np.array_equal(pixels[~allowed], before[~allowed])
        changed_bytes = {by_id[d]['index']*8+k for d in allocation.values() for k in (2, 3, 4, 5, 7)}
        assert all(a == b or i in changed_bytes for i, (a, b) in enumerate(zip(original_cod, cod)))
        joins = []
        for char, visual in rendered.items():
            form = unicodedata.decomposition(char).split(' ')[0]
            visible = visual[:, :, :3].max(axis=2).astype(np.int32)*visual[:, :, 3]//255
            sides = [(0, form in ('<initial>', '<medial>')), (advances[char]-1, form in ('<final>', '<medial>'))]
            for col, needed in sides:
                if needed:
                    peak = int(visible[join_rows[0]:join_rows[1], col].min())
                    assert peak >= 115, (name, char, col, peak)
                    joins.append(peak)
        prefix = 'original/uk/font/'+name
        payloads[prefix+'.cod'] = bytes(cod)
        payloads[prefix+'.tm2'] = original[:off]+pixels.tobytes()+original[off+image_size:]
        reports[name] = {'forms': len(allocation), 'font_sha256': spec['sha256'], 'font': spec['name'], 'pixels': spec['pixels'], 'baseline': BASELINE, 'outline_pixels': spec['rim'], 'join_rows': list(join_rows), 'join_edges_checked': len(joins), 'minimum_join_ink': min(joins), 'maximum_advance': max(advances.values()), 'worst_palette_error': max(errors) if errors else None, 'join_edges_inside_cod_width': True, 'outside_cells_unchanged': True, 'original_format_preserved': True}
        widths_by_font[name] = {e['id']: e['width'] for e in entries}
        advances_by_font[name] = advances
        previews[name] = rendered
    output.mkdir(parents=True, exist_ok=True)
    (output/'allocation.json').write_text(json.dumps([{'form': f'U+{ord(c):04X}', 'donor': f'U+{d:04X}', 'id': d, 'width': {n: a[c] for n, a in advances_by_font.items()}} for c, d in allocation.items()], indent=2)+'\n', encoding='utf-8')
    (output/'font-report.json').write_text(json.dumps(reports, indent=2)+'\n', encoding='utf-8')
    return payloads, allocation, widths_by_font, previews, reports
