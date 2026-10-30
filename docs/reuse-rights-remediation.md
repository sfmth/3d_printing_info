# Reuse-rights remediation — 29 October 2026

This change implements the owner's instruction to retain pictures where no explicit applicable reuse restriction was established, and to meet explicit licence conditions or use alternatives elsewhere. It resolves the earlier audit's website-code findings; it does not convert unverified images into licensed works or remove older copies from Git history, external caches or an already-published deployment.

| Audit finding | Implemented response |
| --- | --- |
| Product images with explicit restrictions or unclear scope of an explicit licence | 30 exact-model replacements under verified CC/publisher terms; 82 original architecture-diagram fallbacks with external product-photo links. Superseded local image files are removed from the current tree. |
| No explicit applicable image-reuse restriction established | 17 originals retained under the owner's stated policy. Records explicitly preserve uncertainty and policy-access/scope limits; no open licence or affirmative permission is asserted. |
| Conditional Top3DShop reproduction grant | 3 original images retained and 26 replacement images published with conspicuous adjacent credit, ordinary source-page links, terms links, modification notices and preserved visible marks. |
| CC-licensed replacement photos | Bambu A1 and Prusa MINI+ under CC0; Bambu P1S and LulzBot TAZ Pro under CC BY-SA 4.0. Full-image transformations and source/creator/licence notices accompany every display. |
| Printables uploader incorrectly called both photo and model author | All 34 examples identify the listing uploader; known original/remix credits are separate. Unknown photographers are not invented. |
| Noncommercial, ShareAlike and NoDerivatives photo conditions | Individual terms remain attached to each image. Site remains noncommercial; no ads, affiliate links or photo sales were added. All 29 retained photo files preserve their original bytes; display uses contain rather than cropping, including the ND example. |
| Octonauts underlying-franchise uncertainty | Hosted Fish Biscuit photograph and photo metadata removed; source model/material report remains an external link with its limitation recorded. |
| Immediate GA4 load with no privacy notice or choice | Basic opt-in gate on every page; no Google script/config/request before a grant or after persistent decline. Advertising consent stays denied. Withdrawal disables collection, removes accessible analytics cookies and reloads to unload Google code. |
| Missing hosting/storage/Google processing disclosure | New privacy page, footer links and settings; explains GitHub IP logging, local consent storage, optional Analytics, external links and limits of withdrawal. |

## Review evidence and maintenance

- `data/printer-images.json` version 2 contains 50 displayed product photos with source, credit, byte hash, dimensions, date and individual reuse basis. `data/printer-image-rights.json` covers every one of the 132 catalog models, including prior sources and dispositions. No orphan printer WebP remains publicly served by the current tree.
- [Top3DShop terms §11](https://top3dshop.com/terms) provide the publisher grant. This is distinct from a Creative Commons licence and is not independent verification of every upstream copyright claim. Product-photo badges do not become editorial awards or site endorsements.
- [Printables terms §§2.1–2.6](https://www.prusa3d.com/page/terms-of-service-of-printables-com_231249/) include related images in uploader-licensed Printing Documents. Current individual listing panels were access-limited; original check dates remain unchanged. `assets/prints/README.md` explains the selected-licence basis and conditions.
- [Analytics terms §7](https://marketingplatform.google.com/about/analytics/terms/us/) require the disclosure; [Google's basic consent mode](https://developers.google.com/tag-platform/security/concepts/consent-mode) keeps remote collection blocked before consent. The website code does not audit Analytics account-side retention, sharing or linked products, and withdrawal does not delete previously received data.
- Numerical catalog facts, source dates, article evidence and all 132 printer/83 material/415 product records are preserved. No third-party firmware, model or manual archive was added.

Static checks enforce reuse metadata, visible licence/change notices, source-photo links and removal of orphan product photos. Tests cover rejection of invented licences, Printables attribution roles and per-image conditions, real Chromium image decoding/full-image display, consent defaults, grant, withdrawal, cross-tab updates, blocked storage and no-JavaScript access. Generated pages and the privacy page total 229 sitemap URLs.

This remediation is prepared on a separate branch for draft-PR review. The repository's release safeguard requires owner approval before merge or deployment; successful tests alone do not establish that a published site has changed.
