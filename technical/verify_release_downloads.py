"""Stream published binaries and verify their hashes and platform headers."""
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
version=json.loads((ROOT/'installer/package.json').read_text(encoding='utf-8'))['version']
release=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
assert release['tag_name']=='v'+version
expected={f'Days-Arabic-Setup-{version}.exe',f'Days-Arabic-Uninstall-{version}.exe',f'Days-Arabic-{version}.AppImage','SHA256SUMS.txt'}
assets={a['name']:a for a in release['assets']}
assert expected==set(assets)
prefix=f'https://github.com/exelight7/KH385-2FM_AR/releases/download/v{version}/'

def response(name):
    assert assets[name]['browser_download_url']==prefix+name
    return urllib.request.urlopen(urllib.request.Request(prefix+name,headers={'User-Agent':'Days-Arabic-Release-Verification'}),timeout=60)

with response('SHA256SUMS.txt') as stream:
    sums={PurePosixPath(line.split(maxsplit=1)[1].lstrip('*')).name:line.split()[0] for line in stream.read().decode().splitlines() if line.strip()}
checks=[]
for name in sorted(expected-{'SHA256SUMS.txt'}):
    digest=hashlib.sha256();count=0;header=b''
    with response(name) as stream:
        while chunk:=stream.read(1024*1024):
            if not header:header=chunk[:4096]
            digest.update(chunk);count+=len(chunk)
    sha=digest.hexdigest()
    assert count==assets[name]['size'] and sha==sums[name],name
    if assets[name].get('digest'):assert assets[name]['digest']=='sha256:'+sha,name
    if name.endswith('.exe'):
        assert header[:2]==b'MZ',name
        offset=int.from_bytes(header[60:64],'little');assert header[offset:offset+4]==b'PE\0\0',name
        kind='Windows PE portable EXE'
    else:
        assert header[:4]==b'\x7fELF' and header[8:11]==b'AI\x02',name
        kind='Linux ELF AppImage type2'
    checks.append({'name':name,'bytes':count,'sha256':sha,'header':kind,'sha256SumsMatch':True,'githubDigestMatch':bool(assets[name].get('digest')),'url':prefix+name})
    print(json.dumps(checks[-1]),flush=True)
proof={'date':datetime.datetime.now(datetime.timezone.utc).isoformat(),'version':version,'release':release['html_url'],'assets':checks,'allDownloadsVerified':True,'executedDownloadedBinaries':False,'inGameVerified':False}
(ROOT/'technical/verification/release-downloads.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
