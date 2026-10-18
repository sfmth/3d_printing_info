# Article source audit

Accessed 2026-10-18. This records discrepancies and evidence boundaries found while researching the structural-composite and thermal articles. All existing catalog payloads, source objects and product records remain unchanged. These observations are not automatic catalog corrections: a correction must first reconcile the exact grade, document version, property and specimen process.

## Structural composites

### 1. Fiberon PA12-CF10 annealing duration

TDS specimen protocol specifies 100 °C / 16 h. Product-page FAQ says 100 °C / 10 h.

Use the TDS specimen protocol; record the conflict separately. Do not silently revise catalog records.

Sources: [Fiberon PA12-CF10 technical data sheet](https://fiberon.polymaker.com/wp-content/uploads/TDS_FIBERON-PA12-CF10_V1.1_EN.pdf), [Fiberon PA12-CF10 manufacturer product page](https://fiberon.polymaker.com/product/pa12-cf10/).

Locator: TDS dry/wet footnotes and recommended annealing; product-page annealing FAQ.

### 2. Fiberon store modulus units

Store tables label the raw values 8636.5 and 3311.2 in GPa; original TDS units are MPa.

Use original TDS units and values; do not copy the store unit label into evidence.

Sources: [Fiberon PA6-CF20 technical data sheet](https://fiberon.polymaker.com/wp-content/uploads/TDS_FIBERON-PA6-CF20_V1.1_EN.pdf), [Fiberon PA12-CF10 technical data sheet](https://fiberon.polymaker.com/wp-content/uploads/TDS_FIBERON-PA12-CF10_V1.1_EN.pdf), [Fiberon PA6-CF20 manufacturer store page](https://shop.polymaker.com/products/fiberon-pa6-cf20), [Fiberon PA12-CF10 manufacturer store page](https://shop.polymaker.com/products/fiberon-pa12-cf10).

Locator: Store property-table Young modulus rows versus TDS dry mechanical blocks.

### 3. Fiberon store moisture conflict

Both inspected store FAQs state 2.57% moisture. V1.1 sheets state 5.30% for PA6-CF20 and 2.92% for PA12-CF10 under their wet protocol.

Use grade-specific TDS specimen moisture; no catalog correction made.

Sources: [Fiberon PA6-CF20 technical data sheet](https://fiberon.polymaker.com/wp-content/uploads/TDS_FIBERON-PA6-CF20_V1.1_EN.pdf), [Fiberon PA12-CF10 technical data sheet](https://fiberon.polymaker.com/wp-content/uploads/TDS_FIBERON-PA12-CF10_V1.1_EN.pdf), [Fiberon PA6-CF20 manufacturer store page](https://shop.polymaker.com/products/fiberon-pa6-cf20), [Fiberon PA12-CF10 manufacturer store page](https://shop.polymaker.com/products/fiberon-pa12-cf10).

Locator: Store moisture-conditioning FAQs versus TDS wet mechanical-table footnotes.

### 4. Fiberon PA12-CF10 matrix description

TDS uses a copolyimide term while the manufacturer store calls the matrix a PA12-based long-chain copolyamide.

Identify the marketed commercial grade; preserve the inconsistency and do not infer an exact comonomer recipe.

Sources: [Fiberon PA12-CF10 technical data sheet](https://fiberon.polymaker.com/wp-content/uploads/TDS_FIBERON-PA12-CF10_V1.1_EN.pdf), [Fiberon PA12-CF10 manufacturer store page](https://shop.polymaker.com/products/fiberon-pa12-cf10).

Locator: TDS opening product description; store product-description paragraph.

### 5. Fiberon drawing test labels

The specimen captions repeat ASTM D638 even for flexural and impact drawings. Mechanical tables instead identify ISO 178 for bending and ISO 179 for Charpy.

Use the property-specific mechanical-table methods; do not claim the impact test was ASTM D638.

Sources: [Fiberon PA6-CF20 technical data sheet](https://fiberon.polymaker.com/wp-content/uploads/TDS_FIBERON-PA6-CF20_V1.1_EN.pdf), [Fiberon PA12-CF10 technical data sheet](https://fiberon.polymaker.com/wp-content/uploads/TDS_FIBERON-PA12-CF10_V1.1_EN.pdf).

Locator: Captions above flexural, tensile and impact specimen sketches versus mechanical-table method columns.

### 6. Fiberon product modulus labels

Product-page sections assign some bending and tensile modulus numbers to the opposite labels.

Use the PDF mechanical rows; do not transfer page labels into the comparison.

Sources: [Fiberon PA12-CF10 technical data sheet](https://fiberon.polymaker.com/wp-content/uploads/TDS_FIBERON-PA12-CF10_V1.1_EN.pdf), [Fiberon PA12-CF10 manufacturer product page](https://fiberon.polymaker.com/product/pa12-cf10/).

Locator: Product-page modulus sections versus original TDS dry mechanical block.

## Heat under load

### 1. Conflicting annealing and unloaded heat claims

Official wiki says anneal for 3 minutes at 80–90 °C, while its linked V1.1 PDF p. 5 says 30 minutes. Wiki own-weight stability text says 130 °C; linked PDF p. 2 says 150 °C.

Use pinned PDF measured rows. Neither recommended schedule is asserted to be the schedule behind the annealed HDT result; no own-weight claim is converted to a loaded service temperature.

Sources: [Polymaker HT-PLA Technical Data Sheet](https://cdn.shopify.com/s/files/1/0548/7299/7945/files/Polymaker_HT-PLA_TDS_EN_V1.1.pdf?v=1746635222), [Manufacturer wiki](https://wiki.polymaker.com/polymaker-products/more-about-our-products/documents/technical-data-sheets/pla/ht-pla).

### 2. HDT specimen recipe not identified

PDF p. 6 gives general specimen recipe and tensile/flexural/impact drawings, without an HDT-specific drawing or clear assignment.

HDT-specific printing fields, orientation and geometry remain null. As-printed labels establish printed basis; FFF is supported by filament/layer specimen context.

Sources: [Polymaker HT-PLA Technical Data Sheet](https://cdn.shopify.com/s/files/1/0548/7299/7945/files/Polymaker_HT-PLA_TDS_EN_V1.1.pdf?v=1746635222).

### 3. Prusament thermal and printed-mechanical tables

HDT rows appear in Typical material properties, outside the explicitly 3D-printed mechanical table and its specimen-printing footnote.

No protected catalog edits. These thermal entries were not imported as FFF comparison measurements or assigned tensile coupon conditions.

Sources: [Prusament PETG technical data sheet](https://storage.googleapis.com/prusa3d-content-prod-14e8-wordpress-prusament-prod/2023/10/9f8d2165-tds_prusament-petg_n_en.pdf), [Prusament ASA technical data sheet](https://storage.googleapis.com/prusa3d-content-prod-14e8-wordpress-prusament-prod/2024/05/bc8551ef-tds_prusament-asa_2024_en.pdf), [Prusament PC Blend technical data sheet](https://prusament.com/wp-content/uploads/2022/10/PCBlend_Prusament_TDS_2022_16_EN.pdf).

### 4. Independent ASTM experiment and supplier ISO results

HDT procedure is ASTM D648 at 0.455 MPa with 2 °C/min heating and two tests/type. ISO 75 supplier results are technically distinct.

Retain qualitative mechanism and exact commercial-grade identity; no estimated graph values or cross-method ranking.

Sources: [Improving the Impact Strength and Heat Resistance of 3D Printed Models: Structure, Property, and Processing Correlationships during Fused Deposition Modeling (FDM) of Poly(Lactic Acid)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6641607/).
