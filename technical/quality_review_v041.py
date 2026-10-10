"""Audit final review provenance and account separately for resource keys/art."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'translation/v0.4.1'
NAMES=['ct00100','ctmn000','ctmn200','ctmn300','cthd000','cthd050','cthd100','cthd300','cthd800']


def main():
    reports=[json.loads(p.read_text(encoding='utf-8')) for p in (DIR/'reviews').glob('*.json')]
    files={};keys=[]
    for name in NAMES:
        path=DIR/f'{name}.json';rows=json.loads(path.read_text(encoding='utf-8'))
        canonical=hashlib.sha256(path.read_text(encoding='utf-8').encode()).hexdigest()
        final=[r for r in reports if name in r.get('files',{}) and 'outputCanonicalSha256' in r['files'][name]]
        assert {r['pass'] for r in final}=={1,2}
        for review in final:
            assert review['status']=='complete' and not review.get('unresolved',[])
            item=review['files'][name]
            assert item['reviewedRows']==len(rows) and not item.get('unresolved',[])
            if review['pass']==2:assert item['outputCanonicalSha256']==canonical
        assert len({r['reviewer'] for r in final})>=2
        unchanged_story=name.startswith('cthd')
        if unchanged_story:assert (ROOT/f'translation/v0.4.0/{name}.json').read_bytes()==path.read_bytes()
        technical=[r for r in rows if name=='ct00100' and 491<=r['index']<=585]
        for row in technical:
            assert row['english'].startswith('hd') and row['english']==row['arabic']
            keys.append(dict(id=row['id'],index=row['index'],value=row['english']))
        files[name]={'reviewedRows':len(rows),'translatedRows':len(rows)-len(technical),'canonicalSha256':canonical,'passes':2,'reviewers':sorted({r['reviewer'] for r in final}),'frozenStoryFrom':'0.4.0' if unchanged_story else None}
    assert len(keys)==95 and sum(v['translatedRows'] for v in files.values())==2461
    corrections=[]
    for name,default in [('diary200-pass1.json','ctmn200'),('remaining-pass1.json',None),('diary200-pass2.json','ctmn200')]:
        report=json.loads((DIR/'reviews'/name).read_text(encoding='utf-8'))
        for c in report['corrections']:
            corrections.append(dict(c,file=c.get('file',default)))
    proof={'version':'0.4.1','status':'complete','translatedEntries':2461,'newTranslatedEntries':845,'unchangedReviewedStoryEntries':1616,'legacyInventoryEntries':2556,'technicalResourceKeysPreserved':keys,'files':files,'correctionEvents':len(corrections),'distinctCorrectedNewRows':len({(r['file'],r['id']) for r in corrections}),'corrections':corrections,'inGameVerified':False,'unresolved':[],
           'metric':'100% refers to the 2461 translatable CTD rows in nine Days/shared-menu files. 95 original movie resource keys are preserved, not counted as dialogue. This is not a claim of 100% visual localization.',
           'scopeExclusions':['KH1 story: cthd400','Re:coded story: cthd500, cthd550, cthd600'],
           'sharedContentIncluded':'Chapter labels, launcher prompts and character descriptions stored in the same menu files, including shared Re:coded labels/descriptions; not Re:coded story.',
           'remainingVisualWork':['Decorative English embedded in scene artwork, including WINNER and OPERATIONS CLOSED FOR VACATION; complete art inventory still needed.','Original publisher/brand logos and credits retained.','Human in-game verification of menus, diary layout and all scenes remains pending.']}
    (DIR/'quality-report.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:proof[k] for k in ['translatedEntries','newTranslatedEntries','correctionEvents','distinctCorrectedNewRows']}))


if __name__=='__main__':main()
