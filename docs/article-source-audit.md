# Article source audit

Accessed 2026-10-18. This records discrepancies and evidence boundaries found while researching the seven material-selection articles. All existing catalog payloads, source objects and product records remain unchanged. These observations are not automatic catalog corrections: a correction must first reconcile the exact grade, document version, property and specimen process.

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

## Conditioned nylon: uptake, dimensions and mechanics

- V5.4 is printed on the cover and remains linked by the manufacturer wiki. No publication date is printed; CDN timestamp is not a publication date. A search also surfaced a V5.5 distributor copy, but no opened current primary V5.5 source was found. Preserve the exact accessed revision and null document date; do not call V5.4 the newest edition. Source: [PolyMide CoPA Technical Data Sheet V5.4](https://cdn.shopify.com/s/files/1/0548/7299/7945/files/PolyMide_CoPA_TDS_V5.4.pdf?v=1731960892); PDF cover; current manufacturer wiki TDS link.
- The mechanical footnote supplies 48 h drying without temperature. The general filament recommendation supplies 100 °C for 8 h. They are distinct statements and cannot be combined into a 100 °C/48 h test procedure. Series keep the test drying temperature unknown and the recommendation separate. Source: [PolyMide CoPA Technical Data Sheet V5.4](https://cdn.shopify.com/s/files/1/0548/7299/7945/files/PolyMide_CoPA_TDS_V5.4.pdf?v=1731960892); PDF p. 4 dry mechanical footnote versus p. 5 general drying recommendation.
- The source describes PA6/66 copolymer without declaring fiber reinforcement. Complete additive composition is not disclosed, so the fragment qualifies its unreinforced grouping and leaves filler null. Use no-fiber-declared wording; do not state pure PA6 or a quantified filler-free composition. Source: [PolyMide CoPA Technical Data Sheet V5.4](https://cdn.shopify.com/s/files/1/0548/7299/7945/files/PolyMide_CoPA_TDS_V5.4.pdf?v=1731960892); PDF p. 2 formulation description.
- The TDS mechanical values numerically match the product dry flexural entries and name ISO 178 / GB/T 9341. The wet page values have no stated method or exposure. Numerical agreement does not justify assigning the TDS settings, unannealed state or absorption environment to the wet page group. Page series contain only page-assigned preparation; method, annealing and wet exposure are explicitly unknown. Source: [Bambu Filament PPA-CF Technical Data Sheet V1.0](https://cdn.shopify.com/s/files/1/0584/7236/6216/files/Bambus_PPA-CF_Technical_Data_Sheet_2ab26420-79f5-4692-888e-090006814050.pdf?v=1724815044), [Bambu PPA-CF product page: Parameters Comparison](https://bambulab-eu.myshopify.com/products/ppa-cf); TDS pp. 2–3; product Parameters Comparison and testing-sample note.
- The source calls 1.30% an absorption rate. It is a percentage attached to 25 °C / 55% RH, with no time basis, so it is not a kinetic uptake rate. Absorption method, duration and geometry are absent. Article calls it uptake, not uptake speed, and does not derive swelling or mechanical retention from it. Source: [Bambu Filament PPA-CF Technical Data Sheet V1.0](https://cdn.shopify.com/s/files/1/0584/7236/6216/files/Bambus_PPA-CF_Technical_Data_Sheet_2ab26420-79f5-4692-888e-090006814050.pdf?v=1724815044), [Bambu PPA-CF product page: Parameters Comparison](https://bambulab-eu.myshopify.com/products/ppa-cf); TDS p. 2 physical table; Parameters Comparison absorption row.
- Product lists dry/saturated XY tensile strength 70/60 MPa and water absorption 2.50%, whereas TDS gives tensile stress at break 72 MPa and absorption 2.59%. Test state and strength definition cannot be aligned. Both omit the moisture exposure. Do not merge numbers into one grade test series or rank against other suppliers. Ask the supplier for a controlled current revision and matched conditioning. Source: [Siraya Tech Fibreheart PPA Filament](https://siraya.tech/products/siraya-tech-fibreheart-ppa-3d-printing-filament), [Siraya Tech Fibreheart PPA TDS](https://siraya.tech/pages/siraya-tech-fibreheart-ppa-filament-tds); Product Key Material Properties; HTML TDS Property Data.
- Both pages suggest possible annealing and separately discourage annealing because of distortion; neither supplies the actual test-specimen annealing route. Preserve as unresolved. Do not recommend a generic PPA anneal or assume the reported properties are annealed. Source: [Siraya Tech Fibreheart PPA Filament](https://siraya.tech/products/siraya-tech-fibreheart-ppa-3d-printing-filament), [Siraya Tech Fibreheart PPA TDS](https://siraya.tech/pages/siraya-tech-fibreheart-ppa-filament-tds); Product Printing Considerations; TDS Preparing for Printing.
- Tables use Max labels and include an aggregate total. Sample count, exposure, nominal-to-measured reference definition and measurement method are unreported. Image filename dates do not establish a page publication date. Use a qualitative illustration only; extract no universal scale factors or family ranking. Source: [Moisture Conditioning](https://wiki.polymaker.com/printing-tips/post-processing/moisture-conditioning); Before/after cube image tables and adjacent prose.

## Outdoor exposure: shared protocols and grade limits

- All quantitative tables were checked against original sources: Stratasys UV WP PDF pp. 7 and 9, ASA MDS PDF p. 14 and PC MDS PDF p. 9 visually rendered locally; Amza Table 2 reopened. Local source PDFs are /tmp/material-outdoor-stratasys-uv.pdf, /tmp/material-outdoor-stratasys-asa.pdf and /tmp/material-outdoor-stratasys-pc.pdf.
- Stratasys ASA color discrepancy is explicit: paragraph says natural, Table 8 says ivory. No equivalence is assumed between every other ASA color.
- PC White identity comes from the newer PC MDS UV section; the older shared UV report says PC. Its UV stabilization/coating is not stated, so do not call it definitively unstabilized or use it to reject all PC.
- Shared Stratasys WP supplies conditioning not repeated in the individual MDS UV tables; source locators and the shared-protocol claim make that support explicit. Lamp type and irradiance remain null.
- ASA/PC UV-table uncertainty is not supplied. Do not borrow standard deviations from their unrelated baseline mechanical tables.
- ASA color Plaque 1 ΔE 9.23 versus Plaque 2 0.86 is intentionally retained; a generic minor-color-change statement or average would obscure this discrepancy. The source’s printed ΔE equation appears suspect in text extraction; only published table outputs are transcribed, no ΔE is recalculated.
- Amza methods report 24 h total UV and three 8 h UV plus 4 h lamp-off cycles. The exposure record preserves UV-on time and cycle description; it does not label elapsed chamber time as 24 h. The paper’s approximation to months outdoors is not adopted.
- PETG tensile build orientation is not explicit in the text; raster ±45° is recorded with printing, not silently converted to XY or build-Z. Filler identity is not reported, so null is retained for all filament series.
- The catalog is untouched. No common ASA/PETG/PC family UV ranking, confidence score or outdoor-life extrapolation is supplied. PETG and supplier ASA/PC groups have different tensile endpoints and protocols.
- Makrolon 2407 and Makrolon AG2677 with coating are contextual industrial resin/system examples, not FFF measurements or transferred approvals. Covestro brochure PDF p. 25 was visually rendered for coating and substrate context.
- ASTM G151-26 active public page was reopened; the current edition replaces G151-19. Only public scope/significance text is used, not an inaccessible full standard.

Primary sources: [Impact of UV Exposure on FDM Materials](https://www.stratasys.com/siteassets/resources/white-papers/whitepaper-uv-exposure-fdm-3d-printing-materials.pdf?v=49ed76), [ASA FDM Thermoplastic Filament Material Data Sheet](https://www.stratasys.com/siteassets/materials/materials-catalog/fdm-materials/asa/mds_fdm_asa_0925a.pdf?v=4ab3e6), [PC (Polycarbonate) FDM Material Data Sheet](https://www.stratasys.com/siteassets/materials/materials-catalog/fdm-materials/pc/polycarbonate-mds-0825a.pdf?v=4a2d80), [Makrolon 2407 product description](https://solutions.covestro.com/en/products/makrolon/makrolon-2407_000000000086286874), [High optical quality polycarbonates: For automotive interior, exterior and lighting](https://solutions.covestro.com/-/media/covestro/solution-center/brochures/pdf/optical-portfolio_brochure_en_v9.pdf?rev=2640738cbb914e4685f5926cd4d09a56), [ASTM G151-26: Standard Practice for Exposing Materials in Accelerated Test Devices that Use Laboratory Light Sources](https://store.astm.org/g0151-26.html), [ASTM D1435-20: Standard Practice for Outdoor Weathering of Plastics](https://store.astm.org/d1435-20.html), [Accelerated Aging Effect on Mechanical Properties of Common 3D-Printing Polymers](https://pmc.ncbi.nlm.nih.gov/articles/PMC8659210/).

## Creep and stress relaxation: control mode and finite endpoints

- Reused existing fischbach-2023 and amza-2021 source records unchanged. New creep series records the known 10 N load, 170 h duration, approximate 20 °C temperature, 30–50% RH and 5 h initial specimen age. Machine-axis and raster-to-load-axis definitions are not explicit, so orientation stays null; the reported line pattern is retained separately.
- Fischbach §4.2 compares its final creep modulus with a supplier quasi-static flexural modulus. That ratio is excluded: it is not a tested universal creep factor, a retained tensile strength or a service-life prediction. The paper’s broad component-transfer claims in §5 are not adopted.
- The newly opened Liber-Kneć/Łagan original PDF is downloadable at the cited mdpi-res.com URL. PDF p. 14 Table 5 was visually inspected; the PLA_100 raw-stress values are 43.53 ± 1.54 MPa and 36.80 ± 3.33 MPa. §2.2.4 explicitly defines standard deviation and five samples per case.
- Liber-Kneć/Łagan uses σ∞ for a measured one-hour residual stress. Article labels it by finite duration. No digitization, normalized retained fraction, equilibrium extrapolation or family-wide rank is introduced. Hydrated rows and mass-normalized columns are omitted; their normalization description is ambiguous in §2.2.1.
- The source spelling MarketBot SKETCH and reported UltiMaker Cura Cloud V5.2 are preserved rather than silently corrected. Table 1’s bottom/top layer thickness wording is unusual relative to the stated 0.2 mm infill layer height; it is reproduced as wording, not converted into invented layer counts. The 5 mm/min static tensile speed is not assigned to the unreported relaxation strain ramp.
- The paper’s PLA_25 maximum relaxation stress exceeds its own Table 2 ultimate-strength mean; the reduced-infill rows are not used here. The one selected PLA_100 cohort has no such cross-table inconsistency, but independent replication remains preferable for design use.
- Bertocco et al. (2022), https://pmc.ncbi.nlm.nih.gov/articles/PMC9147248/, was opened as an alternative primary FDM fixed-strain source. Its σ(t)/ε0 is called creep modulus by the authors, although the control mode is relaxation; its approximate pooled decay figures are excluded in favor of the tabulated measured endpoints above.
- Amza §3.4 describes removal torque in N·m as clamping-force reduction. The article deliberately calls it removal torque, and does not turn the estimated torque-derived initial load into measured preload retention or stress-relaxation data.
- Catalog audit remains separate: legacy creep summaries can include general polymer explanations and PA66-CF30 molded-compound context. Those are not matched printed-grade measurements for PA6-CF, PA12-CF or PPA-CF. Preserve catalog records; no creep ranking or cross-process numerical transfer is made in this article. ASA printed-part creep evidence remains a documented gap.

Primary sources: [Effect of Mass Reduction of 3D-Printed PLA on Load Transfer Capacity—A Circular Economy Perspective](https://mdpi-res.com/d_attachment/materials/materials-18-03262/article_deploy/materials-18-03262.pdf).

## Chemical exposure: bounded observations and excluded comparisons

- Chemical scope is intentionally narrower than a common-condition family ranking: Prusament provides plotted mechanical observations and Apium qualitative compatibility. No curves are digitized and no collapsed/unmeasurable coupon is assigned zero retained strength.
- Prusament chemical article (2021-10-18) separates exact-grade printed experiments from an indicative family chart mixing measurements and literature. The latter is not copied as a measured ranking. Missing acetone concentration/time-to-collapse, endpoint counts, scatter, drying/recovery and applied exposure stress remain explicit. PC Blend nonbreak Charpy controls are bounds, not exact maximum impact values.
- Apium identifies P Series printers in a separate XPS section, not explicitly for immersion coupons. The article therefore does not assign that printer to the chemical series. Its no-change observations lack detection limits and published retained tensile endpoints; fluid labels such as brake fluid do not identify compositions. Prose24.5°C/table24°C discrepancy is retained.
- Arkema Kynar resin fuel-retention data do not identify specimen fabrication/test method; they are not assigned a fictional molding/extrusion/FFF process or used as printed design values. Permeation guidance remains distinct from printed-wall leakage.
- BCN3D PP GF30, Ensinger TECAFORM AH natural (POM-C stock) and TECATRON natural (extruded PPS stock) supply candidate/application guidance rather than named-liquid qualification for a printed component. No stock-to-filament or filled-to-unfilled transfer is made.
- Kaptan (2025), DOI10.3390/polym17121637, was opened as a potential eight-material immersion comparison and excluded from quantitative article evidence. Table1 names PETG-X/Prusa and BVOH Blend/Fillamentum while labeling the latter PVB. Those grade/chemistry identities require reconciliation before transferring any measured family result to a commercial filament. No conclusion about the cause of these discrepancies is asserted.
- ISO175:2010 public scope was rechecked: confirmed2026, externally unrestrained whole-surface immersion, ESC outside scope. No source experiment is relabeled ISO175-compliant merely because it uses immersion.

Primary sources: [Chemical resistance of 3D printing materials](https://prusament.com/chemical-resistance-of-3d-printing-materials/), [Chemical Resistance of FFF 3D Printed PEEK Parts](https://apiumtec.com/en/am-case-study/chemical-resistance-of-peek), [ISO 175:2010 — Plastics — Methods of test for the determination of the effects of immersion in liquid chemicals](https://www.iso.org/standard/55483.html), [Chemical Resistance & Fuel Resistance](https://hpp.arkema.com/cms/render/live/en/sites/hpp_extremematerials_arkema/home/product-families/kynar-fluoropolymer-family/chemical-resistance-fuel-resistance.html), [PP GF30 BCN3D Filaments](https://bcn3d.com/product/pp-gf30-bcn3d-filaments/), [TECAFORM AH natural — POM-C unfilled](https://www.ensingerplastics.com/en/shapes/acetal-tecaform-ah-natural), [TECATRON natural — PPS unfilled](https://www.ensingerplastics.com/en-us/shapes/tecatron-natural).

## Integration review

- Reused Fiberon numeric measurements are unchanged. All twelve dry/wet series now explicitly retain exposure method, duration, applied exposure stress and humidity; unknowns remain null. The measured immersion temperature/duration and annealing context are retained. Repeated annealing numbers and auxiliary formulation/protocol notes remain in full method records; the stated annealing history and essential exposure conditions stay adjacent to the result.
- Independent source checks reconfirmed the new nylon, weathering, creep/relaxation and chemical observations. Creep prose specifies continuing deformation through the end of the loaded hold, without implying a post-unload observation. Unfilled PA6/PA12 are linked as candidate guides with the missing matched evidence explicitly stated.
- The excluded Kaptan2025 comparison also reports conflicting bath volumes in §§2.2–2.3 and mixes ASTM D256/Izod terminology with a Charpy tester. These discrepancies require clarification; no results or family recommendations were imported. Prusament’s nine-liquid protocol list omits acetone while its material-specific results discuss acetone, reinforcing the explicit unknown concentration and collapse time.
