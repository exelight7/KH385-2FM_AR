"""Render shipped eventfont cells offline; no game process or file writes."""
import json
from pathlib import Path
import struct
import sys
import re
import numpy as np
from PIL import Image, ImageDraw
from build_v030 import visual
from font_atlas import cod_entries

ROOT=Path(__file__).resolve().parents[1]
version=sys.argv[1] if len(sys.argv)>1 else '0.3.0'
assert re.fullmatch(r'\d+\.\d+\.\d+',version)
OUT=ROOT/f'out/v{version}'
data=(OUT/'payload/original/uk/font/eventfont.tm2').read_bytes()
_,palette_size,image_size,header=struct.unpack_from('<IIIH',data,16)
assert palette_size==1024
off=16+header
pixels=np.frombuffer(data[off:off+image_size],np.uint8).reshape(2048,2048)
palette=np.frombuffer(data[off+image_size:off+image_size+palette_size],np.uint8).reshape(256,4)
order=[(i&~31)|((i&8)<<1)|((i&16)>>1)|(i&7) for i in range(256)]
rgba=palette[order].copy()
rgba[:,:3]=np.minimum(rgba[:,:3].astype(np.int32)*2,255).astype(np.uint8)
count=struct.unpack_from('<H',(ROOT/'technical/extracted_mare/original/uk/font/eventfont.inf').read_bytes())[0]
entries={e['id']:e for e in cod_entries((OUT/'payload/original/uk/font/eventfont.cod').read_bytes(),count)}
donors={chr(int(e['form'][2:],16)):e['id'] for e in json.loads((OUT/'allocation.json').read_text())}
rows={r['id']:r for p in (ROOT/f'translation/v{version}').glob('ct*.json') for r in json.loads(p.read_text(encoding='utf-8'))}
sample=['03918000','03918100','03918200']
lines=[line for ident in sample for line in visual(rows[ident]['arabic']).split('\n')]
canvas=Image.new('RGBA',(620,45+len(lines)*40),(204,204,218,255))
ImageDraw.Draw(canvas).text((10,10),version+' / IBM PLEX SANS ARABIC MEDIUM / OFFLINE ATLAS PREVIEW',fill='black')
for i,line in enumerate(lines):
    codes=[donors.get(c,ord(c)) for c in line]
    # ASCII space is handled by the engine and has no COD cell. Its advance
    # is estimated here; only the glyph cells are exact, not runtime layout.
    width=sum(16 if c==32 else entries[c]['width'] for c in codes)
    assert width<canvas.width-30,(width,line)
    x=(canvas.width-width)//2
    for code in codes:
        if code==32:
            x+=16
            continue
        e=entries[code];cell=rgba[pixels[e['y']:e['y']+32,e['x']:e['x']+e['width']]]
        canvas.alpha_composite(Image.fromarray(cell),(x,40+i*40))
        x+=e['width']
canvas.convert('RGB').resize((canvas.width*2,canvas.height*2),Image.Resampling.NEAREST).save(OUT/'font-preview.png')
