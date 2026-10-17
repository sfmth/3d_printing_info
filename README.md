# 3d_printing_info

Static GitHub Pages site for 3D printing reference tables.

## Pages

- [Printer comparison](comparison.html)
- [Filament comparison](filaments.html)

## Deployment

This repository deploys to GitHub Pages through `.github/workflows/pages.yml`.
On GitHub, set **Settings -> Pages -> Build and deployment -> Source** to
**GitHub Actions**. Pushes to `main` will publish the site, and the workflow can
also be run manually from the Actions tab.

## Search indexing

The site includes root-level `robots.txt` and `sitemap.xml` files for search
engine discovery. After the Pages deployment is live, add
`https://sfmth.github.io/3d_printing_info/` as a URL-prefix property in Google
Search Console and submit `sitemap.xml`.

## Maintaining the catalog

The tables keep their source-backed data in each page's `payload` JSON script.
Add entries using the existing field IDs, family names and source-reference format.
Keep manufacturer claims separate from measured results; leave unsupported fields
blank. Source dates and prices are snapshots, not a claim that the whole catalog
has been reverified whenever one entry changes.

After editing the catalog, run:

```sh
python3 scripts/sync_summary.py
python3 scripts/check_site.py
```

The first command refreshes homepage totals and structured-data item lists. The
second validates data references, local links, Analytics tags and JavaScript syntax
(requires Node.js). Update sitemap `lastmod` dates only for pages actually changed.

## Analytics and search troubleshooting

All three content pages use the existing GA4 measurement ID `G-12FDG0Z8JB`.
Keep the tag on each HTML page, including pages visitors can enter directly.
Verify this ID matches the intended web data stream in the Analytics account.
An installed tag is not proof that Analytics receives visits: check Realtime or
DebugView after deployment, using a browser without tracking blockers and with
any required consent. Standard reports may take 24–48 hours to process data.
Do not send test traffic from automated regression tests.

Analytics traffic reporting is separate from Google Search indexing. In Search
Console, inspect each canonical URL, verify the rendered content and indexing
status, and submit the sitemap. Search Performance reports show impressions,
clicks and search queries; zero Analytics visits alone cannot diagnose indexing.
A sitemap helps discovery but does not guarantee indexing or rankings.

References:
- [Install the Google tag on every page](https://developers.google.com/tag-platform/gtagjs)
- [Verify Analytics collection](https://developers.google.com/analytics/devguides/collection/ga4/troubleshoot)
- [Google sitemap guidance](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview)
