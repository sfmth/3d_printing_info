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
