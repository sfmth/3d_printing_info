#!/usr/bin/env python3
"""Dependency-free regression checks for static pages and table data."""
import json
import re
import subprocess
import tempfile
from pathlib import Path
from sync_summary import ROOT, payload

pages = ('index.html', 'comparison.html', 'filaments.html')
for filename in pages:
    page = (ROOT / filename).read_text()
    assert page.count('https://www.googletagmanager.com/gtag/js?id=G-12FDG0Z8JB') == 1, filename
    assert page.count("gtag('config', 'G-12FDG0Z8JB')") == 1, filename
    for attrs, script in re.findall(r'<script([^>]*)>(.*?)</script>', page, re.S):
        if 'application/ld+json' in attrs or 'application/json' in attrs:
            json.loads(script)
        elif script.strip():
            with tempfile.NamedTemporaryFile(suffix='.js', mode='w') as tmp:
                tmp.write(script); tmp.flush()
                subprocess.run(['node', '--check', tmp.name], check=True, capture_output=True)
    for href in re.findall(r'(?:href|src)="([^"#?]+)"', page):
        if '$' not in href and not re.match(r'\w+:|//', href):
            assert (ROOT / href).exists(), (filename, href)
    if filename == 'index.html':
        continue
    data = payload(page)
    ids = [c['id'] for c in data['cats']]
    assert len(ids) == len(set(ids)), filename
    fallback = re.search(r'<noscript>(.*?)</noscript>', page, re.S)[1]
    assert fallback.count('<th scope="row">') == len(ids), filename
    fields = {f['id'] for f in data['fields']}
    def check_spec(spec):
        assert set(spec) <= fields, (filename, set(spec) - fields)
        for value in spec.values():
            assert set(value.get('s', [])) <= data['src'].keys(), (filename, value)
    for cat in data['cats']:
        assert cat['f'] in data['families'], (filename, cat['id'])
        check_spec(cat['sp'])
        for product in cat.get('pr', []):
            check_spec(product.get('sp', {}))
            assert set(product.get('s', [])) <= data['src'].keys(), (filename, product.get('p'))
            assert set(product.get('tds') or []) <= data['src'].keys(), (filename, product.get('p'))
    structured = [json.loads(s) for s in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)]
    webpage = next(x for x in structured if x.get('@type') == 'WebPage')
    assert webpage['url'].endswith(filename), filename
    for item in structured:
        if item.get('@type') == 'ItemList':
            assert item['numberOfItems'] == len(ids), filename
    print(f'{filename}: {len(ids)} entries, {len(fields)} fields, valid tags/scripts/links/metadata')
index = (ROOT / 'index.html').read_text()
printers = payload((ROOT / 'comparison.html').read_text())
filaments = payload((ROOT / 'filaments.html').read_text())
for key, count in {'printers':len(printers['cats']), 'printer-fields':len(printers['fields']),
                   'materials':len(filaments['cats']), 'products':sum(len(c.get('pr', [])) for c in filaments['cats'])}.items():
    matches = re.findall(r'data-summary="'+key+r'">(\d+)', index)
    assert len(matches) == (2 if key in ('printers', 'printer-fields') else 1), key
    assert all(int(n) == count for n in matches), key
print('All static site checks passed.')
