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
- PEBA's 9 mm³/s manufacturer spiral-vase result is volumetric flow; 25–110 mm/s is linear speed. Its TDS mechanical specimens used 2 mm³/s. The `>` tensile figures remain lower bounds rather than exact numeric values. eSUN's nominal 90A designation is not converted to Shore D. Vicat is not HDT.
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

Real creator photographs replace the generated spool illustrations. Seven exact-material examples (PLA, PETG, ASA, ABS, TPU 95A, PC and PC-CF) have direct Printables model links, credits, listing licenses and creator-reported material evidence. The decorated TPU case is identified as finished/decorated. Other guides show clearly labeled searches on Printables, MakerWorld and Thingiverse, without assigning a related material’s photo to an unverified grade.

`data/print-examples.json` maintains the material match, model URL, creator, evidence excerpt, photo source URL, license URL, check date, dimensions and SHA-256 of each unmodified downloaded thumbnail. `assets/prints/README.md` documents attribution. To add an example, check the creator’s actual print notes, inspect the photo (not a render), verify reuse terms and record this provenance. Never treat a filament recommendation as proof of the pictured material. Images are served locally, so browsing the guide does not contact model sites until a reader follows a link.

`python3 scripts/sync_site.py` renders examples through `scripts/material_design.py`. `assets/material-guides.css` styles the guides; `assets/material-guides.js` enhances directory filtering. Static checks cover photo hashes/provenance, exact material IDs, discovery links, metadata, anchors and original catalog preservation. Chromium checks decode all seven photos, check their dimensions, links and credits, and exercise desktop/mobile/no-JavaScript navigation plus both comparison tables.
