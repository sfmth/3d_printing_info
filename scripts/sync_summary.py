#!/usr/bin/env python3
"""Refresh static homepage counts and structured data from the table payloads."""
import json
from html import escape
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def payload(page):
    return json.loads(re.search(r'<script[^>]*id="payload"[^>]*>(.*?)</script>', page, re.S)[1])


def sync():
    datasets = {}
    for filename in ('comparison.html', 'filaments.html'):
        path = ROOT / filename
        page = path.read_text()
        data = datasets[filename] = payload(page)
        def refresh(match):
            item = json.loads(match[1])
            if item.get('@type') == 'ItemList':
                item['numberOfItems'] = len(data['cats'])
                item['itemListElement'] = [
                    {'@type': 'ListItem', 'position': i, 'name': c['n']}
                    for i, c in enumerate(data['cats'], 1)]
            elif item.get('@type') == 'Dataset' and filename == 'comparison.html':
                brands = len({c['brand'] for c in data['cats']})
                item['description'] = re.sub(r'of \d+ 3D printers across \d+ brands',
                    f"of {len(data['cats'])} 3D printers across {brands} brands", item['description'])
            return '<script type="application/ld+json">' + json.dumps(item, ensure_ascii=False) + '</script>'
        page = re.sub(r'<script type="application/ld\+json">(.*?)</script>', refresh, page, flags=re.S)
        is_printer = filename == 'comparison.html'
        label = '3D printers' if is_printer else 'filament materials'
        headers = (['Printer', 'Class', 'Street price USD', 'Build volume', 'Max print speed (claimed, mm/s)', 'Max nozzle temp', 'Kinematics']
                   if is_printer else ['Material', 'Family', 'Median price USD/kg', 'Tensile strength', 'HDT at 1.8 MPa', 'Abrasiveness', 'Moisture uptake'])
        rows = []
        for cat in data['cats']:
            spec = lambda field: cat['sp'].get(field, {}).get('v', '—')
            values = ([cat['f'], spec('A4'), spec('B1'), spec('D1'), spec('H2'), spec('C1')]
                      if is_printer else [cat['f'], (cat.get('px') or {}).get('med', '—'), spec('E1'), spec('F2'), spec('C2'), spec('D1')])
            rows.append('<tr><th scope="row">' + escape(cat['n']) + '</th>' + ''.join('<td>' + escape(str(v)) + '</td>' for v in values) + '</tr>')
        fallback = ('<noscript><section id="static"><h2>All ' + str(len(data['cats'])) + ' ' + label + '</h2>'
                    + '<p>Interactive sorting, filtering and comparison need JavaScript. Source dates and prices are snapshots; unsupported fields are shown as —.</p>'
                    + '<table><caption>' + label.capitalize() + ' — summary</caption><thead><tr>'
                    + ''.join('<th scope="col">' + escape(h) + '</th>' for h in headers)
                    + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></section></noscript>')
        page = re.sub(r'<noscript>.*?</noscript>', lambda m: fallback, page, flags=re.S)
        path.write_text(page)
    values = {
        'printers': len(datasets['comparison.html']['cats']),
        'printer-fields': len(datasets['comparison.html']['fields']),
        'materials': len(datasets['filaments.html']['cats']),
        'products': sum(len(c.get('pr', []) ) for c in datasets['filaments.html']['cats']),
    }
    path = ROOT / 'index.html'
    page = path.read_text()
    for key, value in values.items():
        page = re.sub(r'(data-summary="' + key + r'">)\d+', lambda m: m[1] + str(value), page)
    path.write_text(page)
    print(values)


if __name__ == '__main__':
    sync()
