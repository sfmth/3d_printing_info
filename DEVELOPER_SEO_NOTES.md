# SEO Handoff For Generated Table Pages

`comparison.html` and `filaments.html` are generated outside this repo. Do not
patch those output files manually here; add the metadata below to the upstream
HTML generator or template that emits them.

If the site moves to a custom domain, replace every
`https://sfmth.github.io/3d_printing_info/` URL with the production canonical
domain.

## Shared head tags

Add these tags to both generated pages inside `<head>`, after the viewport tag
and before `<title>`:

```html
<meta name="robots" content="index,follow">
<meta name="theme-color" content="#0d0d0d">
<link rel="icon" href="assets/site-icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">
<link rel="manifest" href="site.webmanifest">
<meta property="og:site_name" content="3D Printing Info">
<meta property="og:image" content="https://sfmth.github.io/3d_printing_info/assets/og-card.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://sfmth.github.io/3d_printing_info/assets/og-card.png">
```

## Printer comparison page

Use these page-specific values for `comparison.html`:

```html
<meta name="description" content="Interactive 3D printer comparison for Neptune 4 Pro, Creality K2 SE, Sovol SV06 ACE, FlashForge AD5M, Elegoo Centauri Carbon 2 Combo, and QIDI Q2.">
<link rel="canonical" href="https://sfmth.github.io/3d_printing_info/comparison.html">
<meta property="og:type" content="article">
<meta property="og:title" content="3D Printer Comparison">
<meta property="og:description" content="Six FDM printers compared across hardware, firmware, materials, safety, performance, and ecosystem details.">
<meta property="og:url" content="https://sfmth.github.io/3d_printing_info/comparison.html">
<meta name="twitter:title" content="3D Printer Comparison">
<meta name="twitter:description" content="Six FDM printers compared across hardware, firmware, materials, safety, performance, and ecosystem details.">
<title>3D Printer Comparison | Neptune 4 Pro, K2 SE, SV06 ACE, AD5M, CC2, QIDI Q2</title>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "name": "3D Printer Comparison",
  "url": "https://sfmth.github.io/3d_printing_info/comparison.html",
  "description": "Interactive comparison of six FDM 3D printers across hardware, firmware, materials, safety, performance, and support.",
  "isPartOf": {
    "@type": "WebSite",
    "name": "3D Printing Info",
    "url": "https://sfmth.github.io/3d_printing_info/"
  },
  "primaryImageOfPage": "https://sfmth.github.io/3d_printing_info/assets/og-card.png",
  "about": [
    "3D printer comparison",
    "FDM printer specifications",
    "Klipper 3D printers",
    "3D printing materials support"
  ]
}
</script>
```

## Filament comparison page

Use these page-specific values for `filaments.html`:

```html
<meta name="description" content="Interactive 3D printing filament comparison covering PLA, PETG, ABS, ASA, nylon, TPU, composites, high-temperature polymers, print settings, safety, and prices.">
<link rel="canonical" href="https://sfmth.github.io/3d_printing_info/filaments.html">
<meta property="og:type" content="article">
<meta property="og:title" content="3D Printing Filament Comparison">
<meta property="og:description" content="Compare filament materials by print settings, wear, moisture behavior, mechanical properties, thermal limits, safety, and prices.">
<meta property="og:url" content="https://sfmth.github.io/3d_printing_info/filaments.html">
<meta name="twitter:title" content="3D Printing Filament Comparison">
<meta name="twitter:description" content="Compare filament materials by print settings, wear, moisture behavior, mechanical properties, thermal limits, safety, and prices.">
<title>3D Printing Filament Comparison | Materials, Settings, Safety, Prices</title>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "name": "3D Printing Filament Comparison",
  "url": "https://sfmth.github.io/3d_printing_info/filaments.html",
  "description": "Interactive comparison of 3D printing filament materials by print settings, wear, moisture, mechanical properties, thermal behavior, safety, and prices.",
  "isPartOf": {
    "@type": "WebSite",
    "name": "3D Printing Info",
    "url": "https://sfmth.github.io/3d_printing_info/"
  },
  "primaryImageOfPage": "https://sfmth.github.io/3d_printing_info/assets/og-card.png",
  "about": [
    "3D printer filament",
    "PLA PETG ABS ASA nylon TPU",
    "filament print settings",
    "3D printing material properties"
  ]
}
</script>
```

## Body polish

The generated pages can optionally add a small home link in their existing
header bars:

```html
<a href="./" aria-label="3D Printing Info home">Home</a>
```

Keep the generated table UI as the main first screen. Avoid adding a landing
section above the interactive controls.
