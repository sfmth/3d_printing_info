"""Deterministic page revisions, distinct from research and catalog source dates.

The comparison-navigation panels were published on 2026-11-05 (Pacific).
Freeze that release's paths explicitly: adding a future curated comparison must
not silently assign this historical date to a previously untouched page.
"""

from datetime import date


COMPARISON_NAVIGATION_RELEASE = '2026-11-05'
COMPARISON_NAVIGATION_PATHS = frozenset({
    'materials/abs.html',
    'materials/asa.html',
    'materials/pa12.html',
    'materials/pa12-cf.html',
    'materials/pa6.html',
    'materials/pa6-cf.html',
    'materials/pc.html',
    'materials/pc-cf.html',
    'materials/petg.html',
    'materials/pla.html',
    'printers/bambu-a1.html',
    'printers/bambu-a1-mini.html',
    'printers/bambu-p1s.html',
    'printers/bambu-x1c.html',
    'printers/creality-ender-3-v3-se.html',
    'printers/creality-k1c.html',
    'articles/choosing-fdm-material-load-bearing-part.html',
    'articles/pc-cf-pa6-cf-pa12-cf-structural-components.html',
    'articles/heat-resistance-under-load-hdt-tg-annealing.html',
    'articles/nylon-in-service-pa6-pa12-ppa-moisture-conditioning.html',
    'articles/asa-petg-pc-outdoor-components.html',
    'articles/creep-stress-relaxation-fdm-parts.html',
    'articles/selecting-fdm-polymers-chemical-exposure.html',
})


def page_revision(path, content_revision):
    """Return a page's latest recorded revision without changing evidence dates.

    ``content_revision`` is the existing article or guide revision. A later
    substantive revision wins over this navigation-only release. Paths outside
    the explicit release inventory, including comparison pairs and indexes,
    retain their own revision.
    """
    original = date.fromisoformat(content_revision)
    navigation = (date.fromisoformat(COMPARISON_NAVIGATION_RELEASE)
                  if path in COMPARISON_NAVIGATION_PATHS else original)
    return max(original, navigation).isoformat()
