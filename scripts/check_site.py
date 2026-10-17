#!/usr/bin/env python3
"""Validate complete catalogs, preservation, crawlability and generated output."""
from pathlib import Path
from html.parser import HTMLParser
from html import escape
from collections import Counter
from urllib.parse import urlsplit, unquote, quote
import hashlib
import json
import re
import subprocess
import statistics
import tempfile
import xml.etree.ElementTree as ET
from sync_site import ROOT, BASE, PAGES, PAYLOAD, LD, payload, counts
from material_design import EXAMPLES


def digest(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def snapshot(data):
    return {'cats': {c['id']: {
        'record': digest(c),
        'core': digest({k: v for k, v in c.items() if k not in ('pr', 'px')}),
        'products': [digest(p) for p in c.get('pr', [])],
        'px': c.get('px')
    } for c in data['cats']}, 'src': {k: digest(s) for k, s in data['src'].items()}}


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
    checkpoint = json.loads((ROOT/'data/catalog-checkpoint.json').read_text())
    datasets = {}
    for name in PAGES:
        text = (ROOT/name).read_text(); d = payload(text); datasets[name] = d
        assert len(PAYLOAD.findall(text)) == 1, name
        cats = {c['id']:c for c in d['cats']}
        assert len(cats)==len(d['cats']), ('Duplicate category ID',name)
        fields={f['id']:f for f in d['fields']}
        assert len(fields)==len(d['fields']), ('Duplicate field ID',name)
        saved = checkpoint['catalogs'][name]
        # Appending products may change only the product list and its derived price summary.
        # Preserve every old product object, including repeated records, and all category specs.
        for key, expected in saved['cats'].items():
            assert key in cats, ('Catalog record dropped', name, key)
            c = cats[key]
            assert digest({k:v for k,v in c.items() if k not in ('pr','px')}) == expected['core'], ('Catalog specifications changed', name, key)
            assert not Counter(expected['products']) - Counter(digest(p) for p in c.get('pr', [])), ('Existing product changed/dropped', name, key)
            if digest(c) != expected['record']:
                assert name == 'filaments.html', ('Printer changed', key)
                prices = [p['k'] for p in c.get('pr', []) if p.get('k') is not None]
                derived = {'min':min(prices),'max':max(prices),'med':round(statistics.median(prices),2),'n':len(prices)} if prices else None
                assert c.get('px') == derived, ('Stale product price summary', key)
        for key,expected in saved['src'].items():
            assert key in d['src'] and digest(d['src'][key])==expected, ('Original source changed/dropped',name,key)
        # The newer checkpoint must retain every record/source protected by the rollback manifest.
        for key,expected in baseline['catalogs'][name]['cats'].items():
            assert saved['cats'][key]['record'] == expected, ('Rollback checkpoint mismatch', name, key)
        for key,expected in baseline['catalogs'][name]['src'].items():
            assert saved['src'][key] == expected, ('Rollback source checkpoint mismatch', name, key)
        raw_checkpoint = subprocess.run(['git','show',checkpoint['commit']+':'+name],cwd=ROOT,capture_output=True,text=True)
        if raw_checkpoint.returncode == 0:
            assert snapshot(payload(raw_checkpoint.stdout)) == saved, ('Checkpoint differs from Git object', name)
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
                if p.get('retail'):
                    r=p['retail']
                    assert r['store'] and r['location'] and r['status']
                    assert re.fullmatch(r'\d{4}-\d{2}-\d{2}',r['checked'])
                    assert set(r['s']) <= set(p['s']) and r['s'],p
                    assert all(d['src'][sid]['d']==r['checked'] and d['src'][sid]['p']==r['store'] for sid in r['s'])
                    assert r['mass_kg'] > 0
                    assert p['k'] == (round(r['listed_usd']/r['mass_kg'],2) if r['listed_usd'] is not None else None),p
                    assert r['reference_usd'] is None or r['reference_usd'] >= r['listed_usd'],p
                    # Linear print-speed claims must never populate volumetric flow.
                    if 'B7' in p['sp']: assert 'mm³/s' in p['sp']['B7']['v'] or 'mm3/s' in p['sp']['B7']['v'],p
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
    retail=[p for c in filaments['cats'] for p in c['pr'] if p.get('retail')]
    assert {'Inland','Cookiecad','Insignia'} <= {p['b'] for p in retail}
    retail_page=(ROOT/'filaments.html').read_text()
    for brand in {p['b'] for p in retail}:
        assert 'filaments.html?brand='+quote(brand,safe='') in retail_page,brand
    for c in filaments['cats']:
        for p in c['pr']:
            if not p.get('retail'):continue
            guide=(ROOT/'materials'/(c['id']+'.html')).read_text()
            for value in [p['p'],p['pn'],p['nt'],p['u']]:assert escape(value) in guide,(c['id'],'missing product detail',p['p'])
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
    paths=[ROOT/'index.html',*(ROOT/x for x in PAGES),*(ROOT/'materials').glob('*.html'),*(ROOT/'printers').glob('*.html')]
    assert len(list((ROOT/'materials').glob('*.html')))==len(filaments['cats'])+1
    assert len(list((ROOT/'printers').glob('*.html')))==len(printers['cats'])+1
    canonicals=set()
    for path in paths:
        text=path.read_text();name=str(path.relative_to(ROOT)); parsed=Page(text)
        assert 'bytes omitted' not in text and '[... omitted' not in text, name
        assert text.count('https://www.googletagmanager.com/gtag/js?id=G-12FDG0Z8JB')==1,name
        assert text.count("gtag('config', 'G-12FDG0Z8JB')")==1,name
        assert len(re.findall('<title>.*?</title>',text))==1,name
        canonical=[a['href'] for a in parsed.attrs('link') if a.get('rel')=='canonical']
        url=BASE+('' if name=='index.html' else name[:-10] if name.endswith('/index.html') else name)
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
    for directory,data,comparison in [('materials',filaments,'filaments.html'),('printers',printers,'comparison.html')]:
        listing=(ROOT/comparison).read_text()
        itemlist=next(json.loads(x) for x in LD.findall(listing) if json.loads(x).get('@type')=='ItemList')
        assert [x['url'] for x in itemlist['itemListElement']]==[BASE+directory+'/'+c['id']+'.html' for c in data['cats']]
        for c in data['cats']:
            html=(ROOT/directory/(c['id']+'.html')).read_text()
            assert escape(c['n']) in html,c['id']
            assert 'Published value and conditions' in html and 'Sources and dates' in html,c['id']
            assert directory+'/'+c['id']+'.html' in listing,c['id']
            # Every published value and every attached source must survive static rendering.
            for e in c['sp'].values():
                assert escape(e['v']) in html,(directory,c['id'],'missing published value')
                for sid in e.get('s',[]):
                    source=data['src'][sid]
                    if source.get('u'):assert escape(source['u']) in html,(directory,c['id'],sid)
            if directory=='materials':
                parsed=Page(html)
                assert not any(a.get('src','').startswith('../assets/materials/') for a in parsed.attrs('img')),c['id']
                assert 'prints' in parsed.ids,c['id']
                for host in ('www.printables.com/search/models?q=','makerworld.com/en/search/models?keyword=','www.thingiverse.com/search?q='):
                    assert any(a.get('href','').startswith('https://'+host) for a in parsed.attrs('a')),(c['id'],'missing model discovery link')
                if c['id'] in EXAMPLES:
                    e=EXAMPLES[c['id']]
                    assert any(a.get('src')=='../'+e['image'] and a.get('alt')==e['alt'] for a in parsed.attrs('img')),c['id']
                    for key in ('url','license_url','creator','evidence','note','checked'): assert escape(e[key]) in html,(c['id'],'missing photo provenance',key)
                else:assert 'No verified photo example is curated for this exact material yet.' in html,c['id']
                # Disclosure changes visibility, never the complete record or its source links.
                for p in c.get('pr',[]):
                    for key in ('p','pn','nt'): assert escape(p.get(key,'')) in html,(c['id'],'missing product text',key)
                    for e in p.get('sp',{}).values():
                        assert escape(e['v']) in html,(c['id'],'missing product value')
                        for sid in e.get('s',[]):assert escape(data['src'][sid]['u']) in html,(c['id'],'missing product source')
                for a in parsed.attrs('a'):
                    if a.get('href','').startswith('#'):assert a['href'][1:] in parsed.ids,(c['id'],'broken guide anchor',a['href'])
    library=(ROOT/'materials/index.html').read_text()
    assert len(re.findall(r'data-material="[^"]+"',library))==len(filaments['cats'])
    assert set(EXAMPLES)<=set(c['id'] for c in filaments['cats'])
    assert not (ROOT/'assets/materials').exists() or not list((ROOT/'assets/materials').glob('*.svg'))
    for key,e in EXAMPLES.items():
        assert e['image'].startswith('assets/prints/') and '..' not in e['image']
        photo=ROOT/e['image']
        assert hashlib.sha256(photo.read_bytes()).hexdigest()==e['sha256'],(key,'photo bytes changed')
        assert e['width']>0 and e['height']>0 and e['creator'] and e['evidence'] and e['alt']
        assert e['image_url'].startswith('https://media.printables.com/media/prints/')
        assert e['url'].startswith('https://www.printables.com/model/')
        assert e['license_url'].startswith('https://creativecommons.org/')
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2}',e['checked'])
        assert escape(e['url']) in library and escape(e['creator']) in library
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
