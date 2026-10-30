# Printer guide images and reuse decisions

`data/printer-images.json` version 2 contains the 50 product photographs currently displayed. Each record identifies an exact catalog model, its local WebP, original image and source-page URLs, credit, dimensions, SHA-256, review date, and an image-specific `reuse` decision. `data/printer-image-rights.json` records a disposition for all 132 catalog models and retains the original source/hash and applicable policy references, including replaced images.

## Current decisions — reviewed 2026-10-29

- **4 explicitly licensed replacements:** Bambu Lab A1 (CC0), P1S with optional AMS (CC BY-SA 4.0), Prusa MINI+ (CC0), and LulzBot TAZ Pro (CC BY-SA 4.0). The TAZ Pro photo was extracted from PDF page 4 of the manufacturer's 2023 Quick Start Guide; the guide's licence appears on PDF page 53. No manual PDF is bundled. The credit, source, licence and changes accompany both guide and library displays. Any adaptation of a ShareAlike photo remains under that same licence; the site's compilation licence does not override it.
- **29 publisher-permitted images:** three retained Top3DShop photos and 26 exact-model replacements. [Top3DShop terms, section 11](https://top3dshop.com/terms) permit image reproduction with conspicuous credit and a do-follow hyperlink to the source page, retained notices, and no implied endorsement. These conditions are preserved in captions. This publisher permission is not a Creative Commons licence and does not represent independent verification of every upstream copyright claim.
- **17 retained with no explicit applicable restriction established:** retained under the owner's instruction. This is not an affirmative grant, public-domain declaration or open licence. The manifest explicitly labels permission as unverified; policy-access and scope limitations remain in the decision record. A copyright notice alone has not been relabeled as permission.
- **82 original diagrams:** where explicit source restrictions or unclear licence scope prevent the current photograph's reuse, the local photo was removed. The guide uses a clearly labeled original architecture illustration and links to the source's product photographs. It never borrows a sibling model's picture. The six diagrams are generic explanatory drawings, not claims about an exact model's construction.

## Credits and transformations

New replacements retain the whole image without cropping or retouching. They are proportionally resized to at most 1200 px and converted to WebP; available embedded EXIF/copyright/profile data are retained for the Commons/manual images. Existing retained photographs may have had blank canvas trimmed, as recorded individually. Publisher marks and promotional badges remain visible; their appearance does not create a site review, award or endorsement claim.

Photographs can show optional AMS/CFS systems, spools, sample prints, enclosures and other accessories. Captions and alt text identify pictured configurations; photos do not establish what every purchasing configuration includes. Commons and manufacturer/publisher photo rights remain separate from the GNU GPL compilation licence. Source links identify provenance and licence evidence, not a blanket permission for unrelated images.

## Maintenance

Before adding a photograph, inspect the exact model and configuration and record its reuse basis. For an explicit licence or publisher grant, retain all required credits, source links, licence notices and change disclosures in both library and guide captions. For a source where no explicit applicable restriction was established, retain that precise uncertainty under the owner's policy and never invent a licence. Use the original diagram and source-photo link when explicit terms cannot be met.

Update image bytes, dimensions, digest and provenance together. Do not infer photo rights from a printer's open-source hardware/software licence. Run `python3 scripts/sync_site.py`, `python3 scripts/check_site.py`, the image-rights unit tests and Chromium browser suite. Validation rejects missing reuse decisions, missing visible licence links and modification notices, and orphaned WebP files that would otherwise remain publicly hosted.
