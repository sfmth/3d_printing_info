"""Presentation for material guides; the embedded catalogs remain untouched."""
from html import escape
import math
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
FEATURED = ('pla', 'petg', 'asa', 'tpu-95a', 'pc', 'pa6-cf')
LABELS = {'A':'Material & market', 'B':'Print settings', 'C':'Nozzle wear & reliability',
          'D':'Moisture & drying', 'E':'Strength & mechanical properties', 'F':'Heat & temperature',
          'G':'Weather & chemical resistance', 'H':'Health & safety', 'I':'Finishing & post-processing',
          'J':'Solvents & solubility'}


def compact(value, limit=135):
    text = re.sub(r'\s+', ' ', str(value)).strip()
    if len(text) <= limit: return text
    return text[:limit].rsplit(' ', 1)[0].rstrip(' ,;:') + '…'


def art_name(family): return family.lower() + '.svg'


def spool(color):
    rings = ''.join(f'<ellipse cx="240" cy="318" rx="{r}" ry="{r*1.46:.1f}" fill="none" stroke="#fff" stroke-opacity=".16" stroke-width="1.2"/>' for r in range(39,72,4))
    return f'''<g><ellipse cx="311" cy="275" rx="91" ry="133" fill="#293743"/><path d="M240 190 311 142A91 133 0 0 1 311 408L240 451Z" fill="{color}"/><path d="M250 209 314 164M259 227 324 184M269 246 336 202M280 265 347 223M289 287 357 245M294 312 362 270M294 336 362 295M288 360 354 320M280 383 346 343M270 404 336 364M257 426 325 385" stroke="#fff" stroke-opacity=".18" stroke-width="2"/><ellipse cx="240" cy="318" rx="91" ry="133" fill="#293743"/><ellipse cx="240" cy="318" rx="74" ry="110" fill="{color}"/>{rings}<ellipse cx="240" cy="318" rx="33" ry="48" fill="#293743"/><ellipse cx="240" cy="318" rx="18" ry="27" fill="#101d28"/><path d="M186 378q23 30 54 30t54-30" fill="none" stroke="#eef3f5" stroke-opacity=".8" stroke-width="9"/><path d="M214 397h48" stroke="#293743" stroke-width="2"/></g>'''


def bracket(color, translucent=False):
    lines=''.join(f'<path d="M437 {y} 612 {y+101}"/>' for y in range(190,320,9))
    return f'''<g opacity="{'.8' if translucent else '1'}"><path d="m440 162 174 101 39-22-174-101Z" fill="{color}"/><path d="m614 263 39-22v153l-39 23Z" fill="{color}" filter="url(#shade)"/><path d="m440 162 174 101v154L440 316Z" fill="{color}"/><g clip-path="url(#plate)" fill="none" stroke="#000" stroke-opacity=".13" stroke-width="2">{lines}</g><ellipse cx="524" cy="274" rx="21" ry="29" transform="rotate(-30 524 274)" fill="#293743"/><ellipse cx="524" cy="268" rx="16" ry="23" transform="rotate(-30 524 268)" fill="#182934"/><path d="m440 316 174 101-92 53-174-101Z" fill="{color}"/><path d="m348 369 174 101v25L348 394Z" fill="{color}" filter="url(#shade)"/><path d="m522 470 92-53v25l-92 53Z" fill="{color}" filter="url(#shade)"/><path d="m349 377 173 100m-173-92 173 100" stroke="#000" stroke-opacity=".14" stroke-width="2"/><ellipse cx="441" cy="394" rx="24" ry="13" fill="#293743"/><path d="m440 162 174 101 39-22" fill="none" stroke="#fff" stroke-opacity=".45" stroke-width="2"/></g>'''


def gear(color):
    pts=[]
    for i in range(64):
        angle=i*math.pi/32; radius=116 if i%4 in (1,2) else 96
        pts.append(f'{radius*math.cos(angle):.2f},{radius*math.sin(angle):.2f}')
    shape=' '.join(pts)
    return f'''<g transform="translate(527 331) matrix(1 .53 -.7 .48 0 0)"><polygon points="{shape}" transform="translate(0 33)" fill="{color}" filter="url(#shade)"/><path d="M-95 0v33M95 0v33M0 96v33" stroke="{color}" stroke-width="20"/><polygon points="{shape}" fill="{color}"/><circle r="67" fill="none" stroke="#fff" stroke-opacity=".25" stroke-width="4"/><circle r="32" fill="#243744"/><circle r="18" fill="#eaf0f2"/><g fill="#243744"><circle cx="54" cy="0" r="10"/><circle cx="-54" cy="0" r="10"/><circle cx="0" cy="54" r="10"/><circle cx="0" cy="-54" r="10"/></g></g>'''


def flexible(color):
    return f'''<g transform="translate(10 8)"><path d="M420 410c-50-25-40-65 12-70l120-15c52-6 60-46 8-72l-52-26" fill="none" stroke="#1d4548" stroke-opacity=".22" stroke-width="53" stroke-linecap="round" transform="translate(0 15)"/><path d="M420 410c-50-25-40-65 12-70l120-15c52-6 60-46 8-72l-52-26" fill="none" stroke="{color}" stroke-width="48" stroke-linecap="round"/><path d="M415 400c-40-20-30-46 18-52l118-15c58-7 72-51 13-87l-52-26" fill="none" stroke="#fff" stroke-opacity=".24" stroke-width="3" stroke-linecap="round"/></g>'''


def supports(color):
    return ''.join(f'<g transform="translate({x} {y})"><path d="m0 0 48 28 40-23-48-28Z" fill="{color}"/><path d="m0 0 48 28v150L0 150Z" fill="{color}"/><path d="m48 28 40-23v150l-40 23Z" fill="{color}" filter="url(#shade)"/><path d="m8 20 31 18m-31-7 31 18m-31-7 31 18m-31-7 31 18m-31-7 31 18m-31-7 31 18m-31-7 31 18m-31-7 31 18" stroke="#fff" stroke-opacity=".3" stroke-width="2"/></g>' for x,y in [(414,270),(466,214),(520,290)])


def illustration(family):
    label,_,color,shape=FAMILIES[family]
    part=gear(color) if shape=='gear' else flexible(color) if shape=='flex' else supports(color) if shape=='support' else bracket(color,family=='PC')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600" role="img"><title>{E(label)} filament and printed part illustration</title><defs><radialGradient id="bg"><stop stop-color="#fff"/><stop offset="1" stop-color="#eaf0f2"/></radialGradient><filter id="blur"><feGaussianBlur stdDeviation="17"/></filter><filter id="shade"><feColorMatrix type="matrix" values=".72 0 0 0 0 0 .72 0 0 0 0 0 .72 0 0 0 0 0 1 0"/></filter><clipPath id="plate"><path d="m440 162 174 101v154L440 316Z"/></clipPath></defs><rect width="800" height="600" rx="30" fill="url(#bg)"/><circle cx="635" cy="100" r="140" fill="{color}" opacity=".06"/><path d="m70 445 320-185 350 202M110 485l320-185 280 162" fill="none" stroke="#cad6db" stroke-opacity=".4"/><ellipse cx="405" cy="481" rx="255" ry="28" fill="#334958" opacity=".16" filter="url(#blur)"/>{spool(color)}{part}<path d="M119 457q-64 9-40 27t85 3" fill="none" stroke="{color}" stroke-width="4" stroke-linecap="round"/></svg>\n'''


def write_art(root):
    folder=root/'assets/materials';folder.mkdir(parents=True,exist_ok=True)
    for family in FAMILIES:(folder/art_name(family)).write_text(illustration(family))


def card(c, featured=False):
    cls='featured-card' if featured else 'material-card'
    text=INTRO.get(c['id']) or c.get('sum','')
    return '<a class="'+cls+'" href="'+E(c['id'])+'.html"'+('' if featured else ' data-material="'+E(c['id'])+'" data-search="'+E(' '.join([c['n'],c.get('aka',''),c['f'],c.get('sum',''),c['sp'].get('A7',{}).get('v','')]))+'"')+'><img src="../assets/materials/'+art_name(c['f'])+'" alt="" loading="lazy" width="800" height="600"><div class="material-card-copy"><span class="eyebrow">'+E(c['f'])+'</span><h3>'+E(c['n'])+'</h3><p>'+E(compact(text,128))+'</p><span class="card-bottom">'+str(len(c.get('pr',[])))+' product listings <span aria-hidden="true">↗</span></span></div></a>'


def property_table(data,c,section,refs):
    fields=[f for f in data['fields'] if f['sec']==section and f['id'] in c['sp']]
    if not fields:return ''
    title=LABELS[section]
    body='<details class="spec-group" id="spec-'+section.lower()+'"><summary><span>'+E(title)+'</span><span class="section-count">'+str(len(fields))+' fields</span></summary><div class="table-scroll"><table><caption>'+E(c['n']+' — '+data['sections'][section])+'</caption><thead><tr><th scope="col">Property and unit</th><th scope="col">Published value and conditions</th><th scope="col">Sources and dates</th></tr></thead><tbody>'
    for f in fields:
        e=c['sp'][f['id']];sources=e.get('s',[])
        body+='<tr><th scope="row">'+E(f['name'])+((' <span class="unit">('+E(f['unit'])+')</span>') if f.get('unit') else '')+'</th><td>'+E(e['v'])+'</td><td><details class="row-sources"><summary>'+str(len(sources))+' sources</summary>'+refs(data,sources)+'</details></td></tr>'
    return body+'</tbody></table></div></details>'


def detail_body(data,c,refs,value):
    family=FAMILIES[c['f']];products=c.get('pr',[]);brands={p['b'] for p in products}
    intro=INTRO.get(c['id']) or compact(c.get('sum',''),190)
    body='<nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../">Home</a><span>/</span><a href="./">Material guides</a><span>/</span><span>'+E(c['sh'] if c.get('sh') else c['n'])+'</span></nav>'
    body+='<header class="guide-hero"><div class="hero-copy"><span class="eyebrow">'+E(family[0])+' · Material guide</span><h1>'+E(c['n'])+'</h1><p class="guide-lede">'+E(intro)+'</p><div class="guide-meta"><span>'+str(len(products))+' product listings</span><span>'+str(len(brands))+' brands</span></div><a class="primary-action" href="../filaments.html?material='+E(c['id'])+'">Open in interactive comparison <span aria-hidden="true">↗</span></a></div><figure class="material-visual"><img src="../assets/materials/'+art_name(c['f'])+'" alt="Illustration of a filament spool and a layered printed sample" width="800" height="600" fetchpriority="high"><figcaption>Illustration · appearance varies by formulation and finish</figcaption></figure></header>'
    body+='<nav class="guide-jumps" aria-label="On this page"><a href="#overview">Overview</a><a href="#setup">Print setup</a><a href="#properties">All properties</a><a href="#products">Filaments</a></nav>'
    body+='<section class="guide-section" id="overview"><div class="section-heading"><div><span class="eyebrow">Understand the material</span><h2>At a glance</h2></div></div><div class="overview-grid"><article class="overview-card"><span class="mini-icon" aria-hidden="true">↗</span><h3>Where it is used</h3><p>'+E(value(c,'A7'))+'</p><details class="inline-sources"><summary>Sources</summary>'+refs(data,c['sp'].get('A7',{}).get('s',[]))+'</details></article><article class="overview-card"><span class="mini-icon" aria-hidden="true">⌁</span><h3>Before you print</h3><dl>'
    for fid,label in [('B12','Setup difficulty'),('C2','Nozzle wear')]:
        body+='<div><dt>'+label+'</dt><dd>'+E(compact(value(c,fid),110))+'</dd></div>'
    body+='</dl><a class="text-link" href="#properties">Read conditions and sources ↓</a></article></div><details class="catalog-summary"><summary>Read the full material overview</summary><p>'+E(c.get('sum',''))+'</p></details></section>'
    print_anchor='spec-b' if any(f['sec']=='B' and f['id'] in c['sp'] for f in data['fields']) else 'properties'
    body+='<section class="guide-section" id="setup"><div class="section-heading"><div><span class="eyebrow">Plan your printer setup</span><h2>Printing quick reference</h2></div><a class="text-link" href="#'+print_anchor+'">All print settings ↓</a></div><p class="section-description">Representative catalog values. Check the exact grade and its linked conditions before using a setting.</p><div class="setup-grid">'
    for fid,label,icon in [('B1','Nozzle temperature (°C)','01'),('B2','Bed temperature (°C)','02'),('B3','Enclosure','03'),('D3','Drying','04')]:
        full=value(c,fid); short=compact(full.split(' — ')[0],100)
        body+='<article class="setup-card"><span class="setup-number">'+icon+'</span><h3>'+label+'</h3><p>'+E(short)+'</p><details class="inline-sources"><summary>Full value & sources</summary><p>'+E(full)+'</p>'+refs(data,c['sp'].get(fid,{}).get('s',[]))+'</details></article>'
    body+='</div></section><section class="guide-section" id="properties"><div class="section-heading"><div><span class="eyebrow">Go deeper when you need to</span><h2>Properties & source data</h2></div><span class="quiet-label">'+str(len(c['sp']))+' documented fields</span></div><p class="section-description">Open a topic to explore the complete data. Each value keeps its original conditions, units and dated sources.</p><div class="spec-sections">'
    for sid in data['sections']:body+=property_table(data,c,sid,refs)
    body+='</div><details class="reading-note"><summary>How to read these values</summary><p>Values describe representative grades, not every spool. Manufacturer datasheets and independent tests retain their source labels and dates. Printed orientation, test method, conditioning and formulation can change results. Unknown values are —. A listed use is not a certification. Shore A, Shore D and Rockwell hardness are separate scales.</p></details></section>'
    body+='<section class="guide-section" id="products"><div class="section-heading"><div><span class="eyebrow">Find a specific filament</span><h2>Product listings and datasheets</h2></div><span class="quiet-label">'+str(len(products))+' listings</span></div><p class="section-description">Historical USD/kg snapshots. Read each listing’s sale/from qualifiers, spool mass, source date, shipping and tax notes. Product figures are separate from the material summary.</p>'
    if products:
        body+='<details class="product-library"><summary>Browse all '+str(len(products))+' products from '+str(len(brands))+' brands <span aria-hidden="true">↓</span></summary><div class="product-list">'
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
    body='<header class="library-hero"><div><span class="eyebrow">A field guide to 3D printing</span><h1>Material guides</h1><p class="guide-lede">Find the right filament for your next print. Start with the essentials, then explore the settings, properties and sources that matter to you.</p><div class="library-stats"><span><b>'+str(cs)+'</b> materials</span><span><b>'+str(products)+'</b> products</span><span><b>'+str(brands)+'</b> brands</span></div><a class="primary-action" href="#browse-materials">Browse material guides <span aria-hidden="true">↓</span></a><a class="text-link library-compare" href="../filaments.html">Open the interactive comparison table ↗</a></div><figure class="library-visual"><img src="../assets/materials/pla.svg" alt="Illustration of a colorful filament spool and a layered printed bracket" width="800" height="600" fetchpriority="high"><figcaption>Original material illustrations</figcaption></figure></header>'
    lookup={c['id']:c for c in data['cats']}
    body+='<section class="guide-section" id="featured-materials"><div class="section-heading"><div><span class="eyebrow">A few familiar starting points</span><h2>Start exploring</h2></div><a class="text-link" href="#browse-materials">Browse all '+str(cs)+' materials ↓</a></div><div class="featured-grid">'+''.join(card(lookup[cid],True) for cid in FEATURED if cid in lookup)+'</div></section>'
    body+='<section class="guide-section" id="browse-materials"><div class="section-heading"><div><span class="eyebrow">The complete library</span><h2>Browse by material family</h2></div></div><div class="material-search" hidden><label for="material-search">Search material guides</label><div class="search-input-wrap"><input id="material-search" type="search" placeholder="Try PLA, carbon fibre, flexible, outdoor…" autocomplete="off"><button type="button" id="clear-material-search">Clear</button></div><div class="family-filters" role="group" aria-label="Filter material family"><button type="button" data-family="" aria-pressed="true">All materials</button>'+''.join('<button type="button" data-family="'+E(f)+'" aria-pressed="false">'+E(f)+'</button>' for f in data['families'])+'</div><p id="material-results" role="status" aria-live="polite">'+str(cs)+' materials</p></div><div class="material-families">'
    for family in data['families']:
        cats=[c for c in data['cats'] if c['f']==family];title,subtitle,_,_=FAMILIES[family]
        body+='<details class="family-group" data-family-group="'+E(family)+'"><summary><img src="../assets/materials/'+art_name(family)+'" alt="" width="800" height="600" loading="lazy"><span><b>'+E(title)+'</b><small>'+E(subtitle)+'</small></span><span class="family-count">'+str(len(cats))+' materials</span></summary><div class="material-grid">'+''.join(card(c) for c in cats)+'</div></details>'
    return body+'</div><div id="material-no-results" hidden><h3>No materials found</h3><p>Try a broader name or clear the family filter.</p></div><noscript><p class="section-description">Open any family to browse its guides. Search and family filters become available with JavaScript.</p></noscript></section>'
