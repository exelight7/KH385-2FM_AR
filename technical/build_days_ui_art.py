"""Typeset Arabic labels inside original SP2 UV rectangles; retain L2D geometry."""
import hashlib
import json
from pathlib import Path
import struct

import arabic_reshaper
from bidi.algorithm import get_display
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from inspect_days_art import picture

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'technical/extracted_mare/original'
OUT=ROOT/'out/v0.4.1'
FONT=ROOT/'font-rtl/fonts/IBMPlexSansArabic-Medium.ttf'
LABELS={
    'days_theatre':{2:('DAY','اليوم'),93:("ROXAS’S DIARY",'يوميات روكساس'),
        95:('SECRET REPORTS','التقارير السرية'),97:('DAY','اليوم'),101:('CHAPTERS','الفصول'),107:('NEW!','جديد!'),
        110:('PLAY','تشغيل'),111:('PLAY','تشغيل'),113:('CHAPTERS','الفصول'),114:('CHAPTERS','الفصول'),
        116:('EXTRAS','الإضافات'),117:('EXTRAS','الإضافات'),119:('BACK','رجوع'),120:('BACK','رجوع'),
        122:('Play All','تشغيل الكل'),123:('Play All','تشغيل الكل'),124:('Continue','متابعة'),125:('Continue','متابعة'),
        132:('CHARACTERS','الشخصيات'),133:('CHARACTERS','الشخصيات'),134:("ROXAS’S DIARY",'يوميات روكساس'),
        135:("ROXAS’S DIARY",'يوميات روكساس'),137:('GAME SETTINGS','إعدادات اللعبة')},
    'pause':{4:('PAUSE','إيقاف مؤقت')}
}


def main(out=OUT):
    report=[];previews=[]
    for name,labels in LABELS.items():
        source=SOURCE/f'uk/l2d/{name}.l2d';raw=source.read_bytes();data=bytearray(raw)
        sp=raw.find(b'SP2@');assert sp>=0
        count,table=struct.unpack_from('<II',raw,sp+16)
        tex=raw.find(b'TIM2');image,meta=picture(raw,tex)
        assert meta['kind']==3 and meta['imageBytes']==meta['width']*meta['height']*4
        pos=meta['pixelOffset'];pixels=np.frombuffer(raw[pos:pos+meta['imageBytes']],np.uint8).reshape(meta['height'],meta['width'],4).copy()
        original=pixels.copy();allowed=np.zeros(pixels.shape[:2],bool)
        for ident,(english,arabic) in labels.items():
            assert ident<count
            record=sp+table+ident*24
            uv=struct.unpack_from('<HHHH',raw,record)
            x,y,right,bottom=uv
            assert 0<=x<right<=meta['width'] and 0<=y<bottom<=meta['height']
            cell=original[y:bottom,x:right];w=right-x;h=bottom-y
            solid=cell[cell[:,:,3]>80]
            assert len(solid)>0,(name,ident)
            ink_y,ink_x=np.where(cell[:,:,3]>80)
            native_ink=[int(ink_x.min()),int(ink_y.min()),int(ink_x.max()+1),int(ink_y.max()+1)]
            color=np.median(solid[:,:3],axis=0).round().astype(np.uint8)
            text=get_display(arabic_reshaper.reshape(arabic))
            main_menu=name=='days_theatre' and ident in (110,111,113,114,116,117,119,120)
            secondary=name=='days_theatre' and ident in (122,123,124,125,132,133,134,135)
            header=name=='days_theatre' and ident in (93,95,101,137)
            new_badge=name=='days_theatre' and ident==107
            sizes=[40] if main_menu else [28] if secondary else [26] if header else [24] if new_badge else range(h*2,5,-1)
            for size in sizes:
                font=ImageFont.truetype(str(FONT),size*4,layout_engine=ImageFont.Layout.BASIC)
                box=font.getbbox(text)
                if box[2]-box[0] <= (w-8)*4 and box[3]-box[1] <= (h-4)*4:break
            else:raise AssertionError((name,ident,'label does not fit'))
            mask=Image.new('L',(w*4,h*4));draw=ImageDraw.Draw(mask)
            tx=(w*4-(box[2]-box[0]))//2-box[0];ty=(h*4-(box[3]-box[1]))//2-box[1]
            if main_menu:
                second=ident in (111,114,117,120)
                # Native menu states shift the ink by (+4,+4). Keep that anchor
                # and one Arabic baseline; do not fill the oversized UV slot.
                left,baseline=(84,54) if second else (80,50)
                box=font.getbbox(text,anchor='ls')
                draw.text((left*4-box[0],baseline*4),text,font=font,fill=255,anchor='ls')
            elif secondary or header or new_badge:
                box=font.getbbox(text,anchor='ls')
                baseline=(53 if ident in (123,125,133,135) else 51) if secondary else 38 if header else 24
                right_aligned=secondary or ident in (107,137)
                tx=native_ink[2]*4-box[2] if right_aligned else native_ink[0]*4-box[0]
                draw.text((tx,baseline*4),text,font=font,fill=255,anchor='ls')
            else:
                draw.text((tx,ty),text,font=font,fill=255)
            alpha=np.array(mask.resize((w,h),Image.Resampling.LANCZOS),np.uint16)
            replacement=np.zeros((h,w,4),np.uint8);replacement[:,:,:3]=color
            alpha_max=int(cell[:,:,3].max())
            replacement[:,:,3]=((alpha*alpha_max+127)//255).astype(np.uint8)
            rendered_y,rendered_x=np.where(replacement[:,:,3]>80)
            target_ink=[int(rendered_x.min()),int(rendered_y.min()),int(rendered_x.max()+1),int(rendered_y.max()+1)]
            assert target_ink[3]-target_ink[1]<=native_ink[3]-native_ink[1]+4,(name,ident,native_ink,target_ink)
            pixels[y:bottom,x:right]=replacement;allowed[y:bottom,x:right]=True
            rendered=Image.fromarray(replacement);rendered.putalpha(Image.fromarray(np.minimum(255,replacement[:,:,3].astype(np.uint16)*2).astype(np.uint8)))
            previews.append((english+' / '+arabic,rendered))
            report.append({'path':source.relative_to(SOURCE).as_posix(),'sprite':ident,'sp2RecordOffset':record,'uv':list(uv),
                           'changedRectangle':[x,y,right,bottom],'english':english,'arabic':arabic,'fontPixels':size,'nativeAlphaMaximum':alpha_max,
                           'placement':'native-anchor/common-baseline' if main_menu or secondary or header or new_badge else 'centered-label',
                           'nativeInk':native_ink,'targetInk':target_ink,
                           'sourceSha256':hashlib.sha256(raw).hexdigest()})
        assert np.array_equal(pixels[~allowed],original[~allowed])
        data[pos:pos+meta['imageBytes']]=pixels.tobytes()
        assert len(data)==len(raw) and data[:pos]==raw[:pos] and data[pos+meta['imageBytes']:]==raw[pos+meta['imageBytes']:]
        target=out/f'payload/original/uk/l2d/{name}.l2d';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        for r in report:
            if r['path']==source.relative_to(SOURCE).as_posix():
                r.update(targetSha256=hashlib.sha256(data).hexdigest(),layoutAndOtherTexturesUnchanged=True,outsideLabelsUnchanged=True)
    sheet=Image.new('RGB',(1100,100*len(previews)),(50,50,60));draw=ImageDraw.Draw(sheet)
    for i,(text,image) in enumerate(previews):
        draw.text((8,i*100+2),text.split(' / ')[0],fill='white')
        sheet.paste(image,(220,i*100+10),image)
    sheet.save(out/'ui-art-preview.png')
    (out/'ui-art-report.json').write_text(json.dumps({'labels':report,'count':len(report),'developedByOriginalEnglishPreserved':True,'inGameVerified':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'labels':len(report),'containers':len(LABELS),'geometryUnchanged':True,'outsideLabelsUnchanged':True}))


if __name__=='__main__':main()
