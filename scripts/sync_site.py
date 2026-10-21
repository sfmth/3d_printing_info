#!/usr/bin/env python3
"""Generate summaries, crawlable material guides and sitemap from complete embedded catalogs.

The two #payload JSON blocks remain the sole catalog source of truth.
No network or third-party dependencies. Never consumes console excerpts.
"""
from pathlib import Path
from html import escape
from urllib.parse import quote
import json
import re
from material_design import detail_body, directory_body
from material_articles import generate_articles, load_articles
from printer_design import detail_body as printer_detail_body, write_diagrams
from printer_resources import load_resources, source_urls
from printer_library import directory_body as printer_directory_body

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://sfmth.github.io/3d_printing_info/'
DATE = '2026-10-18'  # Content revision date, not a blanket source/price check date.
PRINTER_DATE = '2026-10-20'  # Printer presentation only; catalog/source dates are unchanged.
PAGES = ('comparison.html', 'filaments.html')
PAYLOAD = re.compile(r'<script[^>]*id="payload"[^>]*>(.*?)</script>', re.S)
LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
E = lambda value: escape(str(value), quote=True)


def payload(page):
    match = PAYLOAD.search(page)
    if not match:
        raise ValueError('Missing complete #payload block')
    return json.loads(match[1])


def jd(value):
    return json.dumps(value, ensure_ascii=False).replace('<', '\\u003c')


def ld(value):
    return '<script type="application/ld+json">' + jd(value) + '</script>'


def marker(page, key, content):
    start, end = '<!-- generated:' + key + ' -->', '<!-- /generated:' + key + ' -->'
    block = start + '\n' + content + '\n' + end
    pattern = re.escape(start) + r'.*?' + re.escape(end)
    if start in page:
        return re.sub(pattern, lambda _: block, page, flags=re.S)
    return page.replace('</main>', block + '\n</main>', 1)


def counts(data):
    return {'items': len(data['cats']), 'fields': len(data['fields']),
            'products': sum(len(c.get('pr', [])) for c in data['cats']),
            'brands': len({(p['b'] if p else c.get('brand', '')).lower()
                           for c in data['cats'] for p in (c.get('pr') or [None])
                           if (p and p.get('b')) or c.get('brand')})}


def retail_links(data):
    groups = {}
    for c in data['cats']:
        for p in c.get('pr', []):
            if p.get('retail'):
                groups.setdefault(p['b'], []).append(p)
    total = sum(map(len, groups.values()))
    body = '<details class="material-directory" id="retail-brands"><summary>Filament in US stores · '+str(total)+' sourced listings</summary><p>Selected product lines with dated store-stock or pickup listings. Check the retailer for current local stock and prices. Each product retains its own source, spool mass and price notes.</p><ul>'
    for brand, products in sorted(groups.items()):
        stores = ', '.join(sorted({p['retail']['store'] for p in products}))
        dates = ', '.join(sorted({p['retail']['checked'] for p in products}))
        body += '<li><a href="filaments.html?brand='+quote(brand,safe='')+'">'+E(brand)+'</a> · '+E(stores)+' · '+str(len(products))+' product lines · checked '+E(dates)+' · <a href="'+E(products[0]['u'])+'">retailer example</a></li>'
    return body+'</ul></details>'


def refs(data, ids):
    result = []
    for sid in dict.fromkeys(ids):
        s = data['src'][sid]
        label = E(s.get('t', sid))
        if s.get('u'):
            label = '<a href="' + E(s['u']) + '">' + label + '</a>'
        result.append(label + (' · ' + E(s['d']) if s.get('d') else '') +
                      (' · ' + E(s['k']) if s.get('k') else ''))
    return '<ul>' + ''.join('<li>' + x + '</li>' for x in result) + '</ul>' if result else '—'


def value(cat, fid):
    return cat.get('sp', {}).get(fid, {}).get('v', '—')


def fallback(data, printer):
    cs = counts(data)
    headers = (['Printer', 'Class', 'Street price (USD; dated snapshot)', 'Build volume (catalog dimensions)',
                'FDM print speed (mm/s; claimed)', 'Resin vertical speed (mm/h; claimed)',
                'Hotend / temperature notes (catalog text)', 'Sources'] if printer else
               ['Material guide', 'Family', 'Median listing price (USD/kg)', 'XY tensile strength (MPa)',
                'HDT at 1.8 MPa (°C)', 'Abrasiveness', 'Moisture uptake', 'Sources'])
    rows = []
    for c in data['cats']:
        keys = ['A4', 'B1', 'D1', 'W4', 'H2'] if printer else ['E1', 'F2', 'C2', 'D1']
        label = '<a href="' + ('printers/' if printer else 'materials/') + E(c['id']) + '.html">' + E(c['n']) + '</a>'
        vals = ([c['f'], *[value(c, k) for k in keys]] if printer else
                [c['f'], (c.get('px') or {}).get('med', '—'), *[value(c, k) for k in keys]])
        ids = [sid for k in keys for sid in c['sp'].get(k, {}).get('s', [])]
        rows.append('<tr><th scope="row">' + label + '</th>' + ''.join('<td>' + E(v) + '</td>' for v in vals) + '<td>' + refs(data, ids) + '</td></tr>')
    label = '3D printers' if printer else 'filament materials'
    table = '<table><caption>' + E(label) + ' — summary</caption><thead><tr>' + ''.join('<th scope="col">' + E(h) + '</th>' for h in headers) + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
    if not printer:
        rows = []
        for c in data['cats']:
            for p in c.get('pr', []):
                title = E(p['b'] + ' ' + p['p'])
                if p.get('u'): title = '<a href="' + E(p['u']) + '">' + title + '</a>'
                rows.append('<tr><th scope="row">' + title + '</th><td><a href="materials/' + E(c['id']) + '.html">' + E(c['n']) + '</a></td><td>' + E(p.get('k') if p.get('k') is not None else '—') + '</td><td>' + E(p.get('pn', '—')) + '</td></tr>')
        table += '<table id="static-products"><caption>All ' + str(cs['products']) + ' filament products — dated listing prices</caption><thead><tr><th scope="col">Product</th><th scope="col">Material</th><th scope="col">USD/kg</th><th scope="col">Price type, date and conditions</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
    return '<noscript><section id="static"><h2>All ' + str(cs['items']) + ' ' + label + '</h2><p>Sorting, filtering and comparison need JavaScript. These summaries and all printer and material guides remain available without it. Unknown fields are —. Prices and source dates are individual snapshots; manufacturer claims retain their conditions.</p>' + table + '</section></noscript>'


def guide_page(name, desc, path, content, analytics, styles, schema):
    url = BASE + (path[:-10] if path.endswith('/index.html') else path)
    depth = '../' if '/' in path else ''
    head = '<!doctype html>\n<html lang="en" data-theme="auto"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    head += '<title>' + E(name) + ' | 3D Printing Info</title><meta name="description" content="' + E(desc) + '"><meta name="robots" content="index,follow"><link rel="canonical" href="' + url + '">'
    for key, val in {'og:title': name, 'og:description': desc, 'og:url': url, 'og:type': 'article' if path.endswith('.html') else 'website', 'og:image': BASE+'assets/og-card.png', 'og:site_name': '3D Printing Info'}.items():
        head += '<meta property="' + key + '" content="' + E(val) + '">'
    head += '<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="'+E(name)+'"><meta name="twitter:description" content="'+E(desc)+'"><meta name="twitter:image" content="'+BASE+'assets/og-card.png">'
    if path.startswith('materials/'):
        head += '<link rel="stylesheet" href="'+depth+'assets/material-guides.css">'
        if path.endswith('/index.html'): head += '<script defer src="'+depth+'assets/material-guides.js"></script>'
    article = path.startswith('articles/')
    body_class = 'article-page' if article else 'material-page '+('material-library' if path.endswith('/index.html') else 'material-detail') if path.startswith('materials/') else 'printer-page '+('printer-library-page' if path.endswith('/index.html') else 'printer-detail') if path.startswith('printers/') else ''
    head += '<link rel="icon" href="' + depth + 'assets/site-icon.svg"><link rel="stylesheet" href="' + depth + 'assets/materials.css">'
    if article: head += '<link rel="stylesheet" href="'+depth+'assets/material-articles.css">'
    if path.startswith('printers/'):
        head += '<link rel="stylesheet" href="'+depth+'assets/printer-guides.css">'
        if path.endswith('/index.html'):
            head += '<link rel="stylesheet" href="'+depth+'assets/printer-library.css"><script defer src="'+depth+'assets/printer-library.js"></script>'
    head += analytics + ld(schema) + '</head><body'+(' class="'+body_class+'"' if body_class else '')+'><div class="wrap">'
    nav = '<nav class="nav" aria-label="Primary"><a href="' + depth + '">Home</a><a href="' + depth + 'comparison.html">Printers</a><a href="' + depth + 'filaments.html">Filaments</a><a href="' + depth + 'printers/">Printer guides</a><a href="./" aria-current="'+('page' if path.endswith('index.html') else 'true')+'">Material guides</a></nav>'
    if path.startswith('printers/'):
        nav = '<nav class="nav" aria-label="Primary"><a href="../">Home</a><a href="../comparison.html">Printers</a><a href="../filaments.html">Filaments</a><a href="./" aria-current="'+('page' if path.endswith('index.html') else 'true')+'">Printer guides</a><a href="../materials/">Material guides</a></nav>'
    if article:
        nav = '<nav class="nav" aria-label="Primary"><a href="../">Home</a><a href="../comparison.html">Printers</a><a href="../filaments.html">Filaments</a><a href="../materials/">Material guides</a><a href="./" aria-current="'+('page' if path.endswith('index.html') else 'true')+'">Selection articles</a></nav>'
    return head + '<div class="topbar"><a class="brand" href="' + depth + '"><img src="' + depth + 'assets/site-icon.svg" alt="">3D Printing Info</a>' + nav + '</div><main>' + content + '</main><footer><span>Catalog values retain their original source dates. Page revision: ' + (PRINTER_DATE if path.startswith('printers/') else DATE) + '.</span><a href="' + depth + 'sitemap.xml">Sitemap</a></footer></div></body></html>\n'


def generate_materials(data, index):
    styles = re.search(r'<style>(.*?)</style>', index, re.S)[1]
    styles += '\nheader { display:block; } h1 { font-size:clamp(1.8rem,5vw,3rem); line-height:1.08; } h2 { margin-top:28px; } .facts { display:grid; gap:12px; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); } .fact { border:1px solid var(--grid); border-radius:8px; background:var(--surface); padding:16px; } .fact h3 { margin:0 0 6px; font-size:1rem; } .fact p { margin:0; } .source-note, .price-note { color:var(--ink-2); font-size:13px; } .table-scroll { overflow:auto; } table { width:100%; border-collapse:collapse; margin-top:12px; font-size:13px; } td,th { border:1px solid var(--grid); padding:10px; vertical-align:top; text-align:left; } th { background:var(--surface); } td ul { margin:0; padding-left:18px; } .directory { columns:3 230px; } .directory li { padding:5px; break-inside:avoid; } details { border:1px solid var(--grid); border-radius:8px; padding:14px; margin-top:16px; } summary { cursor:pointer; font-weight:600; } .breadcrumbs { font-size:13px; color:var(--ink-2); margin-bottom:16px; } p { max-width:88ch; } .topbar { margin-bottom:32px; }\n'
    (ROOT/'assets/materials.css').write_text(styles)
    analytics = re.search(r'<!-- Google tag.*?</script>\s*<script>.*?</script>', index, re.S)[0]
    paths = []
    for c in data['cats']:
        path = 'materials/' + c['id'] + '.html'; paths.append(path)
        desc = c['n'] + ': print settings, mechanical and thermal properties, product listings and dated sources. ' + c.get('sum','')
        body = detail_body(data,c,refs,value)
        schema = {'@context':'https://schema.org','@type':'WebPage','name':c['n']+' material guide','url':BASE+path,'description':desc,'isPartOf':{'@type':'WebSite','url':BASE,'name':'3D Printing Info'},'mainEntity':{'@type':'TechArticle','headline':c['n']+' — printing, properties and sources','about':c['n'],'description':c.get('sum',''),'url':BASE+path,'citation':[s['u'] for k,s in data['src'].items() if s.get('u') and k in {sid for e in c['sp'].values() for sid in e.get('s',[])}]}}
        (ROOT/path).write_text(guide_page(c['n']+' filament guide',desc,path,body,analytics,styles,schema))
    body = directory_body(data)
    path='materials/index.html'
    (ROOT/path).write_text(guide_page('3D printing material guides','Browse '+str(len(data['cats']))+' source-backed filament material guides with printing parameters, mechanical properties and product listings.',path,body,analytics,styles,{'@context':'https://schema.org','@type':'CollectionPage','name':'3D printing material guides','url':BASE+'materials/','mainEntity':{'@type':'ItemList','numberOfItems':len(data['cats']),'itemListElement':[{'@type':'ListItem','position':i,'name':c['n'],'url':BASE+'materials/'+c['id']+'.html'} for i,c in enumerate(data['cats'],1)]}}))
    expected={Path(x).name for x in paths}|{'index.html'}
    for existing in (ROOT/'materials').glob('*.html'):
        if existing.name not in expected: raise ValueError('Unexpected material page: '+str(existing))
    return paths


def generate_printers(data, index):
    """Render every printer's complete sourced record without a JavaScript dependency."""
    folder=ROOT/'printers'; folder.mkdir(exist_ok=True)
    write_diagrams()
    analytics=re.search(r'<!-- Google tag.*?</script>\s*<script>.*?</script>',index,re.S)[0]
    paths=[]
    resources=load_resources(expected_ids={c['id'] for c in data['cats']})
    for c in data['cats']:
        path='printers/'+c['id']+'.html'; paths.append(path)
        desc=c['n']+': hardware, firmware options, modifications, troubleshooting and sourced specifications. '+c.get('sum','')
        body=printer_detail_body(data,c,refs)
        used={sid for e in c['sp'].values() for sid in e.get('s',[])}
        # These are technical reference articles with historical price snapshots,
        # not offer/review records eligible for Google's Product rich results.
        subject={'@type':'Thing','name':c['n'],'description':c.get('brand','')+' '+c['f']+' 3D printer'}
        schema={'@context':'https://schema.org','@type':'WebPage','name':c['n']+' printer guide','url':BASE+path,'description':desc,'isPartOf':{'@type':'WebSite','url':BASE,'name':'3D Printing Info'},'mainEntity':{'@type':'TechArticle','headline':c['n']+' — hardware, firmware, modifications and troubleshooting','about':subject,'description':c.get('sum',''),'url':BASE+path,'citation':list(dict.fromkeys([s['u'] for k,s in data['src'].items() if s.get('u') and k in used]+source_urls(resources[c['id']])))}}
        (ROOT/path).write_text(guide_page(c['n']+' printer guide',desc,path,body,analytics,'',schema))
    body=printer_directory_body(data)
    schema={'@context':'https://schema.org','@type':'CollectionPage','name':'3D printer guides','url':BASE+'printers/','mainEntity':{'@type':'ItemList','numberOfItems':len(data['cats']),'itemListElement':[{'@type':'ListItem','position':i,'name':c['n'],'url':BASE+'printers/'+c['id']+'.html'} for i,c in enumerate(data['cats'],1)]}}
    (folder/'index.html').write_text(guide_page('3D printer guides','Browse '+str(len(data['cats']))+' sourced printer guides with hardware, firmware, dated prices and test notes.','printers/index.html',body,analytics,'',schema))
    expected={Path(x).name for x in paths}|{'index.html'}
    for existing in folder.glob('*.html'):
        if existing.name not in expected:raise ValueError('Unexpected printer page: '+str(existing))
    return paths


def sync():
    datasets = {name:payload((ROOT/name).read_text()) for name in PAGES}
    for filename,data in datasets.items():
        printer = filename=='comparison.html'; cs=counts(data); path=ROOT/filename; page=path.read_text()
        desc = (f"Compare {cs['items']} FDM and resin 3D printers across {cs['brands']} brands and {cs['fields']} fields, with hardware specifications, dated prices and source notes." if printer else f"Compare {cs['items']} filament materials and {cs['products']} products across {cs['brands']} brands, with printing parameters, properties, dated prices and sources.")
        title = '3D Printer Comparison' if printer else '3D Printing Filament Comparison'
        page=re.sub(r'<title>.*?</title>','<title>'+title+' | 3D Printing Info</title>',page,count=1)
        for attr in ['name="description"','property="og:description"','name="twitter:description"']:
            page=re.sub('<meta '+attr+r' content="[^"]*">',lambda _: '<meta '+attr+' content="'+E(desc)+'">',page)
        for attr in ['property="og:title"','name="twitter:title"']:
            page=re.sub('<meta '+attr+r' content="[^"]*">',lambda _: '<meta '+attr+' content="'+E(title)+'">',page)
        def refresh(m):
            x=json.loads(m[1]);typ=x.get('@type')
            if typ=='WebPage':
                x.update(name=title,url=BASE+filename,description=desc,about=['3D printers','FDM','MSLA','printer specifications'] if printer else ['3D printing filament','material properties','printing parameters'])
            elif typ=='ItemList':
                x.update(name='3D printers' if printer else '3D printing filament materials',numberOfItems=cs['items'],url=BASE+filename,itemListElement=[{'@type':'ListItem','position':i,'name':c['n'],'url':BASE+('printers/' if printer else 'materials/')+c['id']+'.html'} for i,c in enumerate(data['cats'],1)])
            elif typ=='Dataset':
                x.update(description=desc,url=BASE+filename,variableMeasured=[f['name']+((' ('+f['unit']+')') if f.get('unit') else '') for f in data['fields']])
                # Catalog row counts are explicit machine-readable properties.
                x['additionalProperty']=[{'@type':'PropertyValue','name':k,'value':v} for k,v in cs.items()]
            return ld(x)
        page=LD.sub(refresh,page)
        page=re.sub(r'<noscript>.*?</noscript>',lambda _:fallback(data,printer),page,flags=re.S)
        directory='printers' if printer else 'materials'
        label='printer' if printer else 'material'
        content='<details class="material-directory"><summary>Browse all '+str(cs['items'])+' '+label+' guides</summary><ul>'+''.join('<li><a href="'+directory+'/'+E(c['id'])+'.html">'+E(c['n'])+'</a></li>' for c in data['cats'])+'</ul></details>'
        page=marker(page,label+'-links',content)
        if not printer: page=marker(page,'retail-brands',retail_links(data))
        path.write_text(page)
    summary={'printers':len(datasets[PAGES[0]]['cats']),'printer-fields':len(datasets[PAGES[0]]['fields']),'materials':len(datasets[PAGES[1]]['cats']),'products':counts(datasets[PAGES[1]])['products']}
    path=ROOT/'index.html';index=path.read_text()
    for key,n in summary.items(): index=re.sub(r'(data-summary="'+key+r'">)\d+',lambda m:m[1]+str(n),index)
    path.write_text(index)
    material_paths=generate_materials(datasets[PAGES[1]],index)
    printer_paths=generate_printers(datasets[PAGES[0]],index)
    article_paths=generate_articles(BASE,index,guide_page,{c['id'] for c in datasets[PAGES[1]]['cats']})
    urls=['','comparison.html','filaments.html','materials/','printers/',*material_paths,*printer_paths,*article_paths]
    article_dates={'articles/'+a['id']+'.html':a['modified'] for a in load_articles()['articles']}
    article_dates['articles/']=max(article_dates.values())
    sitemap='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join('  <url><loc>'+BASE+u+'</loc><lastmod>'+article_dates.get(u,PRINTER_DATE if u.startswith('printers/') else DATE)+'</lastmod></url>\n' for u in urls)+'</urlset>\n'
    (ROOT/'sitemap.xml').write_text(sitemap)
    print(json.dumps(summary,sort_keys=True))

if __name__=='__main__': sync()
