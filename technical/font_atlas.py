"""Plex Medium glyphs in Days' existing cells; retain every other texel."""
import hashlib
import json
from pathlib import Path
import struct
import unicodedata

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / 'font-rtl/fonts/IBMPlexSansArabic-Medium.ttf'
FONT_SHA = 'b60e43e9a2f454f3ef705bb29bb751a9eb915de14898dc0513a2d80d0d3e54f0'
SOURCE = ROOT / 'technical/extracted_mare/original/uk/font'
SS, PX, PEN, BASE = 4, 21, 2, 22


def cod_entries(data, count):
    return [dict(zip(['id', 'x', 'y', 'palette', 'width'], struct.unpack_from('<HHHBB', data, i*8)), index=i) for i in range(count)]


def make_fonts(forms, used_codes, output):
    assert hashlib.sha256(FONT.read_bytes()).hexdigest() == FONT_SHA
    font = ImageFont.truetype(str(FONT), PX*SS, layout_engine=ImageFont.Layout.BASIC)
    metadata = {}
    for name in ['eventfont', 'menufont']:
        inf = (SOURCE / (name+'.inf')).read_bytes()
        count = struct.unpack_from('<H', inf)[0]
        data = (SOURCE / (name+'.cod')).read_bytes()
        metadata[name] = (data, cod_entries(data, count))
    common = set.intersection(*[{e['id'] for e in entries if 0x3040 <= e['id'] < 0x3100 and e['id'] not in used_codes} for _, entries in metadata.values()])
    assert len(forms) <= len(common), (len(forms), len(common))
    allocation = dict(zip(sorted(forms), sorted(common)))
    glyphs, advances = {}, {}
    for char in sorted(forms):
        advance = round(font.getlength(char)/SS)
        assert 0 < advance <= 28, (char, advance)
        mask = Image.new('L', (32*SS, 32*SS))
        draw = ImageDraw.Draw(mask)
        bbox = draw.textbbox((PEN*SS, BASE*SS), char, font=font, anchor='ls')
        assert min(bbox[:2]) >= 0 and max(bbox[2:]) <= 32*SS, (char, bbox)
        draw.text((PEN*SS, BASE*SS), char, font=font, anchor='ls', fill=255)
        form = unicodedata.decomposition(char).split(' ')[0]
        ink = np.array(mask.resize((32,32), Image.Resampling.LANCZOS), dtype=np.int32)
        # Round advances onto the game's integer pen grid. Join strokes occupy
        # rows20..21 for this exact Plex/size/baseline, measured from tatweel.
        for row in range(BASE-2, BASE):
            if form in ('<initial>', '<medial>'):
                peak = int(ink[row, PEN:PEN+4].max())
                assert peak >= 180, (char, 'left join', row, peak)
                ink[row, PEN:PEN+2] = max(peak, 245)
            if form in ('<final>', '<medial>'):
                edge = PEN+advance
                peak = int(ink[row, max(PEN,edge-4):edge+1].max())
                assert peak >= 180, (char, 'right join', row, peak)
                ink[row, edge-1:edge] = max(peak, 245)
        glyphs[char] = ink
        advances[char] = advance
    payloads, reports, previews, widths_by_font = {}, {}, {}, {}
    for name, (original_cod, entries) in metadata.items():
        original = (SOURCE / (name+'.tm2')).read_bytes()
        _, palette_size, image_size, header_size = struct.unpack_from('<IIIH', original,16)
        off = 16+header_size
        assert struct.unpack_from('<HH', original,36) == (2048,2048)
        if palette_size:
            assert image_size == 2048*2048 and palette_size == 1024
            pixels = np.frombuffer(original[off:off+image_size],np.uint8).reshape(2048,2048).copy()
            palette = np.frombuffer(original[off+image_size:off+image_size+palette_size],np.uint8).reshape(256,4)
            order = [(i&~31)|((i&8)<<1)|((i&16)>>1)|(i&7) for i in range(256)]
            rgba = palette[order].astype(np.int32)
        else:
            assert image_size == 2048*2048*4
            pixels = np.frombuffer(original[off:off+image_size],np.uint8).reshape(2048,2048,4).copy()
        before = pixels.copy()
        allowed = np.zeros((2048,2048),bool)
        cod = bytearray(original_cod)
        by_id = {e['id']:e for e in entries}
        rendered = {}
        for char, donor in allocation.items():
            e = by_id[donor]; x,y = e['x'],e['y']; advance = advances[char]
            ink = glyphs[char]; form = unicodedata.decomposition(char).split(' ')[0]
            if palette_size:
                # Half-pixel rim instead of the old one-pixel black rim.
                high = Image.fromarray(ink.astype(np.uint8)).resize((128,128),Image.Resampling.LANCZOS)
                outline = np.array(high.filter(ImageFilter.MaxFilter(5)).resize((32,32),Image.Resampling.LANCZOS),np.int32)
                desired = np.zeros((32,32,4),np.int32)
                desired[:,:,:3] = (ink[:,:,None]*128+127)//255
                desired[:,:,3] = np.maximum(ink,outline)
                if form in ('<initial>','<medial>'):desired[:,:PEN] = 0
                if form in ('<final>','<medial>'):desired[:,PEN+advance:] = 0
                distances = ((desired[:,:,None,:]-rgba[None,None,:,:])**2).sum(axis=3)
                cell = distances.argmin(axis=2).astype(np.uint8)
                visual = rgba[cell].astype(np.uint8)
            else:
                # Native menu texture uses straight RGB128 and alpha0..128.
                cell = np.full((32,32,4),128,np.uint8)
                cell[:,:,3] = ((ink+1)//2).astype(np.uint8)
                if form in ('<initial>','<medial>'):cell[:,:PEN,3] = 0
                if form in ('<final>','<medial>'):cell[:,PEN+advance:,3] = 0
                visual = cell.copy(); visual[:,:,3] = np.minimum(255,visual[:,:,3].astype(np.int32)*2).astype(np.uint8)
            pixels[y:y+32,x:x+32] = cell
            allowed[y:y+32,x:x+32] = True
            cod[e['index']*8+7] = advance
            e['width'] = advance
            rendered[char] = visual
        assert np.array_equal(pixels[~allowed],before[~allowed])
        changed_widths = {by_id[d]['index']*8+7 for d in allocation.values()}
        assert all(a==b or i in changed_widths for i,(a,b) in enumerate(zip(original_cod,cod)))
        joins=[]
        for char,visual in rendered.items():
            form=unicodedata.decomposition(char).split(' ')[0]
            visible = visual[:,:,:3].max(axis=2).astype(np.int32)*visual[:,:,3]//255
            for col,needed in [(PEN,form in ('<initial>','<medial>')),(PEN+advances[char]-1,form in ('<final>','<medial>'))]:
                if needed:
                    peak=int(visible[BASE-2:BASE,col].max());assert peak>=115,(name,char,col,peak);joins.append(peak)
        prefix='original/uk/font/'+name
        payloads[prefix+'.cod']=bytes(cod)
        payloads[prefix+'.tm2']=original[:off]+pixels.tobytes()+original[off+image_size:]
        reports[name]={'forms':len(allocation),'font_sha256':FONT_SHA,'font':'IBM Plex Sans Arabic Medium','pixels':PX,'outline_pixels':0.5 if palette_size else 0,'join_edges_checked':len(joins),'minimum_join_ink':min(joins),'outside_cells_unchanged':True,'original_format_preserved':True}
        widths_by_font[name]={e['id']:e['width'] for e in entries}
        previews[name]=rendered
    output.mkdir(parents=True,exist_ok=True)
    (output/'allocation.json').write_text(json.dumps([{'form':f'U+{ord(c):04X}','donor':f'U+{d:04X}','id':d,'width':advances[c]} for c,d in allocation.items()],indent=2)+'\n',encoding='utf-8')
    (output/'font-report.json').write_text(json.dumps(reports,indent=2)+'\n',encoding='utf-8')
    return payloads,allocation,widths_by_font,previews,reports
