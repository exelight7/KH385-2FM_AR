"""Build reviewed story/intro milestone; originals and movies stay read-only."""
import base64
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import string
import xml.etree.ElementTree as ET

import arabic_reshaper
from bidi.algorithm import get_display
import numpy as np
from PIL import Image, ImageDraw
from font_atlas import make_fonts

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'technical/extracted_mare/original'
NAMES = ['cthd000', 'cthd050', 'cthd100', 'cthd300', 'cthd800']
COMPLETE_NAMES = ['ct00100', 'ctmn000', 'ctmn200', 'ctmn300'] + NAMES
COUNTS = dict(ct00100=538,ctmn000=51,ctmn200=232,ctmn300=119,cthd000=319,cthd050=509,cthd100=444,cthd300=46,cthd800=298)
PATHS = dict(ct00100='uk/ctd/ct00100.ctd',ctmn000='uk/ctd/ctmn000.ctd',ctmn200='uk/message/diary/ctmn200.ctd',ctmn300='uk/message/diary/ctmn300.ctd')
TAG = re.compile(r'(\{[^}]+\}|\[(?:BGTRANS|WAIT)[^]]*\])')
digest = lambda b: hashlib.sha256(b).hexdigest()


def node(code, value=None):
    p = subprocess.run(['node','-e',code],cwd=ROOT,input=json.dumps(value,ensure_ascii=True),text=True,encoding='utf-8',capture_output=True,check=True)
    return json.loads(p.stdout)


def visual(text):
    # Narrative image/wait directives remain in their original order; shape only
    # the text between them, including each independent newline paragraph.
    return ''.join(part if TAG.fullmatch(part) else get_display(arabic_reshaper.reshape(part)) for part in TAG.split(text))


def build(require_reviews=True, version='0.3.0'):
    assert re.fullmatch(r'\d+\.\d+\.\d+',version)
    OUT=ROOT/f'out/v{version}'
    complete=tuple(map(int,version.split('.'))) >= (0,4,1)
    names=COMPLETE_NAMES if complete else NAMES
    rows=[];technical_keys=[];review_counts={}
    for name in names:
        translated=json.loads((ROOT/f'translation/v{version}/{name}.json').read_text(encoding='utf-8'))
        assert len(translated)==COUNTS[name]
        review_counts[name]=len(translated)
        for row in translated:
            assert row['file']==PATHS.get(name,f'uk/message/en/event/hd/bin/{name}.ctd')
            if name=='ct00100' and 491<=row['index']<=585:
                assert row['english'].startswith('hd')
                assert row['arabic']==row['english'],row['id']
                technical_keys.append(row)
                continue
            assert row['arabic'].strip() and row['arabic']!=row['english']
            assert row['arabic'].count('\n')==row['english'].count('\n'),row['id']
            assert TAG.findall(row['arabic'])==TAG.findall(row['english']),row['id']
            assert [not line.strip() for line in row['arabic'].split('\n')]==[not line.strip() for line in row['english'].split('\n')],row['id']
            assert not re.search('[\u064b-\u065f\u0640\u200e\u200f]',row['arabic']),row['id']
            rows.append(row)
    assert len(rows)==(2461 if complete else 1616)
    assert len(technical_keys)==(95 if complete else 0)
    if technical_keys:
        node(r"""
const fs=require('fs'),assert=require('assert/strict'),c=require('./technical/tools/kh-localization-tool/tools/lib/ddd-ctd');
const rows=JSON.parse(fs.readFileSync(0,'utf8')),p=c.parseDddCtd(fs.readFileSync('technical/extracted_mare/original/uk/ctd/ct00100.ctd'));
for(const r of rows){assert.equal(p.entries[r.index].text,r.english);assert.equal(p.entries[r.index].id,parseInt(r.id,16));}console.log(JSON.stringify({verified:rows.length}));
""",technical_keys)
    if require_reviews:
        reviews=[json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/f'translation/v{version}/reviews').glob('*.json')]
        for name in names:
            matching=[r for r in reviews if name in r.get('files',{}) and 'pass' in r and 'outputCanonicalSha256' in r['files'][name]]
            assert len(matching)>=2,('missing second review',name)
            assert {r['pass'] for r in matching}=={1,2},('missing independent passes',name)
            assert len({r['reviewer'] for r in matching})>=2,('reviews need distinct reviewers',name)
            for review in matching:
                assert review['status']=='complete' and not review.get('unresolved',[])
                item=review['files'][name]
                assert item['reviewedRows']==review_counts[name]
                assert not item.get('unresolved',[])
                if review['pass']==2:
                    reviewed_hash=item['outputCanonicalSha256']
                    canonical=(ROOT/f'translation/v{version}/{name}.json').read_text(encoding='utf-8').encode('utf-8')
                    assert reviewed_hash==digest(canonical),('changed after final review',name)
    metadata=node(r"""
const fs=require('fs'),path=require('path'),c=require('./technical/tools/kh-localization-tool/tools/lib/ddd-ctd');let used=new Set(),count=0;
function walk(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,e.name);if(e.isDirectory())walk(p);else if(p.endsWith('.ctd')){const b=fs.readFileSync(p),v=c.parseDddCtd(b);if(!c.composeDddCtd(v).equals(b))throw Error(p);count++;if(p.split(path.sep).includes('uk'))for(const r of v.entries)for(const x of r.codes)used.add(x);}}}
walk('technical/extracted_mare/original');walk('technical/extracted/original');console.log(JSON.stringify({used:[...used],count}));
""")
    assert metadata['count']==92
    shaped=[visual(r['arabic']) for r in rows]
    # Arabic lines use Plex punctuation and a Plex-width blank cell, avoiding
    # the original font's heavy dot and oversized interword advance. Original
    # English glyphs/space handling elsewhere remain unchanged.
    forms={c for s in shaped for part in TAG.split(s) if not TAG.fullmatch(part) for c in part if ord(c)>127 or c in string.punctuation+' '}
    payloads,allocation,widths,previews,font_report=make_fonts(forms,set(metadata['used']),OUT)
    def encode(s):
        return ''.join(part if TAG.fullmatch(part) else ''.join(chr(allocation[c]) if c in allocation else c for c in part) for part in TAG.split(s))
    mapped=[encode(s) for s in shaped]
    inverse={chr(value):key for key,value in allocation.items()}
    assert [''.join(inverse.get(c,c) for c in s) for s in mapped]==shaped
    built=node(r"""
const fs=require('fs'),assert=require('assert/strict'),c=require('./technical/tools/kh-localization-tool/tools/lib/ddd-ctd');const x=JSON.parse(fs.readFileSync(0,'utf8'));let files={},unchanged=0;
for(const rel of new Set(x.rows.map(r=>r.file))){const p=c.parseDddCtd(fs.readFileSync('technical/extracted_mare/original/'+rel)),rep=new Map();x.rows.forEach((r,i)=>{if(r.file===rel){assert.equal(p.entries[r.index].text,r.english);assert.equal(p.entries[r.index].id,parseInt(r.id,16));assert(!rep.has(r.index));rep.set(r.index,x.mapped[i]);}});const b=c.composeDddCtd(p,rep),q=c.parseDddCtd(b);assert(c.composeDddCtd(q).equals(b));assert(p.layouts.equals(q.layouts));assert.equal(p.entries.length,q.entries.length);for(let i=0;i<p.entries.length;i++){assert.equal(p.entries[i].id,q.entries[i].id);assert.equal(p.entries[i].layout,q.entries[i].layout);if(rep.has(i))assert.equal(q.entries[i].text,rep.get(i));else{assert.deepEqual(p.entries[i].codes,q.entries[i].codes);unchanged++;}}files['original/'+rel]=b.toString('base64');}console.log(JSON.stringify({files,unchanged}));
""",{'rows':rows,'mapped':mapped})
    payloads.update({rel:base64.b64decode(data) for rel,data in built['files'].items()})
    ui_art=None
    if complete:
        from build_days_ui_art import main as build_ui
        build_ui(OUT)
        ui_art=json.loads((OUT/'ui-art-report.json').read_text(encoding='utf-8'))
        for rel in sorted({r['path'] for r in ui_art['labels']}):
            payloads['original/'+rel]=(OUT/'payload/original'/rel).read_bytes()
    by_id={int(row['id'],16):(row,text) for row,text in zip(rows,mapped)}
    assert len(by_id)==len(rows)
    xml_ids=set();xml_report=[];xml_source_mismatches=[]
    for source in sorted((SOURCE/'uk/event/en/hd').glob('*/*.exia2')):
        raw=source.read_bytes();end=raw.index(b'</EXUSIA2_XML>')+len(b'</EXUSIA2_XML>')
        try:
            xml=raw[:end].decode('utf-8');encoding='utf-8'
        except UnicodeDecodeError:
            xml=raw[:end].decode('cp932');encoding='cp932'
        assert xml.encode(encoding)==raw[:end]
        changed=set()
        def category(match):
            block=match.group()
            if not re.search(r'<PARAM[^>]+Language="LANGUAGE_EN"',block):return block
            def data(match):
                ident=int(match['id'],16)
                if ident not in by_id:return match.group()
                row,text=by_id[ident]
                if html.unescape(match['text']).replace('\r\n','\n')!=row['english']:xml_source_mismatches.append({'path':source.relative_to(SOURCE).as_posix(),'id':row['id']})
                xml_ids.add(ident);changed.add(ident)
                value=''.join(f'&#x{ord(c):04X};' if ord(c)>127 else html.escape(c,quote=True) for c in text).replace('\n','&#10;')
                return match['prefix']+value+match['suffix']
            return re.sub(r'(?P<prefix><DATA\b[^>]*?TextID="(?P<id>[0-9A-Fa-f]+)"[^>]*?Text=")(?P<text>[^"]*)(?P<suffix>")',data,block,flags=re.S)
        updated=re.sub(r'<SCHEDULE_CATEGORY\b[^>]*>.*?</SCHEDULE_CATEGORY>',category,xml,flags=re.S)
        if not changed:continue
        strip=lambda s:re.sub(r' Text=".*?"',' Text=""',s,flags=re.S)
        if strip(xml)!=strip(updated):
            import difflib
            raise AssertionError((str(source),list(difflib.unified_diff(strip(xml).splitlines(),strip(updated).splitlines()))[:20]))
        ET.fromstring(updated)
        old_categories=re.findall(r'<SCHEDULE_CATEGORY\b[^>]*>.*?</SCHEDULE_CATEGORY>',xml,re.S)
        new_categories=re.findall(r'<SCHEDULE_CATEGORY\b[^>]*>.*?</SCHEDULE_CATEGORY>',updated,re.S)
        for old,new in zip(old_categories,new_categories):
            if not re.search(r'<PARAM[^>]+Language="LANGUAGE_EN"',old):assert old==new
        encoded=updated.encode(encoding)+b'\r\n';encoded+=bytes([0xCD])*(-len(encoded)%16)
        rel='original/'+source.relative_to(SOURCE).as_posix();payloads[rel]=encoded
        xml_report.append({'path':rel,'rows':len(changed),'encoding':encoding,'timing_and_other_languages_unchanged':True})
    files=[]
    for rel,data in payloads.items():
        dest=OUT/'payload'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        files.append({'path':rel,'bytes':len(data),'source_sha256':digest((SOURCE/rel.removeprefix('original/')).read_bytes()),'sha256':digest(data)})
    width_report=[]
    for row,encoded in zip(rows,mapped):
        name='menufont' if row['file'].endswith('cthd300.ctd') or '/ctmn' in row['file'] or row['file'].endswith('ct00100.ctd') else 'eventfont'
        def width(s):return sum(widths[name].get(ord(c),16) for part in TAG.split(s) if not TAG.fullmatch(part) for c in part)
        source_max=max(width(line) for line in row['english'].split('\n'))
        target_max=max(width(line) for line in encoded.split('\n'))
        width_report.append({'file':row['file'],'index':row['index'],'id':row['id'],'source_max':source_max,'arabic_max':target_max,'warn':target_max>max(160,source_max*1.3)})
    total=2461 if complete else 2556
    report={'version':version,'changed_messages':len(rows),'unchanged_messages':built['unchanged'],'totalVisibleEntries':total,'translatedPercent':round(100*len(rows)/total,3),'legacyInventoryEntries':2556,'technicalResourceKeysPreserved':[{'id':r['id'],'index':r['index'],'value':r['english']} for r in technical_keys],'uiArt':ui_art,'roundtrip_original_files':92,'font':font_report,'files':files,'xml_files':xml_report,'xml_rows':len(xml_ids),'xml_source_mismatches':xml_source_mismatches,'widths':width_report,'installed':False,'in_game_verified':False,'review_gate_enforced':require_reviews}
    (OUT/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'translated':len(rows),'percent':report['translatedPercent'],'files':len(files),'xml_rows':len(xml_ids),'xml_source_mismatches':len(xml_source_mismatches),'width_warnings':sum(r['warn'] for r in width_report)}))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--version',default='0.3.0')
    parser.add_argument('--draft-check',action='store_true')
    args=parser.parse_args()
    build(require_reviews=not args.draft_check,version=args.version)
