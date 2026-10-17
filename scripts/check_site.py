#!/usr/bin/env python3
"""Validate complete catalogs, preservation, crawlability and generated output."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import hashlib
import json
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from sync_site import ROOT, BASE, PAGES, PAYLOAD, LD, payload, counts


def digest(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = []; self.ids = []; self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs); self.tags.append((tag, a))
        if 'id' in a: self.ids.append(a['id'])

    def attrs(self, tag):
        return [a for t, a in self.tags if t == tag]


def run():
    baseline = json.loads((ROOT/'data/baseline-integrity.json').read_text())
    datasets = {}
    for name in PAGES:
        text = (ROOT/name).read_text(); d = payload(text); datasets[name] = d
        assert len(PAYLOAD.findall(text)) == 1, name
        cats = {c['id']:c for c in d['cats']}
        assert len(cats)==len(d['cats']), ('Duplicate category ID',name)
        fields={f['id']:f for f in d['fields']}
        assert len(fields)==len(d['fields']), ('Duplicate field ID',name)
        for key,expected in baseline['catalogs'][name]['cats'].items():
            assert key in cats and digest(cats[key])==expected, ('Original catalog record changed/dropped',name,key)
        for key,expected in baseline['catalogs'][name]['src'].items():
            assert key in d['src'] and digest(d['src'][key])==expected, ('Original source changed/dropped',name,key)
        # Check the recorded baseline against real Git objects whenever history is available.
        raw=subprocess.run(['git','show',baseline['baseline']+':'+name],cwd=ROOT,capture_output=True,text=True)
        if raw.returncode==0:
            old=payload(raw.stdout)
            assert {c['id']:digest(c) for c in old['cats']}==baseline['catalogs'][name]['cats'], name
            assert {k:digest(s) for k,s in old['src'].items()}==baseline['catalogs'][name]['src'], name
        def spec(values):
            assert set(values)<=fields.keys(), (name,'unknown field',set(values)-fields.keys())
            for k,e in values.items():
                assert isinstance(e.get('v'),str), (name,k,e)
                assert set(e.get('s',[]))<=d['src'].keys(), (name,k,'unknown source')
                if 'n' in e: assert isinstance(e['n'],(int,float)), (name,k,'invalid numeric value')
        for c in d['cats']:
            assert re.fullmatch('[a-z0-9-]+',c['id']), c['id']
            assert c['f'] in d['families'], c['id']
            spec(c['sp'])
            for p in c.get('pr',[]):
                spec(p.get('sp',{}))
                assert set(p.get('s',[]))<=d['src'].keys(),p
                assert set(p.get('tds') or [])<=d['src'].keys(),p
        cs=counts(d)
        structured=[json.loads(m) for m in LD.findall(text)]
        webpage=next(x for x in structured if x['@type']=='WebPage')
        assert webpage['url']==BASE+name,name
        if name=='comparison.html': assert 'filament' not in webpage['description'].lower(),name
        items=next(x for x in structured if x['@type']=='ItemList')
        assert items['numberOfItems']==len(items['itemListElement'])==cs['items'],name
        assert [x['name'] for x in items['itemListElement']]==[c['n'] for c in d['cats']],name
        ds=next(x for x in structured if x['@type']=='Dataset')
        assert ds['url']==BASE+name and {x['name']:x['value'] for x in ds['additionalProperty']}==cs,name
        assert len(ds['variableMeasured'])==len(fields),name
        static=re.search(r'<noscript>(.*?)</noscript>',text,re.S)[1]
        expected=cs['items']+(cs['products'] if name=='filaments.html' else 0)
        assert static.count('<th scope="row">')==expected,(name,'fallback rows')
        for c in d['cats']: assert c['n'].replace('&','&amp;') in static or c['n'] in static,(name,c['id'])
        print(f'{name}: {cs}; all original records and sources preserved')
    filaments=datasets['filaments.html']; printers=datasets['comparison.html']
    hardness=next(f for f in filaments['fields'] if f['id']=='E10')
    assert hardness['type']=='text' and hardness['mixed'] and not hardness['dir']
    peba=next(c for c in filaments['cats'] if c['id']=='peba')
    assert peba['sp']['B7']['n']==9 and 'mm³/s' in peba['sp']['B7']['v']
    assert 'n' not in peba['sp']['E10']
    assert 'n' not in peba['sp']['E1'] and '>' in peba['sp']['E1']['v']
    assert 'peba' in (ROOT/'materials/peba.html').read_text().lower()
    index=(ROOT/'index.html').read_text()
    summary={'printers':len(printers['cats']),'printer-fields':len(printers['fields']),'materials':len(filaments['cats']),'products':counts(filaments)['products']}
    for key,n in summary.items():
        found=re.findall('data-summary="'+key+r'">(\d+)',index)
        assert found and all(int(x)==n for x in found),(key,found,n)
    paths=[ROOT/'index.html',*(ROOT/x for x in PAGES),*(ROOT/'materials').glob('*.html')]
    assert len(list((ROOT/'materials').glob('*.html')))==len(filaments['cats'])+1
    canonicals=set()
    for path in paths:
        text=path.read_text();name=str(path.relative_to(ROOT)); parsed=Page(text)
        assert 'bytes omitted' not in text and '[... omitted' not in text, name
        assert text.count('https://www.googletagmanager.com/gtag/js?id=G-12FDG0Z8JB')==1,name
        assert text.count("gtag('config', 'G-12FDG0Z8JB')")==1,name
        assert len(re.findall('<title>.*?</title>',text))==1,name
        canonical=[a['href'] for a in parsed.attrs('link') if a.get('rel')=='canonical']
        url=BASE+('' if name=='index.html' else 'materials/' if name=='materials/index.html' else name)
        assert canonical==[url],(name,canonical)
        assert url not in canonicals,('Duplicate canonical',url)
        canonicals.add(url)
        assert any(a.get('name')=='robots' and a.get('content')=='index,follow' for a in parsed.attrs('meta')),name
        assert any(a.get('name')=='description' and a.get('content') for a in parsed.attrs('meta')),name
        assert any(a.get('aria-label')=='Primary' for a in parsed.attrs('nav')),name
        assert len(parsed.ids)==len(set(parsed.ids)),(name,'duplicate HTML IDs')
        for tag,a in parsed.tags:
            for key in ('href','src'):
                href=a.get(key)
                if not href or '${' in href: continue
                u=urlsplit(href)
                if u.scheme and not href.startswith(BASE): continue
                if u.netloc and not href.startswith(BASE): continue
                if href.startswith(BASE): local=ROOT/unquote(u.path[len('/3d_printing_info/'):])
                elif href.startswith('/'): raise AssertionError((name,'root-relative link breaks project Pages',href))
                else: local=path.parent/unquote(u.path)
                if local.is_dir():local=local/'index.html'
                assert local.exists(),(name,href,'missing target')
        for attrs,script in re.findall(r'<script([^>]*)>(.*?)</script>',text,re.S):
            if 'application/json' in attrs or 'ld+json' in attrs: json.loads(script)
            elif script.strip():
                with tempfile.NamedTemporaryFile(mode='w',suffix='.js') as tmp:
                    tmp.write(script);tmp.flush()
                    checked=subprocess.run(['node','--check',tmp.name],capture_output=True,text=True)
                    assert checked.returncode==0,(name,checked.stderr)
    for c in filaments['cats']:
        html=(ROOT/'materials'/ (c['id']+'.html')).read_text()
        assert c['n'].replace('&','&amp;') in html or c['n'] in html,c['id']
        assert 'Published value and conditions' in html and 'Sources and dates' in html,c['id']
        assert 'materials/'+c['id']+'.html' in (ROOT/'filaments.html').read_text(),c['id']
    ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
    urls=[x.text for x in ET.parse(ROOT/'sitemap.xml').findall('s:url/s:loc',ns)]
    assert len(urls)==len(set(urls)) and set(urls)==canonicals,('sitemap/canonical mismatch',set(urls)^canonicals)
    robots=(ROOT/'robots.txt').read_text()
    assert 'Disallow:' not in robots and BASE+'sitemap.xml' in robots
    # Staleness test: sync must be idempotent across all generated pages/metadata.
    files=[*paths,ROOT/'sitemap.xml',ROOT/'assets/materials.css']
    before={p:p.read_bytes() for p in files}
    subprocess.run(['python3',str(ROOT/'scripts/sync_site.py')],check=True,capture_output=True)
    assert all(p.read_bytes()==content for p,content in before.items()),'Generated files out of date: run python scripts/sync_site.py'
    print(f'{len(paths)} pages validated: metadata, links, scripts, GA, sitemap, fallbacks and generated content agree.')

if __name__=='__main__':run()
