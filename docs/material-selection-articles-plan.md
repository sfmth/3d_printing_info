# Professional material-selection articles

Status: planned; audience and subject priorities confirmed by the owner on 2026-10-18.

## Purpose and scope

Create separate comparison and selection articles for professional and industrial material selection. Begin with strength, stiffness, impact, creep, heat, UV, chemical exposure and moisture. The primary scope is FDM/FFF parts. Injection-molded, extruded-stock and other industrial applications can explain material choices where printed-part evidence is sparse, with the manufacturing process and exact grade identified.

Retain the existing material guides, their Applications sections, creator print examples and complete catalogs. Articles should connect material properties to design decisions rather than repeat all specifications. Keep the visual presentation restrained: readable prose, useful comparison tables, direct source links and conditional conclusions. Article length and examples follow the available evidence; there is no content quota.

## Initial article set

| Order | Working title | Decision and intended coverage |
| --- | --- | --- |
| 1 | Choosing an FDM material for a load-bearing part | Distinguish stiffness, yield, rupture, impact and deflection. Relate build orientation and load path to candidate selection. Begin with documented grades of PLA, PETG, ASA and PC, and explain when those candidates should give way to engineering polymers. |
| 2 | PC-CF vs PA6-CF vs PA12-CF for structural components | Compare specific short-fiber filament grades using stiffness, cross-layer behavior, impact, moisture conditioning and the printing conditions required to achieve the reported properties. Extend to other composites only where appropriate evidence is available. |
| 3 | Heat resistance under load: HDT, Tg, annealing and service temperature | Explain what each measurement supports when selecting hot fixtures, housings and tooling. Compare grades and processes under their stated loads, conditioning and annealing state; identify where creep data or continuous-use evidence are still needed. |
| 4 | Nylon in service: PA6, PA12 and PPA after moisture conditioning | Compare dimensional change and retained strength/stiffness in service. Distinguish drying filament for processing from conditioning a finished part. Include unfilled and fiber-filled grades as separate measurements. |
| 5 | ASA vs PETG vs PC for outdoor components | Compare specified weathering/UV exposure, mechanical retention, appearance, heat and moisture effects. Identify UV-stabilized grades and avoid transferring their behavior to an entire polymer family. |
| 6 | Creep and stress relaxation in FDM parts | Support screening of brackets, fastened joints and fixtures under sustained load. Present time-dependent evidence with stress, environment and orientation attached, and explain what is missing before estimating service life. |
| 7 | Selecting FDM polymers for chemical exposure | Start from named chemicals and exposure conditions. Evaluate candidate grades of PP, PVDF, POM, PA, PC and relevant high-performance polymers such as PPS or PEEK when supported. Distinguish immersion, environmental stress cracking, permeation and retained mechanical performance. |

This is a research backlog, not a promise that every family has comparable measurements. Source gaps may narrow an article or change its candidate list. Creep and chemical selection must remain bounded by the evidence available.

## Evidence standard

Build a separate article evidence dataset rather than copying catalog family scores into comparison tables. Reopen the original sources and record the exact passage, table or figure supporting each measurement and recommendation.

Each measurement record should preserve:

- Exact commercial grade, manufacturer, base polymer, filler identity/content when reported, and manufacturing process.
- Measured property and definition: distinguish yield, ultimate and break strength; tensile and flexural modulus; test method and notched/unnotched impact results.
- Test standard and revision when reported, specimen geometry, test rate, temperature and conditioning.
- Specimen orientation using the source's actual axis/raster definition, plus relevant printing, annealing and post-processing conditions when reported. A supplier's axis label must not silently become another supplier's orientation convention.
- Source title, publisher/authors, document version/date, access date, stable URL and a precise locator for the result.
- Sample count, scatter and uncertainty when reported. Missing information stays explicit; no invented confidence score.

Creep records additionally need stress/load, duration, temperature, humidity/conditioning, measured strain or compliance and specimen orientation. Stress-relaxation measurements retain their fixed-strain context. Environmental records need exposure method, chemical/concentration or weathering conditions, duration, applied stress and retained properties.

Keep three distinctions visible near the result: printed versus molded/stock specimens; manufacturer tests versus independent measurements; measured findings versus engineering interpretation. Use peer-reviewed experimental work, manufacturer technical documents and documented application cases according to the claim they actually support. A case study can establish that a material was used in a component without establishing a general design value.

Direct numerical rankings require comparable definitions and conditions. Separate incompatible measurements instead of averaging them. A bound remains a bound; an unknown remains unknown. Short tests do not establish years of service. Molded-grade data do not supply FDM design allowables. Where a choice remains conditional, state what specific measurement or component test would resolve it.

### Existing-data audit required

The catalog remains a source index and navigation aid. Its legacy qualitative creep summaries sometimes combine printed-part observations, general polymer explanations and molded-compound evidence. Some fiber-filled nylon summaries cite PA66-CF30 molding-compound data as context, and the ASA entry explicitly notes a missing printed creep test. These summaries are not a common-condition comparison dataset.

Re-audit sources for the articles independently. Record discrepancies and proposed catalog corrections separately for owner review; do not silently rewrite protected catalog records or transfer a result to another matrix or process.

## Article experience

Use an `articles/` directory with a concise index grouped by mechanical performance and service environment. Each article should provide:

1. A short opening answer stating the decision, relevant conditions and supported conclusion.
2. A comparison table where the data are actually comparable, with units, grade and essential conditions visible. Use separate groups where methods differ.
3. Connected engineering explanation of the mechanisms and practical advantages/tradeoffs.
4. Linked application examples when they illuminate the decision, with the actual manufacturing process and material scope stated.
5. Adjacent claim citations, a readable methods/source section, known evidence gaps and the verification needed for a proposed use.

The structure can vary with the topic. Do not force identical headings, example counts or repeated disclaimers onto every article. Use plots only when the underlying data support their axes and comparisons. Tables and conclusions must remain available without JavaScript; important conditions should not be available only in hover tooltips.

Link each article to relevant material guides and the existing comparison tool. Add contextual links from the relevant guides and a clear route from the homepage. Use stable section anchors, accurate canonical URLs and WebPage/TechArticle metadata. Show real authorship and content revision information without invented credentials or implying that old measurements were freshly retested. Extend the sitemap and validators for article URLs; preserve the Product-schema correction.

## Delivery sequence

### M1: Evidence model and pilot

Define and validate the article evidence records, source locators and process/condition labels. Research article 1, write its engineering argument, and build the article template and index around that actual content. Verify readability on desktop, mobile and without JavaScript. Deliver a draft PR with the article, its evidence and validation for review.

### M2: Structural and thermal comparisons

Complete articles 2 and 3 using the reviewed evidence model and presentation. Add the relevant links to material guides and the comparison interface. Report unresolved comparability gaps alongside the conclusions; do not turn missing data into a family ranking.

### M3: Service environment and long-term behavior

Complete conditioned nylon and outdoor articles, then creep/stress-relaxation and chemical exposure. Let evidence availability determine the depth of quantitative comparisons. Provide explicit, useful next-test recommendations where reliable selection cannot be completed from public data.

### M4: Final review and maintenance

Check every quantitative conclusion against its source and conditions; verify that inferences are identifiable and no catalog specification, source or existing example was lost. Extend static checks for evidence references, units, article links, anchors, metadata and sitemap coverage, and browser checks for article navigation, tables and mobile/no-JavaScript access. Confirm deployment-generated IndexNow notifications select the added or substantively changed article URLs.

Use separate branches and draft PRs under the repository's existing release safeguards. Revise article dates only when their substantive content or evidence changes. Future maintenance should follow source revisions and corrections rather than regenerate superficially fresh pages.

## Completion criteria

The completed series has a navigable article index and the seven researched articles, or a documented narrower scope where the source audit shows that a proposed comparison is unsupported. The pilot is the first reviewable release. Readers can trace every engineering comparison to the grade, process, test conditions and source. The existing reference site continues to work, automated checks pass on the exact remote commit, and the resulting content is useful to professional readers independently of any search-engine outcome.
