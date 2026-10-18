# 3D Printing Info

Static GitHub Pages reference for printer hardware and filament materials. Existing interactive comparisons, family filters, field guides, theme controls and slicer exports are retained. Every material and printer has an individual guide that works without JavaScript.

## Catalog maintenance

The complete JSON in `#payload` in `comparison.html` and `filaments.html` is the catalog source of truth. Edit those objects using a local JSON parser or complete raw/Git files. Never copy catalogs from console excerpts, summaries or truncated API output.

```sh
python3 scripts/sync_site.py
python3 scripts/check_site.py
```

The sync command derives homepage totals, WebPage/Dataset/ItemList metadata, fallback tables, every `materials/<catalog-id>.html` and `printers/<catalog-id>.html` guide, both directories, store-brand shortcuts and the sitemap from the catalogs. Generated files are committed so GitHub Pages has no runtime build dependency. Update `DATE` in `scripts/sync_site.py` when revising generated content; it is a page revision date, not a replacement for existing source or price dates. The check command fails on stale generated output. The rollback integrity manifest remains unchanged; `data/catalog-checkpoint.json` also protects all records from main commit `089a5708fd4689068e10f4792002969fdbc21a3e`. Category specifications and every existing product/source object must remain intact. Product lists may grow and derived `px` summaries may be recalculated. Both manifests are checked against complete Git objects when history is available.

The restored baseline contains 130 printers, 82 material categories and 394 products. Subsequent additions include two printers, PEBA/eSUN PEBA-90A and 20 retail filament listings: **132 printers, 83 materials, 415 filament products, 57 filament brands, 151 printer fields**. Counts are checked against the payloads rather than maintained manually. The catalog generates **215 detail pages: 83 material guides and 132 printer guides**, plus the two directories and three main pages (220 content URLs). Each guide renders every known catalog field with its source links and dates; this does not imply a new audit of historical specifications.

### US store filament additions (accessed 2026-10-17)

- **Inland / Micro Center — 11 lines:** PLA Basic, PLA, PLA+, Matte PLA, Silk PLA, PLA-CF, PETG, PETG+, PETG-CF, ABS and ASA. The source URLs select Tustin, CA; the pages listed local stock.
- **Cookiecad / Micro Center — 3 lines:** PLA Mint Green, TPU 95A Pixie Dust and PETG Pixie Dust. Store snapshots are Tustin, CA and Madison Heights, MI, as recorded per product.
- **Insignia / Best Buy — 6 lines:** PLA, PLA+, Matte PLA, Silk PLA, PETG and ABS. The pages listed pickup at Roseville or Sterling. PLA and PLA+ prices are unknown because their pages combined amounts with expired promotional dates. Other displayed amounts are recorded as listing prices; inconsistent compare-at text is not used as a regular price.

Each added product has a `retail` object with retailer, location, access date, source IDs, spool mass and price components (retailer original/reference amounts are separate from the listed price). These are dated examples, not a live inventory feed or a comprehensive list of every color. Brand shortcuts use `filaments.html?brand=Inland` and preserve the regular filtering/comparison views. Original product records are retained verbatim. Inland PETG tolerance is unfilled because its page conflicts; generic ABS copy on the ASA page is not treated as ASA data. Unclear Inland/Insignia TPU hardness grades are omitted; Cookiecad explicitly identifies TPU95A. No OEM/rebranding equivalence is assumed. Linear mm/s figures are kept in notes and never used as mm³/s flow.

## Data definitions

- Unknown values remain absent in JSON and display as `—` or `·`. Do not add a zero for an unknown.
- Preserve source type (`vendor`, `tds`, review/test, etc.), individual dates, test conditions, grade and printed orientation. Manufacturer tests are not independent measurements.
- Prices are USD snapshots with sale/from/regular qualifiers, configuration, spool mass and shipping/tax conditions. A compare-at price is not automatically launch MSRP. Older prices have not been rechecked by this rebuild.
- Printer dimensions retain their stated axis order in the text. FDM toolhead/print speed in mm/s and resin vertical speed in mm/h use separate fields. The printer table displays full text/qualifiers for numeric fields whose unit was only embedded in the original text.
- Shore A, Shore D and Rockwell hardness are separate scales. Hardness is displayed and sorted as scale-specific text, with no numeric best/worst ranking. Original numeric source values are preserved in the catalog objects.
- PEBA's 9 mm³/s manufacturer spiral-vase result is volumetric flow; 25–110 mm/s is linear speed. Its TDS mechanical specimens used 2 mm³/s. Inequalities in numeric cells retain their operator (for example, `>16.5` tensile and `>520` elongation); full units and test conditions remain in tooltips and detail views. Bounds, including historical product records that contain a numeric summary, are excluded from exact-value sorting, best/worst highlighting and manufacturer spreads. The `>` tensile figures remain lower bounds rather than exact numeric values. eSUN's nominal 90A designation is not converted to Shore D. Vicat is not HDT.
- Material-guide summaries reuse the sourced catalog; they are not a fresh audit of the 82 legacy materials. Family/representative-grade values must not be treated as measurements for every listed spool.

## Repeatable browser verification

```sh
npm ci --ignore-scripts
npx playwright install --with-deps chromium
npm run test:browser
```

The test serves a clean checkout under `/3d_printing_info/`, matching the production project URL. It checks real Chromium rendering, both interactive tables, search, family filtering, sorting, two-printer/material comparisons, hardness handling, field guides, theme, PEBA slicer export, product prices, material-page navigation, all material and printer URLs, mobile layout, missing assets/errors and complete no-JavaScript tables. It writes screenshots plus `test-results/browser-results.json`, including the exact tested commit. The PR validation workflow runs these checks and uploads the evidence. It checks out the PR head SHA, not an unrecorded local tree or only an upload hash.

Analytics is intercepted in browser tests to avoid test pageviews in production. Tests assert a single loader request and config queue entry, not successful external script execution or data receipt. Material-page source links and identifiers are statically validated; every external historical source is not re-fetched by CI.

## Analytics and Google Search

Every content page has one GA4 loader/config for `G-12FDG0Z8JB`. After an approved deployment:

1. Confirm the ID belongs to the intended Analytics web stream. With blockers disabled and any consent requirements satisfied, open each guide and check the network request for `gtag.js` and GA collection requests. Use Analytics **Realtime/DebugView** to verify actual receipt. Tags and test mocks cannot establish ingestion.
2. In Search Console, use the URL-prefix property `https://sfmth.github.io/3d_printing_info/`, submit `sitemap.xml` and inspect the homepage, both comparisons, a material guide and a printer guide. Check live URL rendering, Google-selected canonical, indexing status and coverage.
3. Read Search Console's Performance report for impressions, clicks and queries. Missing Analytics data does not establish missing Google Search traffic.
4. `robots.txt` in this project directory is a useful declaration but crawler rules are actually controlled by `https://sfmth.github.io/robots.txt` at the host root. Check that host-root file, HTTP status and `X-Robots-Tag` after deployment. A sitemap and crawlable HTML support discovery; they do not guarantee indexing or ranking.

## Branch and release safeguards

Work in separate branches and draft PRs. **Do not merge or deploy without the owner's explicit approval.** Main automatically deploys to GitHub Pages. After a push, fetch the exact remote commit into a fresh checkout and rerun static checks; inspect the matching commit's Chromium CI result and screenshots. Never declare a PR ready from local tests or matching upload hashes alone.

The existing `.github/workflows/pages.yml` deployment workflow is unchanged. Configure Pages to deploy with GitHub Actions. The added validation workflow has read-only repository permissions and does not deploy.

## Material guide presentation

The material library and all 83 detail guides use a visual overview followed by progressive disclosure. Search, family filters and six starting points help readers find a material. Native HTML disclosures retain every property, source and product record without JavaScript; both interactive comparison tables retain their behavior.

Real creator photographs replace the generated spool illustrations. 34 creator-reported examples cover 31 exact material guides, with 30 locally served, unmodified print photos. These include PLA variants, nylon composites, PET/PETG-CF, PCTG, PC/ABS, polypropylene, HIPS, conductive and flexible grades. PEBA, PA6-CF and PC/ABS use model links without assigning an unverified or unsuitable photo; PVA is explicitly a sacrificial-support example, not the finished model body. Each example has a direct Printables link, creator credit, listing license and material evidence. The decorated TPU case is identified as finished/decorated. Other guides show clearly labeled searches on Printables, MakerWorld and Thingiverse, without assigning a related material’s photo to an unverified grade.

`data/print-examples.json` maps each material ID to a list of examples, maintaining the material match, model URL, creator, evidence excerpt, license URL and check date. Optional photos additionally record their source URL, displayed dimensions and SHA-256; downloaded image bytes and metadata remain unchanged. `assets/prints/README.md` documents attribution. To add an example, check the creator’s actual print notes, inspect the photo (not a render), verify reuse terms and record this provenance. Never treat a filament recommendation as proof of the pictured material. Images are served locally, so browsing the guide does not contact model sites until a reader follows a link.

`python3 scripts/sync_site.py` renders examples through `scripts/material_design.py`. `assets/material-guides.css` styles the guides; `assets/material-guides.js` enhances directory filtering. Static checks cover photo hashes/provenance, exact material IDs, discovery links, metadata, anchors and original catalog preservation. Chromium checks decode every curated photo, check their dimensions, links and credits, and exercise desktop/mobile/no-JavaScript navigation plus both comparison tables.

### Application examples and material selection

Every one of the 83 material guides contains five explained application examples (415 in total), maintained in `data/application-examples.json`. Each entry states the part's job, why the material fits, the practical advantage and a relevant tradeoff. Its `fields` reference exact entries in that material's sourced catalog; the guide renders those values, their units, source links and dates in a native disclosure. Additional directly consulted sources can be attached in `external_sources`.

These are reasoned application ideas, not a claim that 415 builds were independently verified. A `print_url` can label a documented print only when it exactly matches a creator record for the same material in `data/print-examples.json`. All 34 existing creator reports retain their links, credits, photos and evidence, and have a corresponding material-choice explanation among the five cards. The explanations are our analysis rather than an attributed statement of the creator's intent.

Grade boundaries matter: conductive PLA and TPU, filled and unfilled nylon, foamed grades, support formulations, and FR/ESD products are kept distinct. Sparse categories such as PA66 and PA-aramid explicitly present conditional design studies and the lack of validated FDM data. A suggested application is not a certification, printed-part property test, or suitability guarantee.

Static validation enforces complete material coverage, five distinct titles per material, populated explanations, valid field/source links and verified build associations. Chromium checks every rendered card on all 83 guides, mobile layout and no-JavaScript access to the explanations and evidence.
