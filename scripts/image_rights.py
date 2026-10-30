"""Image-specific reuse decisions, kept separate from catalog/compilation rights."""
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E = lambda value: escape(str(value), quote=True)


def decisions():
    return json.loads((ROOT / 'data/printer-image-rights.json').read_text())['records']


def license_credit(entry):
    reuse = entry['reuse']
    if not reuse.get('license'):
        return ''
    text = ' · <a class="image-license" href="' + E(reuse['license_url']) + '">' + E(reuse['license']) + '</a>'
    if reuse.get('changes'):
        text += ' · <span class="image-changes">' + E(reuse['changes']) + '</span>'
    return text


def source_photo_link(cid):
    record = decisions().get(cid)
    if not record:
        return ''
    return '<a class="product-photo-source" href="' + E(record['original_source_url']) + '">View product photos <span aria-hidden="true">↗</span></a>'


def validate_reuse(entry):
    reuse = entry.get('reuse', {})
    assert reuse.get('status') in {'licensed', 'publisher-grant', 'no-explicit-restriction-found'}, 'Missing image reuse decision'
    assert all(isinstance(reuse.get(k), str) and reuse[k].strip() for k in ('checked', 'basis_url', 'note', 'changes')), 'Incomplete image reuse basis'
    assert reuse['basis_url'].startswith('https://'), 'Reuse basis must link its source'
    if reuse['status'] in {'licensed', 'publisher-grant'}:
        assert reuse.get('license') and reuse.get('license_url', '').startswith('https://'), 'Reuse grant lacks terms'
    else:
        assert 'license' not in reuse and 'license_url' not in reuse, 'Unverified permission must not be labeled a licence'
