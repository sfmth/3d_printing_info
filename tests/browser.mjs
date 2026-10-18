/** Real Chromium integration checks. Serve under the GitHub Pages project prefix.
 * Analytics is intercepted: we verify the loader request/config queue, not ingestion.
 */
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import { execFileSync } from 'node:child_process';
const root = path.resolve(new URL('..', import.meta.url).pathname);
const prefix = '/3d_printing_info/';
const catalog = async name => JSON.parse((await fs.readFile(path.join(root,name),'utf8')).match(/<script[^>]*id="payload"[^>]*>([\s\S]*?)<\/script>/)[1]);
const printers = await catalog('comparison.html'), materials = await catalog('filaments.html');
const examples = Object.fromEntries(Object.entries(JSON.parse(await fs.readFile(path.join(root,'data/print-examples.json'),'utf8'))).map(([id,entries])=>[id,Array.isArray(entries)?entries:[entries]]));
const applications = JSON.parse(await fs.readFile(path.join(root,'data/material-applications.json'),'utf8'));
const productCount = materials.cats.reduce((n,c)=>n+c.pr.length,0);
const mime = {'.html':'text/html; charset=utf-8','.css':'text/css','.js':'application/javascript','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.gif':'image/gif','.webp':'image/webp','.xml':'application/xml','.webmanifest':'application/manifest+json'};
const server = http.createServer(async (req,res) => {
  try {
    let pathname = decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    if (!pathname.startsWith(prefix)) { res.writeHead(404); return res.end(); }
    let target = path.resolve(root, pathname.slice(prefix.length));
    if (!target.startsWith(root+path.sep) && target!==root) { res.writeHead(403); return res.end(); }
    if ((await fs.stat(target)).isDirectory()) target = path.join(target,'index.html');
    res.setHeader('content-type',mime[path.extname(target)] || 'text/plain');
    res.end(await fs.readFile(target));
  } catch { res.writeHead(404); res.end(); }
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base = `http://127.0.0.1:${server.address().port}${prefix}`;
await fs.mkdir(path.join(root,'test-results'),{recursive:true});
let browser;
const steps=[];
const step = (message) => { steps.push(message); console.log('PASS',message); };
try {
  browser = await chromium.launch();
  const context = await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
  let loads=0; const errors=[], missing=[];
  await context.route('https://**/*', async route => {
    if (route.request().url().startsWith('https://www.googletagmanager.com/gtag/js')) {
      loads++; await route.fulfill({contentType:'application/javascript',body:'/* Analytics loader intercepted by integration test. */'});
    } else await route.abort();
  });
  const page = await context.newPage();
  page.on('pageerror',error=>errors.push(error.message));
  page.on('response',r=>{if(r.url().startsWith(base) && r.status()>=400) missing.push(r.url());});
  async function referenceMetadata() {
    return page.locator('script[type="application/ld+json"]').evaluateAll(scripts=>{
      const documents=scripts.map(script=>JSON.parse(script.textContent));
      const types=[];
      function walk(value) {
        if (!value || typeof value!=='object') return;
        const declared=value['@type'] || [];
        types.push(...(Array.isArray(declared)?declared:[declared]));
        Object.values(value).forEach(walk);
      }
      documents.forEach(walk);
      return {documents,types:types.map(type=>type.replace(/\/$/,'').split(/[/:]/).pop())};
    });
  }
  async function visit(file) {
    await page.waitForLoadState('networkidle');
    const before=loads;
    const response=await page.goto(base+file,{waitUntil:'networkidle'});
    assert.equal(response.status(),200,file);
    assert.equal(loads-before,1,`one Analytics loader request: ${file}`);
    assert.equal(await page.locator('script[src*="googletagmanager.com/gtag/js"]').count(),1);
    assert.equal(await page.evaluate(()=>window.dataLayer.filter(x=>x[0]==='config' && x[1]==='G-12FDG0Z8JB').length),1);
    assert.ok(!(await referenceMetadata()).types.includes('Product'),`no unsupported Product markup: ${file}`);
  }
  await visit('');
  for (const [key,n] of Object.entries({printers:printers.cats.length,'printer-fields':printers.fields.length,materials:materials.cats.length,products:productCount})) {
    for (const s of await page.locator(`[data-summary="${key}"]`).allTextContents()) assert.equal(Number(s),n);
  }
  await page.screenshot({path:path.join(root,'test-results/home.png')});
  await page.getByRole('link',{name:'Printers',exact:true}).click();
  await page.locator('#mtbody tr.row').first().waitFor({state:'visible'});
  assert.equal(await page.locator('#mtbody tr.row').count(),printers.cats.length);
  step('Homepage catalog counts and printer navigation');
  await page.getByLabel('Search printers',{exact:true}).fill('Photon P1 Max');
  assert.equal(await page.locator('#mtbody tr.row').count(),1);
  await page.locator('input.selbox').check();
  await page.getByLabel('Search printers',{exact:true}).fill('Photon Mono M7 Max');
  assert.equal(await page.locator('#mtbody tr.row').count(),1);
  await page.locator('input.selbox').check();
  await page.locator('button[data-view="compare"]').click();
  assert.equal(await page.locator('#cmpout table thead th').count(),3);
  assert.match(await page.locator('#cmpout').innerText(),/15–25 mm\/h/);
  assert.match(await page.locator('#cmpout').innerText(),/≤31 mm\/h/);
  assert.match(await page.locator('#cmpout').innerText(),/2026-10-17/);
  await page.screenshot({path:path.join(root,'test-results/printer-compare.png')});
  await page.locator('#cmpclear').click();
  assert.match(await page.locator('#cmpout').innerText(),/Pick printers/);
  await page.locator('button[data-view="materials"]').click();
  await page.getByLabel('Search printers',{exact:true}).fill('');
  await page.locator('#famchips button[data-f="RESIN"]').click();
  assert.equal(await page.locator('#mtbody tr.row').count(),printers.cats.filter(c=>c.f==='RESIN').length);
  await page.locator('#famchips button[data-f="RESIN"]').click();
  const first=await page.locator('#mtbody tr.row').first().getAttribute('data-id');
  await page.locator('#mthead th[data-k="name"]').click();
  assert.notEqual(await page.locator('#mtbody tr.row').first().getAttribute('data-id'),first);
  await page.locator('#theme').click();
  assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
  await page.locator('#scalesbtn').click();
  assert.equal(await page.locator('#legendpanel').isVisible(),true);
  await page.locator('#gq').fill('price');
  assert.match(await page.locator('#legend').innerText(),/snapshot/);
  await page.locator('#lpclose').click();
  step('Printer search, family filtering, sorting, two-printer comparison, sources, field guide and theme');
  await visit('comparison.html');
  await page.getByLabel('Search printers',{exact:true}).fill('Photon P1 Max');
  await page.locator('#mtbody a.guide-link').click();
  assert.match(page.url(),/printers\/anycubic-photon-p1-max.html$/);
  assert.equal(await page.locator('h1').innerText(),'Anycubic Photon P1 Max');
  await page.screenshot({path:path.join(root,'test-results/printer-guide.png')});
  await page.getByRole('link',{name:'Open in interactive comparison',exact:true}).click();
  await page.locator('#mtbody tr.row.open').waitFor({state:'visible'});
  assert.match(page.url(),/comparison\.html#anycubic-photon-p1-max$/);
  assert.equal(await page.locator('#mtbody tr.row.open').count(),1);
  assert.equal(await page.locator('#q').inputValue(),'Anycubic Photon P1 Max');
  await page.locator('.site-nav').getByRole('link',{name:'Printer guides',exact:true}).click();
  assert.match(page.url(),/printers\/$/);
  await page.getByRole('heading',{name:'Printer guides',exact:true}).waitFor({state:'visible'});
  assert.equal(await page.locator('main li a').count(),printers.cats.length);
  step('Printer detail-page round trip and complete crawlable printer directory');
  await visit('filaments.html');
  assert.equal(await page.locator('#mtbody tr.row').count(),materials.cats.length);
  await page.getByLabel('Search materials and products',{exact:true}).fill('PEBA');
  assert.equal(await page.locator('#mtbody tr.row').count(),1);
  await page.locator('#presets button').filter({hasText:/^Mechanical$/}).click();
  for (const [field,expected] of [['E1','>16.5'],['E3','>520']]) {
    const index=await page.locator(`#mthead th[data-k="${field}"]`).evaluate(th=>th.cellIndex);
    const cell=page.locator('#mtbody tr.row[data-id="peba"] > td').nth(index);
    assert.equal(await cell.innerText(),expected,'qualified numeric value stays compact');
    assert.match(await cell.getAttribute('title'),/printed XY.*GB\/T 1040/);
    assert.match(await cell.getAttribute('title'),/lower bound/);
  }
  await page.screenshot({path:path.join(root,'test-results/peba-numeric-bounds.png')});
  await page.locator('input.selbox').check();
  await page.getByLabel('Search materials and products',{exact:true}).fill('TPU 95A');
  await page.locator('input.selbox').first().check();
  await page.locator('button[data-view="compare"]').click();
  assert.equal(await page.locator('#cmpout table thead th').count(),3);
  const hardness=page.locator('#cmpout tr').filter({has:page.locator('td.fn').filter({hasText:'Hardness (scale-specific)'})});
  assert.equal(await hardness.count(),1);
  assert.equal(await hardness.locator('td.best').count(),0);
  assert.match(await hardness.innerText(),/Shore A/);
  const pebaCompareColumn=await page.locator('#cmpout thead th').filter({hasText:'PEBA'}).evaluate(th=>th.cellIndex);
  for (const field of ['Tensile strength (XY)','Elongation at break']) {
    const row=page.locator('#cmpout tr').filter({has:page.locator('td.fn').filter({hasText:field})});
    assert.match(await row.locator('td').nth(pebaCompareColumn).innerText(),/lower bound/);
    assert.equal(await row.locator('td').nth(pebaCompareColumn).getAttribute('class'),'','lower bounds are never highlighted as exact best values');
  }
  await page.locator('#cmpclear').click();
  await page.locator('button[data-view="products"]').click();
  await page.getByLabel('Search materials and products',{exact:true}).fill('');
  assert.equal(await page.locator('#ptbody > tr').count(),productCount);
  await page.getByLabel('Search materials and products',{exact:true}).fill('PEBA');
  assert.equal(await page.locator('#ptbody > tr').count(),1);
  assert.match(await page.locator('#ptbody').innerText(),/From \$60.99/);
  for (const [field,expected] of [['E1','>16.5'],['E3','>520']]) {
    const index=await page.locator(`#pthead th[data-k="${field}"]`).evaluate(th=>th.cellIndex);
    const cell=page.locator('#ptbody > tr > td').nth(index);
    assert.equal(await cell.innerText(),expected);
    assert.match(await cell.getAttribute('title'),/lower bound/);
  }
  await page.locator('button[data-view="materials"]').click();
  await page.locator('#mtbody tr.row .full').click();
  assert.match(await page.locator('#mtbody tr.detail').innerText(),/9 mm³\/s/);
  const downloading=page.waitForEvent('download');
  await page.locator('#mtbody button[data-prof="dl"][data-prod="-1"]').click();
  const downloaded=await downloading;
  const profile=JSON.parse(await fs.readFile(await downloaded.path(),'utf8'));
  assert.deepEqual(profile.filament_type,['PEBA']);
  assert.deepEqual(profile.filament_max_volumetric_speed,['9']);
  await page.screenshot({path:path.join(root,'test-results/peba-table.png')});
  await page.locator('#mtbody a.guide-link').click();
  assert.match(page.url(),/materials\/peba.html$/);
  assert.match(await page.locator('h1').innerText(),/PEBA/);
  await page.getByRole('link',{name:'Open in interactive comparison',exact:true}).click();
  await page.locator('#mtbody tr.row.open').waitFor({state:'visible'});
  assert.equal(await page.locator('#mtbody tr.row').count(),1);
  assert.equal(await page.locator('#q').inputValue(),'PEBA (polyether block amide)');
  assert.equal(await page.locator('#mtbody tr.row.open').count(),1);
  step('Material and product filtering, mixed-hardness comparison, price qualifiers, profile export and material-guide round trip');
  const storeProducts=materials.cats.flatMap(c=>c.pr.filter(p=>p.retail));
  for (const brand of [...new Set(storeProducts.map(p=>p.b))]) {
    await visit('filaments.html');
    await page.locator('#retail-brands summary').click();
    await page.locator('#retail-brands').getByRole('link',{name:brand,exact:true}).click();
    await page.locator('#v-products').waitFor({state:'visible'});
    const expected=storeProducts.filter(p=>p.b===brand);
    assert.equal(await page.locator('#q').inputValue(),brand);
    assert.equal(await page.locator('#ptbody > tr').count(),expected.length);
    for (const p of expected) {
      const row=page.locator('#ptbody > tr').filter({has:page.getByRole('link',{name:p.p,exact:true})});
      assert.equal(await row.count(),1,p.p);
      assert.ok((await row.innerText()).includes(p.retail.checked),p.p);
      assert.equal(await row.locator('a').first().getAttribute('href'),p.u);
      assert.ok((await row.innerText()).includes(p.pn),p.p);
    }
    if (brand==='Inland') await page.screenshot({path:path.join(root,'test-results/retail-filaments.png')});
  }
  await visit('filaments.html?brand=insignia');
  assert.equal(await page.locator('#ptbody > tr').count(),storeProducts.filter(p=>p.b==='Insignia').length);
  await visit('filaments.html?brand=missing-brand');
  assert.equal(await page.locator('#mtbody tr.row').count(),materials.cats.length);
  step('All store-brand shortcuts filter the product table; every new listing retains its retailer link and dated price notes');
  await visit('materials/');
  assert.equal(await page.locator('[data-material]').count(),materials.cats.length);
  assert.equal(await page.locator('.family-group[open]').count(),0);
  assert.equal(await page.locator('.featured-card').count(),6);
  await page.getByLabel('Search material guides',{exact:true}).fill('PEBA');
  assert.equal(await page.locator('[data-material]:not([hidden])').count(),1);
  assert.match(await page.locator('#material-results').innerText(),/^1 of/);
  await page.locator('[data-material="peba"] .material-card-link').click();
  assert.match(page.url(),/materials\/peba.html$/);
  assert.equal(await page.locator('.spec-group[open]').count(),0,'technical tables start collapsed');
  assert.equal(await page.locator('.product-library[open]').count(),0,'product lists start collapsed');
  assert.equal(await page.locator('[data-print-example]').count(),0,'no unrelated photo for PEBA');
  assert.equal(await page.locator('#prints .print-story').count(),(examples.peba || []).length);
  if (examples.peba) assert.ok((await page.locator('#prints').innerText()).includes(examples.peba[0].title));
  else assert.equal(await page.locator('#prints').count(),0);
  assert.equal(await page.locator('#prints .model-search-links a').count(),3);
  await page.screenshot({path:path.join(root,'test-results/material-overview.png')});
  await page.locator('#spec-b > summary').focus();
  await page.keyboard.press('Enter');
  assert.equal(await page.locator('#spec-b').getAttribute('open'),'');
  assert.match(await page.locator('#spec-b').innerText(),/9 mm³\/s/);
  await page.locator('#spec-b .row-sources > summary').first().click();
  assert.ok(await page.locator('#spec-b .row-sources[open] a').count()>0);
  await page.locator('.product-library > summary').click();
  await page.locator('.product-entry > summary').first().click();
  assert.match(await page.locator('.product-entry[open]').innerText(),/From \$60.99/);
  await visit('materials/?family=FLEX');
  assert.equal(await page.locator('[data-material]:not([hidden])').count(),materials.cats.filter(c=>c.f==='FLEX').length);
  assert.equal(await page.locator('button[data-family="FLEX"]').getAttribute('aria-pressed'),'true');
  await page.getByLabel('Search material guides',{exact:true}).fill('no-such-material-xyz');
  assert.equal(await page.locator('#material-no-results').isVisible(),true);
  await page.locator('#clear-material-search').click();
  assert.equal(await page.locator('[data-material]:not([hidden])').count(),materials.cats.length);
  await page.screenshot({path:path.join(root,'test-results/material-library.png')});
  await page.getByLabel('Search material guides',{exact:true}).fill('PLA');
  await page.screenshot({path:path.join(root,'test-results/material-library-filtered.png')});
  step('Material library search/family filters, empty/reset states, keyboard accordions, complete sourced properties and product details');
  for (const [id,entries] of Object.entries(examples)) {
    await visit('materials/'+id+'.html');
    const primary=entries.find(e=>e.image) || entries[0];
    if (primary.image) {
      assert.equal(await page.locator('.print-photo-link').getAttribute('href'),primary.url);
      assert.equal(await page.locator('.print-title').getAttribute('href'),primary.url);
    } else assert.equal(await page.locator('.material-visual img').count(),0);
    assert.equal(await page.locator('#prints .print-story').count(),entries.length);
    for (let i=0;i<entries.length;i++) {
      const e=entries[i],story=page.locator('#prints .print-story').nth(i);
      if (e.image) {
        const photo=e===primary?page.locator('.material-visual img'):story.locator('.example-photo');
        await photo.evaluate(img=>img.decode());
        assert.equal(await photo.getAttribute('alt'),e.alt);
        assert.deepEqual(await photo.evaluate(img=>[img.naturalWidth,img.naturalHeight]),[e.width,e.height]);
      }
      assert.equal(await story.locator('h3 a').getAttribute('href'),e.url);
      await story.locator('.inline-sources > summary').click();
      assert.ok((await story.innerText()).includes(e.evidence));
      assert.ok((await story.innerText()).includes(e.creator));
      assert.ok(await story.locator(`a[href="${e.license_url}"]`).count()>0);
    }
    assert.equal(await page.locator('#prints .model-search-links a').count(),3);
    if(id==='pla')await page.screenshot({path:path.join(root,'test-results/printed-pla-guide.png')});
    if(entries.length>1)await page.screenshot({path:path.join(root,`test-results/printed-${id}-examples.png`),fullPage:true});
  }
  await visit('materials/');
  await page.screenshot({path:path.join(root,'test-results/printed-material-library.png')});
  step(`All ${Object.values(examples).flat().length} creator-reported examples have model links, material evidence and license links; all curated photos decode at recorded dimensions`);
  for (const c of materials.cats) {
    const response=await page.goto(base+'materials/'+c.id+'.html',{waitUntil:'domcontentloaded'});
    assert.equal(response.status(),200,c.id);
    assert.match(await page.locator('h1').innerText(),new RegExp(c.n.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')));
    assert.equal(await page.locator('link[rel="canonical"]').getAttribute('href'),'https://sfmth.github.io/3d_printing_info/materials/'+c.id+'.html');
    const entry=applications[c.id];
    assert.equal(await page.locator('#applications > .section-heading h2').innerText(),'Applications');
    assert.deepEqual(await page.locator('#applications .application-copy > p').allTextContents(),entry.paragraphs,c.id);
    assert.equal(await page.locator('[data-application-example], .application-card').count(),0);
    const cases=await page.locator('[data-engineering-example]').evaluateAll(nodes=>nodes.map(node=>({title:node.querySelector('h3 a').textContent.replace(/ ↗$/,''),text:node.querySelector('p:not(.case-context)').textContent,context:node.querySelector('.case-context').textContent,url:node.querySelector('h3 a').getAttribute('href')})));
    assert.deepEqual(cases,(entry.examples||[]).map(e=>({title:e.title,text:e.text,context:[e.process,e.scope,e.evidence==='case-study'?'Documented case':'Manufacturer-listed applications'].filter(Boolean).join(' · '),url:e.url})),c.id);
  }
  step(`All ${materials.cats.length} material guides render Applications prose, sourced engineering examples and explicit process/grade context, without numbered cards`);
  for(const id of ['pla','peba','pa-aramid','pa66','peek']) {
    await visit('materials/'+id+'.html');
    assert.equal(await page.locator('#applications .application-copy > p').first().isVisible(),true);
    await page.locator('#applications .application-sources > summary').click();
    assert.equal(await page.locator('#applications .application-sources a').first().isVisible(),true);
    await page.locator('#applications').evaluate(el=>el.scrollIntoView({block:'start'}));
    await page.screenshot({path:path.join(root,`test-results/applications-${id}.png`)});
  }
  for (const c of printers.cats) {
    const response=await page.goto(base+'printers/'+c.id+'.html',{waitUntil:'domcontentloaded'});
    assert.equal(response.status(),200,c.id);
    assert.equal(await page.locator('h1').innerText(),c.n);
    assert.equal(await page.locator('link[rel="canonical"]').getAttribute('href'),'https://sfmth.github.io/3d_printing_info/printers/'+c.id+'.html');
    assert.equal(await page.locator('script[src*="googletagmanager.com/gtag/js"]').count(),1);
    const metadata=await referenceMetadata();
    assert.ok(!metadata.types.includes('Product'),c.id);
    const article=metadata.documents.find(document=>document['@type']==='WebPage').mainEntity;
    assert.equal(article['@type'],'TechArticle',c.id);
    assert.equal(article.about['@type'],'Thing',c.id);
    assert.equal(article.about.name,c.n,c.id);
  }
  step(`All ${printers.cats.length} printer guides render technical-article metadata without unsupported Product entities, matching canonical URLs and one Analytics tag`);
  const articlePath='articles/choosing-fdm-material-load-bearing-part.html';
  const articleTitle='Choosing an FDM material for a load-bearing part';
  await visit('');
  await page.getByRole('navigation',{name:'Primary',exact:true}).getByRole('link',{name:'Selection articles',exact:true}).click();
  assert.equal(new URL(page.url()).pathname,new URL(base+'articles/').pathname);
  await visit('articles/');
  assert.ok(await page.locator('[data-article-card]').count()>0,'article hub has a published article');
  await page.screenshot({path:path.join(root,'test-results/article-index.png')});
  await page.locator('a[data-article-card][href="choosing-fdm-material-load-bearing-part.html"]').click();
  assert.equal(new URL(page.url()).pathname,new URL(base+articlePath).pathname);
  await visit(articlePath);
  assert.equal(await page.locator('body.article-page').count(),1);
  assert.equal(await page.locator('main h1').innerText(),articleTitle);
  assert.equal(await page.locator('#quick-answer').isVisible(),true);
  assert.equal(await page.locator('#verification').isVisible(),true);
  const articleMetadata=(await referenceMetadata()).documents.find(document=>document['@type']==='WebPage');
  assert.equal(articleMetadata.url,'https://sfmth.github.io/3d_printing_info/'+articlePath);
  assert.equal(articleMetadata.mainEntity['@type'],'TechArticle');
  assert.equal(articleMetadata.mainEntity.headline,articleTitle);
  assert.ok(articleMetadata.mainEntity.author,'article has identified authorship');
  assert.match(articleMetadata.mainEntity.dateModified,/^\d{4}-\d{2}-\d{2}/);
  const evidenceTable=page.locator('#measurements table.evidence-table');
  assert.equal(await evidenceTable.isVisible(),true);
  assert.ok(await evidenceTable.locator('tr[data-measurement]').count()>=8,'pilot preserves grade-specific measurements');
  const tableText=await evidenceTable.innerText();
  for(const polymer of [/PLA/,/PETG/,/ASA/,/PC/]) assert.match(tableText,polymer);
  assert.match(tableText,/MPa|GPa/,'engineering units are visible in the comparison');
  for(const row of await evidenceTable.locator('tr[data-measurement]').all()) {
    assert.ok((await row.innerText()).trim().length>20,'measurement rows retain readable context');
    assert.ok(await row.locator('a.evidence-link').count()>0,'each measurement links its evidence');
  }
  const claims=page.locator('p[data-evidence-refs]');
  assert.ok(await claims.count()>0,'engineering claims identify their evidence');
  for(const claim of await claims.all()) {
    assert.ok(await claim.locator('a.claim-citation[href^="https://"]').count()>0,'claim has a direct primary-source citation');
    assert.ok(await claim.locator('a.evidence-link[href^="#evidence-"]').count()>0,'claim exposes precise evidence context');
  }
  for(const href of await page.locator('a.evidence-link').evaluateAll(links=>links.map(link=>link.getAttribute('href')))) {
    assert.match(href,/^#evidence-/);
    assert.equal(await page.locator(href).count(),1,'evidence anchor resolves: '+href);
  }
  const methods=page.locator('#methods details[data-series]');
  assert.ok(await methods.count()>0,'test-series conditions are available');
  for(const method of await methods.all()) {
    if(await method.getAttribute('open')===null) await method.locator(':scope > summary').click();
    assert.equal(await method.getAttribute('open'),'');
    assert.ok((await method.innerText()).trim().length>80,'expanded method includes specimen and test context');
  }
  assert.ok(await page.locator('#sources li[data-source]').count()>0);
  for(const source of await page.locator('#sources li[data-source]').all()) {
    assert.ok(await source.locator('a[href^="https://"]').count()>0,'source retains its primary URL');
  }
  await page.locator('#measurements').evaluate(el=>el.scrollIntoView({block:'start'}));
  await page.screenshot({path:path.join(root,'test-results/article-desktop.png')});
  await page.locator('main a[href="../materials/pla.html"]').first().click();
  assert.equal(new URL(page.url()).pathname,new URL(base+'materials/pla.html').pathname);
  await page.locator('#selection-articles a[href="../'+articlePath+'"]').click();
  assert.equal(await page.locator('main h1').innerText(),articleTitle);
  await page.getByRole('navigation',{name:'Primary',exact:true}).getByRole('link',{name:'Material guides',exact:true}).click();
  assert.equal(new URL(page.url()).pathname,new URL(base+'materials/').pathname);
  for(const id of ['pla','petg','asa','pc']) {
    await visit('materials/'+id+'.html');
    assert.equal(await page.locator('#selection-articles a[href="../'+articlePath+'"]').count(),1,id+' links to its selection article');
  }
  await visit('filaments.html');
  await page.getByRole('navigation',{name:'Primary',exact:true}).getByRole('link',{name:'Selection articles',exact:true}).click();
  assert.equal(new URL(page.url()).pathname,new URL(base+'articles/').pathname);
  step('Selection article hub and pilot retain grade-specific evidence, conditions, primary citations, technical-article metadata and material-guide round trips');
  await visit('materials/peba.html');
  await page.screenshot({path:path.join(root,'test-results/peba-guide.png')});
  await page.setViewportSize({width:390,height:844});
  await page.goto(base,{waitUntil:'networkidle'});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'homepage mobile width');
  await page.getByRole('link',{name:'Filaments',exact:true}).click();
  await page.locator('#mtbody tr.row').first().waitFor({state:'visible'});
  await page.getByLabel('Search materials and products',{exact:true}).fill('PEBA');
  assert.equal(await page.locator('#mtbody tr.row').count(),1);
  await page.screenshot({path:path.join(root,'test-results/mobile-filaments.png')});
  await page.goto(base+'materials/peba.html',{waitUntil:'networkidle'});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'guide mobile width');
  assert.equal(await page.locator('#applications').count(),1);
  await page.locator('#applications').evaluate(el=>el.scrollIntoView({block:'start'}));
  await page.screenshot({path:path.join(root,'test-results/mobile-applications.png')});
  await page.screenshot({path:path.join(root,'test-results/mobile-guide.png')});
  await page.goto(base+'materials/pla.html',{waitUntil:'networkidle'});
  await page.locator('.material-visual img').evaluate(img=>img.decode());
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'photo guide mobile width');
  await page.screenshot({path:path.join(root,'test-results/mobile-printed-guide.png')});
  await page.goto(base+'materials/',{waitUntil:'networkidle'});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'material library mobile width');
  await page.screenshot({path:path.join(root,'test-results/mobile-material-library.png')});
  await page.getByLabel('Search material guides',{exact:true}).fill('nylon');
  assert.ok(await page.locator('[data-material]:not([hidden])').count()>0);
  await page.screenshot({path:path.join(root,'test-results/mobile-material-search.png')});
  await page.goto(base+'printers/anycubic-photon-p1-max.html',{waitUntil:'networkidle'});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'printer guide mobile width');
  await page.screenshot({path:path.join(root,'test-results/mobile-printer-guide.png')});
  await visit(articlePath);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'article mobile width');
  const mobileTable=page.locator('#measurements table.evidence-table');
  const scrollState=await mobileTable.evaluate(table=>{
    let wrapper=table.parentElement;
    while(wrapper && !/^(auto|scroll)$/.test(getComputedStyle(wrapper).overflowX)) wrapper=wrapper.parentElement;
    if(!wrapper) return null;
    const original=wrapper.scrollLeft;
    wrapper.scrollLeft=wrapper.scrollWidth;
    const result={width:wrapper.clientWidth,contentWidth:wrapper.scrollWidth,scrolled:wrapper.scrollLeft>original};
    wrapper.scrollLeft=original;
    return result;
  });
  assert.ok(scrollState && scrollState.contentWidth>scrollState.width && scrollState.scrolled,'mobile comparison scrolls inside its own wrapper');
  await page.locator('#measurements').evaluate(el=>el.scrollIntoView({block:'start'}));
  await page.screenshot({path:path.join(root,'test-results/article-mobile.png')});
  await visit('articles/');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'article hub mobile width');
  step('Article hub and evidence table remain readable at 390 px with horizontal scrolling contained inside the comparison');
  step('Mobile navigation, filtering, material and printer guide layouts at 390 px');
  const nojs=await browser.newContext({javaScriptEnabled:false});
  const staticPage=await nojs.newPage();
  await staticPage.goto(base+'comparison.html');
  assert.equal(await staticPage.locator('#static tbody tr').count(),printers.cats.length);
  await staticPage.locator('#static a[href="printers/anycubic-photon-p1-max.html"]').click();
  assert.equal(await staticPage.locator('h1').innerText(),'Anycubic Photon P1 Max');
  assert.equal(await staticPage.locator('main table').count()>0,true);
  await staticPage.getByRole('link',{name:'Open in interactive comparison',exact:true}).click();
  assert.equal(await staticPage.locator('#static tbody tr').count(),printers.cats.length);
  await staticPage.goto(base+'materials/');
  assert.equal(await staticPage.locator('[data-material]').count(),materials.cats.length);
  assert.equal(await staticPage.locator('.material-search').isVisible(),false);
  await staticPage.locator('[data-family-group="PLA"] > summary').click();
  await staticPage.locator('[data-material="pla"] .material-card-link').click();
  assert.equal(await staticPage.locator('#applications .application-copy > p').first().isVisible(),true,'applications readable without JavaScript');
  await staticPage.locator('#applications .application-sources > summary').click();
  assert.equal(await staticPage.locator('#applications .application-sources a').first().isVisible(),true);
  await staticPage.locator('#spec-b > summary').click();
  assert.equal(await staticPage.locator('#spec-b table').isVisible(),true);
  await staticPage.locator('#spec-b .row-sources > summary').first().click();
  assert.ok(await staticPage.locator('#spec-b .row-sources[open] a').count()>0);
  await staticPage.locator('.product-library > summary').click();
  assert.equal(await staticPage.locator('.product-entry').count(),materials.cats.find(c=>c.id==='pla').pr.length);
  step('Material directory, native property accordions, source links and product listings work without JavaScript');
  await staticPage.goto(base+'filaments.html');
  assert.equal(await staticPage.locator('#static > table').first().locator('tbody tr').count(),materials.cats.length);
  assert.equal(await staticPage.locator('#static-products tbody tr').count(),productCount);
  for (const p of storeProducts) {
    const link=staticPage.locator('#static-products').getByRole('link',{name:p.b+' '+p.p,exact:true});
    assert.equal(await link.count(),1,p.p);
    assert.equal(await link.getAttribute('href'),p.u);
  }
  await staticPage.locator('#static a[href="materials/peba.html"]').first().click();
  assert.match(await staticPage.locator('h1').innerText(),/PEBA/);
  assert.equal(await staticPage.locator('main table').count()>0,true);
  step('No-JavaScript tables preserve every printer, material and product; guide links work');
  await staticPage.goto(base);
  await staticPage.getByRole('navigation',{name:'Primary',exact:true}).getByRole('link',{name:'Selection articles',exact:true}).click();
  await staticPage.locator('a[data-article-card][href="choosing-fdm-material-load-bearing-part.html"]').click();
  assert.equal(await staticPage.locator('main h1').innerText(),articleTitle);
  assert.equal(await staticPage.locator('#quick-answer').isVisible(),true);
  assert.equal(await staticPage.locator('#measurements table.evidence-table').isVisible(),true);
  assert.ok(await staticPage.locator('#measurements tr[data-measurement]').count()>=8);
  const staticMethod=staticPage.locator('#methods details[data-series]').first();
  if(await staticMethod.getAttribute('open')===null) {
    await staticMethod.locator(':scope > summary').focus();
    await staticPage.keyboard.press('Enter');
  }
  assert.equal(await staticMethod.getAttribute('open'),'','test conditions expand without JavaScript');
  assert.ok((await staticMethod.innerText()).length>80);
  const staticEvidence=staticPage.locator('p[data-evidence-refs] a.evidence-link').first();
  const evidenceTarget=await staticEvidence.getAttribute('href');
  await staticEvidence.click();
  assert.equal(new URL(staticPage.url()).hash,evidenceTarget);
  assert.equal(await staticPage.locator(evidenceTarget).count(),1);
  assert.equal(await staticPage.locator(evidenceTarget).isVisible(),true,'fragment navigation reveals its evidence record without JavaScript');
  assert.ok(await staticPage.locator('#sources li[data-source] a[href^="https://"]').count()>0);
  assert.equal(await staticPage.locator('#verification').isVisible(),true);
  await staticPage.locator('main a[href="../materials/pla.html"]').first().click();
  await staticPage.locator('#selection-articles a[href="../'+articlePath+'"]').click();
  assert.equal(await staticPage.locator('main h1').innerText(),articleTitle);
  step('Article navigation, comparison values, native method disclosures, evidence anchors and source links work without JavaScript');
  assert.deepEqual(errors,[],'uncaught JavaScript errors');
  assert.deepEqual(missing,[],'missing local assets');
  step('No uncaught JavaScript exceptions or missing local assets');
  const result={commit:execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(),browser:await browser.version(),counts:{printers:printers.cats.length,materials:materials.cats.length,products:productCount,detailPages:printers.cats.length+materials.cats.length},analytics:'One loader request and config per checked page; loader intercepted, ingestion not verified',steps};
  await fs.writeFile(path.join(root,'test-results/browser-results.json'),JSON.stringify(result,null,2)+'\n');
} finally {
  if(browser) await browser.close();
  await new Promise(resolve=>server.close(resolve));
}
