"""Presentation for material guides; the embedded catalogs remain untouched."""
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import quote

E = lambda x: escape(str(x), quote=True)
FAMILIES = {
    'PLA': ('PLA', 'Models, prototypes and decorative prints', '#e66e42', 'bracket'),
    'PETG': ('PETG & related polymers', 'Practical parts and durable everyday prints', '#268d86', 'gear'),
    'ABS': ('ABS', 'Functional parts with more demanding setup', '#586b83', 'bracket'),
    'ASA': ('ASA', 'Explore weather-resistant formulations', '#8975b7', 'bracket'),
    'PC': ('Polycarbonate', 'Explore tough engineering formulations', '#408ca8', 'bracket'),
    'PA': ('Nylon & composites', 'Engineering polymers and reinforced grades', '#b98b32', 'gear'),
    'FLEX': ('Flexible materials', 'Rubbery, flexible and cushioning grades', '#36a19b', 'flex'),
    'POLYOLEFIN': ('Polyolefins', 'Polypropylene, polyethylene and composites', '#dc8361', 'bracket'),
    'ENGINEERING': ('Engineering materials', 'Specialized functional polymers', '#5c7b8b', 'gear'),
    'HIGHTEMP': ('High-temperature polymers', 'Advanced polymers and demanding hardware', '#b96a5e', 'bracket'),
    'SUPPORT': ('Support materials', 'Breakaway and soluble support options', '#76a1bc', 'support'),
    'SPECIALTY': ('Specialty materials', 'Unusual finishes, functions and formulations', '#ad9271', 'gear'),
}
INTRO = {
    'pla': 'A familiar starting point for models, prototypes and everyday prints at room temperature.',
    'petg': 'A practical step up from PLA for tougher functional parts. Expect a little more tuning.',
    'asa': 'A material to consider for outdoor parts. An enclosed printer is part of the setup.',
    'abs': 'A familiar engineering plastic for functional parts, with more demanding printing conditions.',
    'tpu-95a': 'For flexible parts such as gaskets, protective covers and vibration mounts.',
    'pc': 'For demanding functional parts where toughness and heat tolerance matter.',
    'pa6-cf': 'A stiff, reinforced engineering material for brackets, tooling and loaded parts.',
    'peba': 'A flexible polyamide blend used in cushioning, footwear and sports equipment.',
}
FEATURED = ('pla', 'petg', 'asa', 'tpu-95a', 'pc', 'abs')
_examples = json.loads((Path(__file__).resolve().parents[1]/'data/print-examples.json').read_text())
EXAMPLES = {cid: entries if isinstance(entries, list) else [entries] for cid, entries in _examples.items()}


def primary_example(cid):
    entries = EXAMPLES.get(cid, [])
    return next((e for e in entries if e.get('image')), entries[0] if entries else None)
LABELS = {'A':'Material & market', 'B':'Print settings', 'C':'Nozzle wear & reliability',
          'D':'Moisture & drying', 'E':'Strength & mechanical properties', 'F':'Heat & temperature',
          'G':'Weather & chemical resistance', 'H':'Health & safety', 'I':'Finishing & post-processing',
          'J':'Solvents & solubility'}


def compact(value, limit=135):
    text = re.sub(r'\s+', ' ', str(value)).strip()
    if len(text) <= limit: return text
    return text[:limit].rsplit(' ', 1)[0].rstrip(' ,;:') + '…'


def count_label(number, noun):
    return str(number)+' '+noun+('' if number==1 else 's')


def discovery(c):
    query=c.get('sh') or c['n']
    return '<div class="model-search-links">'+''.join('<a href="'+E(url+quote(query))+'">'+label+' <span aria-hidden="true">↗</span></a>' for label,url in [('Printables','https://www.printables.com/search/models?q='),('MakerWorld','https://makerworld.com/en/search/models?keyword='),('Thingiverse','https://www.thingiverse.com/search?q=')])+'</div>'


def photograph(e, cls='material-visual'):
    return '<figure class="'+cls+'" data-print-example><a class="print-photo-link" href="'+E(e['url'])+'" aria-label="View '+E(e['title'])+' on '+E(e['platform'])+'"><img src="../'+E(e['image'])+'" alt="'+E(e['alt'])+'" width="'+str(e['width'])+'" height="'+str(e['height'])+'" fetchpriority="high"></a><figcaption><span class="eyebrow">Printed in '+E(e['material'])+'</span><a class="print-title" href="'+E(e['url'])+'">'+E(e['title'])+' <span aria-hidden="true">↗</span></a><span>Photo & model by '+E(e['creator'])+' · '+E(e['platform'])+' · <a href="'+E(e['license_url'])+'">'+E(e['license'])+'</a></span></figcaption></figure>'


def card(c, featured=False):
    cls='featured-card' if featured else 'material-card'
    text=INTRO.get(c['id']) or c.get('sum','');e=primary_example(c['id'])
    attrs='' if featured else ' data-material="'+E(c['id'])+'" data-search="'+E(' '.join([c['n'],c.get('aka',''),c['f'],c.get('sum',''),c['sp'].get('A7',{}).get('v','')]))+'"'
    body='<article class="'+cls+(' has-photo' if e and e.get('image') else ' text-only')+'"'+attrs+'><a class="material-card-link" href="'+E(c['id'])+'.html">'
    if e and e.get('image'):body+='<img src="../'+E(e['image'])+'" alt="'+E(e['alt'])+'" loading="lazy" width="'+str(e['width'])+'" height="'+str(e['height'])+'">'
    body+='<div class="material-card-copy"><span class="eyebrow">'+E(c['f'])+'</span><h3>'+E(c['n'])+'</h3><p>'+E(compact(text,128))+'</p><span class="card-bottom">'+count_label(len(c.get('pr',[])),'product listing')+' <span aria-hidden="true">↗</span></span></div></a>'
    if e:body+='<div class="card-example"><a href="'+E(e['url'])+'">View print by '+E(e['creator'])+' ↗</a> · <a href="'+E(e['license_url'])+'">'+E(e['license'])+'</a></div>'
    return body+'</article>'


def print_section(c):
    examples=EXAMPLES.get(c['id'],[])
    primary=primary_example(c['id'])
    body='<section class="guide-section print-examples" id="prints"><div class="section-heading"><div><span class="eyebrow">From the maker community</span><h2>Things people print</h2></div></div>'
    for e in examples:
        body+='<article class="print-story">'
        if e.get('image') and e is not primary:
            body+='<a href="'+E(e['url'])+'"><img class="example-photo" src="../'+E(e['image'])+'" alt="'+E(e['alt'])+'" width="'+str(e['width'])+'" height="'+str(e['height'])+'" loading="lazy"></a>'
        body+='<span class="print-badge">Creator-reported '+E(e['material'])+' print</span><h3><a href="'+E(e['url'])+'">'+E(e['title'])+' ↗</a></h3><p>'+E(e['note'])+'</p><a class="text-link" href="'+E(e['url'])+'">Get the model & read the creator’s print notes on '+E(e['platform'])+' ↗</a><details class="inline-sources"><summary>Material evidence & '+('photo credit' if e.get('image') else 'model credit')+'</summary><p>Creator’s note: “'+E(e['evidence'])+'”</p><p>'+('Photo and model' if e.get('image') else 'Model')+': '+E(e['creator'])+' · <a href="'+E(e['url'])+'">Original listing</a> · <a href="'+E(e['license_url'])+'">'+E(e['license'])+'</a> · Checked '+E(e['checked'])+'. '+('Photo bytes unchanged. Appearance can include paint or other finishing. ' if e.get('image') else '')+'This is a creator report, not an independent material test.</p></details></article>'
    if not examples:body+='<p class="section-description">No verified photo example is curated for this exact material yet. Explore community models below; check each creator’s actual filament and print notes.</p>'
    body+='<div class="more-models"><h3>Explore more '+E(c.get('sh') or c['n'])+' models</h3>'+discovery(c)+'<p>Search results are ideas, not verified material matches. A suggested filament is not proof of the material in a photo.</p></div></section>'
    return body


def property_table(data,c,section,refs):
    fields=[f for f in data['fields'] if f['sec']==section and f['id'] in c['sp']]
    if not fields:return ''
    title=LABELS[section]
    body='<details class="spec-group" id="spec-'+section.lower()+'"><summary><span>'+E(title)+'</span><span class="section-count">'+count_label(len(fields),'field')+'</span></summary><div class="table-scroll"><table><caption>'+E(c['n']+' — '+data['sections'][section])+'</caption><thead><tr><th scope="col">Property and unit</th><th scope="col">Published value and conditions</th><th scope="col">Sources and dates</th></tr></thead><tbody>'
    for f in fields:
        e=c['sp'][f['id']];sources=e.get('s',[])
        body+='<tr><th scope="row">'+E(f['name'])+((' <span class="unit">('+E(f['unit'])+')</span>') if f.get('unit') else '')+'</th><td>'+E(e['v'])+'</td><td><details class="row-sources"><summary>'+count_label(len(sources),'source')+'</summary>'+refs(data,sources)+'</details></td></tr>'
    return body+'</tbody></table></div></details>'


def detail_body(data,c,refs,value):
    family=FAMILIES[c['f']];products=c.get('pr',[]);brands={p['b'] for p in products}
    intro=INTRO.get(c['id']) or compact(c.get('sum',''),190)
    body='<nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../">Home</a><span>/</span><a href="./">Material guides</a><span>/</span><span>'+E(c['sh'] if c.get('sh') else c['n'])+'</span></nav>'
    body+='<header class="guide-hero"><div class="hero-copy"><span class="eyebrow">'+E(family[0])+' · Material guide</span><h1>'+E(c['n'])+'</h1><p class="guide-lede">'+E(intro)+'</p><div class="guide-meta"><span>'+count_label(len(products),'product listing')+'</span><span>'+count_label(len(brands),'brand')+'</span></div><a class="primary-action" href="../filaments.html?material='+E(c['id'])+'">Open in interactive comparison <span aria-hidden="true">↗</span></a></div></header>'
    visual=photograph(primary_example(c['id'])) if (primary_example(c['id']) or {}).get('image') else '<aside class="print-discovery"><span class="eyebrow">Make something with it</span><h2>Find your next print</h2><p>Explore community models and check each creator’s material notes.</p>'+discovery(c)+'<a class="text-link" href="#prints">About printed examples ↓</a></aside>'
    body=body.replace('</header>',visual+'</header>',1)
    body+='<nav class="guide-jumps" aria-label="On this page"><a href="#overview">Overview</a><a href="#prints">Printed examples</a><a href="#setup">Print setup</a><a href="#properties">All properties</a><a href="#products">Filaments</a></nav>'
    body+='<section class="guide-section" id="overview"><div class="section-heading"><div><span class="eyebrow">Understand the material</span><h2>At a glance</h2></div></div><div class="overview-grid"><article class="overview-card"><span class="mini-icon" aria-hidden="true">↗</span><h3>Where it is used</h3><p>'+E(value(c,'A7'))+'</p><details class="inline-sources"><summary>Sources</summary>'+refs(data,c['sp'].get('A7',{}).get('s',[]))+'</details></article><article class="overview-card"><span class="mini-icon" aria-hidden="true">⌁</span><h3>Before you print</h3><dl>'
    for fid,label in [('B12','Setup difficulty'),('C2','Nozzle wear')]:
        body+='<div><dt>'+label+'</dt><dd>'+E(compact(value(c,fid),110))+'</dd></div>'
    body+='</dl><a class="text-link" href="#properties">Read conditions and sources ↓</a></article></div><details class="catalog-summary"><summary>Read the full material overview</summary><p>'+E(c.get('sum',''))+'</p></details></section>'
    body+=print_section(c)
    print_anchor='spec-b' if any(f['sec']=='B' and f['id'] in c['sp'] for f in data['fields']) else 'properties'
    body+='<section class="guide-section" id="setup"><div class="section-heading"><div><span class="eyebrow">Plan your printer setup</span><h2>Printing quick reference</h2></div><a class="text-link" href="#'+print_anchor+'">All print settings ↓</a></div><p class="section-description">Representative catalog values. Check the exact grade and its linked conditions before using a setting.</p><div class="setup-grid">'
    for fid,label,icon in [('B1','Nozzle temperature (°C)','01'),('B2','Bed temperature (°C)','02'),('B3','Enclosure','03'),('D3','Drying','04')]:
        full=value(c,fid); short=compact(full.split(' — ')[0],100)
        body+='<article class="setup-card"><span class="setup-number">'+icon+'</span><h3>'+label+'</h3><p>'+E(short)+'</p><details class="inline-sources"><summary>Full value & sources</summary><p>'+E(full)+'</p>'+refs(data,c['sp'].get(fid,{}).get('s',[]))+'</details></article>'
    body+='</div></section><section class="guide-section" id="properties"><div class="section-heading"><div><span class="eyebrow">Go deeper when you need to</span><h2>Properties & source data</h2></div><span class="quiet-label">'+str(len(c['sp']))+' documented fields</span></div><p class="section-description">Open a topic to explore the complete data. Each value keeps its original conditions, units and dated sources.</p><div class="spec-sections">'
    for sid in data['sections']:body+=property_table(data,c,sid,refs)
    body+='</div><details class="reading-note"><summary>How to read these values</summary><p>Values describe representative grades, not every spool. Manufacturer datasheets and independent tests retain their source labels and dates. Printed orientation, test method, conditioning and formulation can change results. Unknown values are —. A listed use is not a certification. Shore A, Shore D and Rockwell hardness are separate scales.</p></details></section>'
    body+='<section class="guide-section" id="products"><div class="section-heading"><div><span class="eyebrow">Find a specific filament</span><h2>Product listings and datasheets</h2></div><span class="quiet-label">'+count_label(len(products),'listing')+'</span></div><p class="section-description">Historical USD/kg snapshots. Read each listing’s sale/from qualifiers, spool mass, source date, shipping and tax notes. Product figures are separate from the material summary.</p>'
    if products:
        body+='<details class="product-library"><summary>Browse '+count_label(len(products),'product')+' from '+count_label(len(brands),'brand')+' <span aria-hidden="true">↓</span></summary><div class="product-list">'
        for p in products:
            name=p['b']+' '+p['p'];price=f"{p['k']:.2f} USD/kg" if p.get('k') is not None else 'Price unknown'
            body+='<details class="product-entry"><summary><span><small>'+E(p['b'])+'</small>'+E(p['p'])+'</span><span class="product-price">'+E(price)+'</span></summary><div class="product-content"><p class="price-note">'+E(p.get('pn',''))+'</p><p>'+E(p.get('nt',''))+'</p>'
            if p.get('u'):body+='<a class="text-link" href="'+E(p['u'])+'">Open product listing ↗</a>'
            body+=refs(data,[*p.get('s',[]),*(p.get('tds') or [])])
            if p.get('sp'):
                body+='<div class="table-scroll"><table><caption>'+E(name)+' — product-specific figures</caption><tbody>'
                for f in data['fields']:
                    if f['id'] not in p['sp']:continue
                    e=p['sp'][f['id']];body+='<tr><th scope="row">'+E(f['name'])+((' ('+E(f['unit'])+')') if f.get('unit') else '')+'</th><td>'+E(e['v'])+'</td><td>'+refs(data,e.get('s',[]))+'</td></tr>'
                body+='</tbody></table></div>'
            body+='</div></details>'
        body+='</div></details>'
    else:body+='<p class="empty-list">No specific product listings are recorded yet. The sourced material properties remain available above.</p>'
    body+='</section>'
    siblings=[x for x in data['cats'] if x['f']==c['f'] and x['id']!=c['id']]
    if siblings:
        body+='<section class="guide-section related-materials"><div class="section-heading"><div><span class="eyebrow">Keep exploring</span><h2>Related materials</h2></div><a class="text-link" href="./?family='+quote(c['f'])+'">All '+E(family[0])+' guides ↗</a></div><div class="featured-grid">'+''.join(card(x,True) for x in siblings[:3])+'</div></section>'
    return body


def directory_body(data):
    cs=len(data['cats']);products=sum(len(c.get('pr',[])) for c in data['cats']);brands=len({p['b'].lower() for c in data['cats'] for p in c.get('pr',[])})
    body='<header class="library-hero"><div><span class="eyebrow">A field guide to 3D printing</span><h1>Material guides</h1><p class="guide-lede">Find the right filament for your next print. Start with the essentials, then explore the settings, properties and sources that matter to you.</p><div class="library-stats"><span><b>'+str(cs)+'</b> materials</span><span><b>'+str(products)+'</b> products</span><span><b>'+str(brands)+'</b> brands</span></div><a class="primary-action" href="#browse-materials">Browse material guides <span aria-hidden="true">↓</span></a><a class="text-link library-compare" href="../filaments.html">Open the interactive comparison table ↗</a></div>'+photograph(primary_example('pla'),'library-visual')+'</header>'
    lookup={c['id']:c for c in data['cats']}
    body+='<section class="guide-section" id="featured-materials"><div class="section-heading"><div><span class="eyebrow">A few familiar starting points</span><h2>Start exploring</h2></div><a class="text-link" href="#browse-materials">Browse all '+str(cs)+' materials ↓</a></div><div class="featured-grid">'+''.join(card(lookup[cid],True) for cid in FEATURED if cid in lookup)+'</div></section>'
    body+='<section class="guide-section" id="browse-materials"><div class="section-heading"><div><span class="eyebrow">The complete library</span><h2>Browse by material family</h2></div></div><div class="material-search" hidden><label for="material-search">Search material guides</label><div class="search-input-wrap"><input id="material-search" type="search" placeholder="Try PLA, carbon fibre, flexible, outdoor…" autocomplete="off"><button type="button" id="clear-material-search">Clear</button></div><div class="family-filters" role="group" aria-label="Filter material family"><button type="button" data-family="" aria-pressed="true">All materials</button>'+''.join('<button type="button" data-family="'+E(f)+'" aria-pressed="false">'+E(f)+'</button>' for f in data['families'])+'</div><p id="material-results" role="status" aria-live="polite">'+str(cs)+' materials</p></div><div class="material-families">'
    for family in data['families']:
        cats=[c for c in data['cats'] if c['f']==family];title,subtitle,_,_=FAMILIES[family]
        body+='<details class="family-group" data-family-group="'+E(family)+'"><summary><span class="family-marker" aria-hidden="true">'+E(family)+'</span><span><b>'+E(title)+'</b><small>'+E(subtitle)+'</small></span><span class="family-count">'+count_label(len(cats),'material')+'</span></summary><div class="material-grid">'+''.join(card(c) for c in cats)+'</div></details>'
    return body+'</div><div id="material-no-results" hidden><h3>No materials found</h3><p>Try a broader name or clear the family filter.</p></div><noscript><p class="section-description">Open any family to browse its guides. Search and family filters become available with JavaScript.</p></noscript></section>'
