# 3D Printing Info

Static GitHub Pages reference for printer hardware and filament materials. Existing interactive comparisons, family filters, field guides, theme controls and slicer exports are retained. Every material and printer has an individual guide that works without JavaScript.

## Catalog maintenance

The complete JSON in `#payload` in `comparison.html` and `filaments.html` is the catalog source of truth. Edit those objects using a local JSON parser or complete raw/Git files. Never copy catalogs from console excerpts, summaries or truncated API output.

```sh
python3 scripts/sync_site.py
python3 scripts/check_site.py
python3 -m unittest discover -s tests -p 'test_printer_resources.py'
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

Printer and material guides describe technical reference articles using `WebPage` and `TechArticle`; printer subjects use a named `Thing`. The catalog retains `Dataset`, `ItemList` and directory `CollectionPage` metadata. Do not emit nested `Product` markup for these records: Google validates it for Product snippets even when it appears only in an article's `about` property. Historical catalog prices and source notes are not current offers or editorial ratings. Product snippets require a real `offers`, `review` or `aggregateRating` record in addition to the product name; see [Google's Product snippet requirements](https://developers.google.com/search/docs/appearance/structured-data/product-snippet). Static checks audit nested JSON-LD and microdata/RDFa on every content page to prevent recurrence.

After deploying this metadata correction, inspect a printer guide's live URL and check that the unsupported Product item is absent. In the Product snippets issue report, use **Validate fix** if offered and allow Google to recrawl. Product item counts may fall as reference articles stop being reported as product rich-result candidates. This correction does not by itself guarantee indexing or rankings.

### IndexNow deployment notifications

After a successful Pages deployment from `main`, `scripts/notify_indexnow.py` verifies the deployed public key and sends one notification to `https://api.indexnow.org/indexnow`. The public ownership file `c6df70c23c3143feab713134fa94bc0f.txt` belongs at the project root; `keyLocation` explicitly points inside `/3d_printing_info/`, so no host-root file or secret is needed. Only canonical HTML URLs in the old or current sitemap are eligible, and every URL must remain under this project path. See the [IndexNow protocol](https://www.indexnow.org/documentation).

The first notification bootstraps the current sitemap. Later deployments compare Git history with the last acknowledged notification: added/removed sitemap URLs and changed public HTML pages are submitted; source-only, documentation and asset-only changes do not trigger a notification. The exact generated page-revision footer date is ignored when it is the only HTML change; content, source dates and other metadata changes remain eligible. Removed pages are included so participating engines can discover their removal. A cached checkpoint outside the deployed site advances only after HTTP 200/202, or when there are no changed pages. Cache keys identify individual workflow attempts, so a rerun of an older deployment still restores the latest acknowledgment and compares rollback changes, including removed URLs. Provider/key/network errors preserve the checkpoint for retry on the next deployment and produce a warning/report without failing the successful Pages deployment. Cache eviction, unavailable history or an unusable prior sitemap triggers another clearly labeled bootstrap. A checkpoint cannot remember deletions that predate its available history. This is a deployment-driven retry, not a background scheduler.

Each notification writes a GitHub Actions job summary and an `indexnow-notification-<commit>-<attempt>` JSON artifact with the exact URLs, selection mode, commit, response code or error. HTTP 200 acknowledges receipt; HTTP 202 also leaves key validation pending. Neither establishes crawling, indexing, rankings or citations in LLM answers. No automatic POST retries are sent within a run. To intentionally resubmit every current page, dispatch the Pages workflow on `main` with **Resubmit all sitemap URLs** checked; this also deploys the selected commit under the release safeguard below.

The command defaults to a network-free dry run. PR checks use local Git fixtures and mocked responses, so they never notify search engines:

```sh
python3 scripts/notify_indexnow.py --state-file /tmp/indexnow-state/checkpoint.json --report /tmp/indexnow-report.json
python3 -m unittest discover -s tests -p 'test_indexnow.py' -v
```

## Branch and release safeguards

Work in separate branches and draft PRs. **Do not merge or deploy without the owner's explicit approval.** Main automatically deploys to GitHub Pages. After a push, fetch the exact remote commit into a fresh checkout and rerun static checks; inspect the matching commit's Chromium CI result and screenshots. Never declare a PR ready from local tests or matching upload hashes alone.

Configure Pages to deploy with GitHub Actions using `.github/workflows/pages.yml`. Its IndexNow notification runs only after a successful deployment from `main`. The validation workflow has read-only repository permissions and does not deploy or notify search engines.

## Printer guide presentation

All 132 printer guides use a visual model overview, three reading cards, chapter navigation and native expandable specification sections. Firmware options, printable parts, hardware changes and diagnostic routes are interleaved with their matching hardware or workflow topic, rather than appended as a separate resource directory. The full catalog values, qualifiers, variant warnings and individual source references remain in the HTML. On phones, specification rows become stacked reading blocks instead of a wide table. The printer library adds model/brand search and combined printer-group filters; its complete linked model collection remains available without JavaScript.

`scripts/printer_resources.py` loads the model-specific ownership records from `data/printer-resources-*.json`. Each entry explains the change or diagnostic starting point, names its exact model/board/firmware limits, labels the evidence type and links dated primary sources. Official stock firmware, source-build routes, community replacements, stock repair parts and optional upgrades remain explicitly distinguished in the prose. An official troubleshooting procedure is not evidence of failure frequency; owner reports remain labeled. Missing categories are documented as research gaps in the guide’s source notes. Never infer physical fit from a model-hosting site’s supported-printer/profile dropdown. Tag entries with the matching catalog section A–W so the renderer places them beside the relevant specifications. Schema checks reject missing model coverage, duplicate records/keys, invalid provenance and dates, or missing compatibility context.

`scripts/printer_design.py` renders detail pages and the six original architecture illustrations; `scripts/printer_library.py` renders the library. Styles live in `assets/printer-guides.css` and `assets/printer-library.css`; optional library filtering lives in `assets/printer-library.js`. Exact-model product images are mapped separately in `data/printer-images.json`, with local file hashes, dimensions, original image and product-page URLs, credits and check dates. See `assets/printers/README.md` for image provenance. Images retain their manufacturers’ rights; no open license is implied. Models without a verified image use an explicitly labeled general illustration, and library cards use typography. An illustration does not establish a particular model’s appearance or construction.

Update `PRINTER_DATE` in `scripts/sync_site.py` when revising printer presentation. Printer footers and their sitemap entries use that date independently of material and article revisions; source and price dates remain unchanged. The generator does not edit either catalog payload. Static and Chromium checks retain every printer field and source, verify the placement and complete context of every ownership entry, decode every local product image, exercise library filtering and deep comparison links, and check desktop, dark, mobile and no-JavaScript reading.

## Material guide presentation

### Material selection articles

The [professional article plan](docs/material-selection-articles-plan.md) is implemented as seven researched articles: [load-bearing selection](articles/choosing-fdm-material-load-bearing-part.html), [structural composites](articles/pc-cf-pa6-cf-pa12-cf-structural-components.html), [heat under load](articles/heat-resistance-under-load-hdt-tg-annealing.html), [conditioned nylon](articles/nylon-in-service-pa6-pa12-ppa-moisture-conditioning.html), [outdoor components](articles/asa-petg-pc-outdoor-components.html), [creep and stress relaxation](articles/creep-stress-relaxation-fdm-parts.html), and [chemical exposure](articles/selecting-fdm-polymers-chemical-exposure.html). Together with the [article index](articles/index.html), these add eight article URLs to the 220 catalog/reference URLs (**228 content URLs total**). Comparisons narrow where sources do not support a common grade/process/exposure ranking; each article gives concrete next-test recommendations.

`data/article-evidence.json` holds grade-specific supplier measurements and independently consulted experimental/design sources. Each result retains its property definition, method, process, orientation, source locator and reported printing conditions; unknown test conditions stay explicit. `data/material-articles.json` holds the prose and its evidence references. `scripts/material_articles.py` renders both without taking comparison values from the protected catalog. Editorial interpretation is labeled, unspecified ± terms remain unspecified, and the Prusament on-edge XZ coupons are not presented as build-Z tensile results. Separate table groups retain strength definitions, moisture states, impact methods, HDT stresses, annealing states and exposure/control protocols. Chemical observation tables retain categorical findings and explicit concentration, duration, temperature and stress gaps, without converting collapse or unreported change into numeric strength/absorption. Important test context appears beside results and remains readable without JavaScript.

Edit article dates only for substantive article/evidence revisions. The article footer, TechArticle metadata and sitemap use those dates independently of the catalog generator's global revision date. Re-run `python3 scripts/sync_site.py`, `python3 scripts/check_site.py`, `python3 -m unittest discover -s tests -p 'test_article_evidence.py'` and the existing browser suite after changes. Evidence validation checks identities, references, units, conditions and comparison pairs; browser checks include sources, native method disclosures, mobile table scrolling and no-JavaScript access. Source links are not re-fetched during CI; a source revision needs a human/source audit before updating its records.

The [source audit](docs/article-source-audit.md) records conflicting supplier webpage units, conditioning/annealing information, formulation wording, thermal-specimen boundaries, outdoor color/grade gaps and excluded chemical comparisons. The articles use the identified original measurement tables; the protected catalogs are not silently corrected from these findings. Creep and relaxation validation requires the control mode, duration, humidity and imposed load/strain; exposure records retain the duration and applied-stress field even where unknown. All articles follow the release safeguards above: draft PR for review, with no merge or deployment without the owner's explicit approval.

The material library and all 83 detail guides use a visual overview followed by progressive disclosure. Search, family filters and six starting points help readers find a material. Native HTML disclosures retain every property, source and product record without JavaScript; both interactive comparison tables retain their behavior.

Real creator photographs replace the generated spool illustrations. 34 creator-reported examples cover 31 exact material guides, with 30 locally served, unmodified print photos. These include PLA variants, nylon composites, PET/PETG-CF, PCTG, PC/ABS, polypropylene, HIPS, conductive and flexible grades. PEBA, PA6-CF and PC/ABS use model links without assigning an unverified or unsuitable photo; PVA is explicitly a sacrificial-support example, not the finished model body. Each example has a direct Printables link, creator credit, listing license and material evidence. The decorated TPU case is identified as finished/decorated. Other guides show clearly labeled searches on Printables, MakerWorld and Thingiverse, without assigning a related material’s photo to an unverified grade.

`data/print-examples.json` maps each material ID to a list of examples, maintaining the material match, model URL, creator, evidence excerpt, license URL and check date. Optional photos additionally record their source URL, displayed dimensions and SHA-256; downloaded image bytes and metadata remain unchanged. `assets/prints/README.md` documents attribution. To add an example, check the creator’s actual print notes, inspect the photo (not a render), verify reuse terms and record this provenance. Never treat a filament recommendation as proof of the pictured material. Images are served locally, so browsing the guide does not contact model sites until a reader follows a link.

`python3 scripts/sync_site.py` renders examples through `scripts/material_design.py`. `assets/material-guides.css` styles the guides; `assets/material-guides.js` enhances directory filtering. Static checks cover photo hashes/provenance, exact material IDs, discovery links, metadata, anchors and original catalog preservation. Chromium checks decode every curated photo, check their dimensions, links and credits, and exercise desktop/mobile/no-JavaScript navigation plus both comparison tables.

### Applications and engineering context

`data/material-applications.json` supplies the Applications section on each material guide. Connected prose explains established engineering roles, material benefits and relevant limitations. There is no example quota. Documented cases and manufacturer-listed uses are linked when available, with the manufacturing process and material/grade scope stated explicitly.

Molded-resin applications can provide useful context where public FDM examples are sparse. They remain labeled as molding, extrusion, foam or another reported process; their performance, approvals and grade identity must not be transferred to a filament or printed part. A manufacturer application list is labeled separately from a documented component or case study. Every external case retains its primary source title and URL, and the prose cites existing catalog fields plus directly consulted engineering sources.

The 34 existing creator-reported prints and 30 credited photographs remain in the Printed examples section where available. They retain their exact-material evidence and attribution independently from the broader industrial applications.

Static checks validate complete Applications coverage, source references, case provenance and process/grade labels while protecting the original catalogs. Chromium checks every material page, readable mobile and no-JavaScript prose, example links, and the absence of the removed numbered application cards.
