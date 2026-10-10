"""Read native TM2 pictures, including textures embedded in L2D, for auditing."""
import json
from pathlib import Path
import struct

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'technical/extracted_mare/original'
OUT = ROOT / 'out/v0.4.1/art-source'


def picture(data, offset=0):
    assert data[offset:offset+4] == b'TIM2'
    count = struct.unpack_from('<H', data, offset+6)[0]
    assert count == 1
    start = offset+16
    total, palette_size, image_size, header, colors, fmt, mips, clut, kind, w, h = struct.unpack_from('<IIIHHBBBBHH', data, start)
    assert 0 < w <= 4096 and 0 < h <= 4096 and start+total <= len(data)
    pos = start+header
    raw = data[pos:pos+image_size]
    if kind == 3:
        assert image_size >= w*h*4
        rgba = np.frombuffer(raw[:w*h*4], np.uint8).reshape(h,w,4).copy()
    elif kind == 2:
        assert image_size >= w*h*3
        rgb = np.frombuffer(raw[:w*h*3], np.uint8).reshape(h,w,3)
        rgba = np.concatenate([rgb,np.full((h,w,1),128,np.uint8)],axis=2)
    elif kind == 5:
        assert image_size >= w*h and palette_size == colors*4
        palette = np.frombuffer(data[pos+image_size:pos+image_size+palette_size],np.uint8).reshape(colors,4)
        if not clut & 0x80 and colors == 256:
            order = [(i&~31)|((i&8)<<1)|((i&16)>>1)|(i&7) for i in range(256)]
            palette = palette[order]
        rgba = palette[np.frombuffer(raw[:w*h],np.uint8).reshape(h,w)].copy()
    else:
        raise ValueError(('unsupported TM2', kind, w, h))
    rgba[:,:,3] = np.minimum(255,rgba[:,:,3].astype(np.uint16)*2).astype(np.uint8)
    # Most Days assets store full-range RGB; menu fonts are the exception.
    return Image.fromarray(rgba), {'offset':offset,'bytes':16+total,'width':w,'height':h,'kind':kind,'pixelOffset':pos,'imageBytes':image_size,'paletteBytes':palette_size}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    records=[]
    paths=list((SOURCE/'bg/artwork').glob('*x.tm2'))
    paths += [SOURCE/'uk/l2d'/f'{name}.l2d' for name in ['days_theatre','pause','launcher']]
    paths += [SOURCE/'uk/tim2/title/title_days.tm2']
    for path in paths:
        data=path.read_bytes();offset=0;number=0
        while (offset:=data.find(b'TIM2',offset)) >= 0:
            image,info=picture(data,offset)
            name=f'{path.stem}-{number}.png'
            image.save(OUT/name)
            records.append({'source':path.relative_to(SOURCE).as_posix(),'image':name,**info})
            offset += info['bytes'];number+=1
    (OUT/'inventory.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    for group in ['tz','days_theatre','pause','launcher','title_days']:
        selected=[r for r in records if r['image'].startswith(group)]
        for page in range(0,len(selected),24):
            batch=selected[page:page+24]
            sheet=Image.new('RGB',(960,170*((len(batch)+3)//4)),(65,65,65));draw=ImageDraw.Draw(sheet)
            for i,r in enumerate(batch):
                im=Image.open(OUT/r['image']);im.thumbnail((236,145))
                x=(i%4)*240;y=(i//4)*170
                sheet.paste(im,(x,y+20),im)
                draw.text((x+3,y+3),r['image'],fill='white')
            sheet.save(OUT/f'sheet-{group}-{page//24}.png')
    print(json.dumps({'pictures':len(records),'groups':{g:sum(r['image'].startswith(g) for r in records) for g in ['tz','days_theatre','pause','launcher','title_days']}}))


if __name__ == '__main__':
    main()
