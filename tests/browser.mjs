/** Real Chromium integration checks. Serve under the GitHub Pages project prefix.
 * Analytics stays off by default. Consent tests intercept Google's loader/collection, not ingestion.
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
const printerResources = {};
for (const file of (await fs.readdir(path.join(root,'data'))).filter(name=>/^printer-resources-.*\.json$/.test(name))) Object.assign(printerResources,JSON.parse(await fs.readFile(path.join(root,'data',file),'utf8')).models);
assert.deepEqual(Object.keys(printerResources).sort(),printers.cats.map(printer=>printer.id).sort(),'ownership evidence covers the catalog');
const printerPhotos = JSON.parse(await fs.readFile(path.join(root,'data/printer-images.json'),'utf8')).images;
const examples = Object.fromEntries(Object.entries(JSON.parse(await fs.readFile(path.join(root,'data/print-examples.json'),'utf8'))).map(([id,entries])=>[id,Array.isArray(entries)?entries:[entries]]));
const applications = JSON.parse(await fs.readFile(path.join(root,'data/material-applications.json'),'utf8'));
const articles = JSON.parse(await fs.readFile(path.join(root,'data/material-articles.json'),'utf8')).articles;
const siteUpdates = JSON.parse(await fs.readFile(path.join(root,'data/site-updates.json'),'utf8')).entries;
const articleEvidence = JSON.parse(await fs.readFile(path.join(root,'data/article-evidence.json'),'utf8'));
const genericArticles = articles.filter(article=>article.tables);
const productCount = materials.cats.reduce((n,c)=>n+c.pr.length,0);
const pairFile = (kind, ids) => `compare/${kind}/${[...ids].sort().join('-vs-')}.html`;
const pairCases = [
  {kind:'materials',data:materials,ids:['petg','pla'],interactive:'filaments.html'},
  {kind:'printers',data:printers,ids:['bambu-a1','neptune4pro'],interactive:'comparison.html'},
];
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
  await context.addInitScript(() => localStorage.setItem('3dpi.analyticsConsent.v1','denied'));
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
    assert.equal(loads-before,0,`no Analytics loader after decline: ${file}`);
    assert.equal(await page.locator('script[src*="googletagmanager.com/gtag/js"]').count(),0);
    assert.equal(await page.evaluate(()=>(window.dataLayer || []).filter(x=>x[0]==='config').length),0);
    assert.equal(await page.locator('footer [data-analytics-settings]').count(),1);
    assert.equal(await page.locator('script[src$="analytics-consent.js"]').count(),1);
    assert.ok(!(await referenceMetadata()).types.includes('Product'),`no unsupported Product markup: ${file}`);
  }
  async function verifyPair(target, fixture) {
    const {kind,data}=fixture, ids=[...fixture.ids].sort();
    const cats=ids.map(id=>data.cats.find(cat=>cat.id===id));
    assert.ok(cats.every(Boolean),'browser pair fixture exists in catalog');
    assert.equal(await target.locator('body').getAttribute('data-left'),ids[0]);
    assert.equal(await target.locator('body').getAttribute('data-right'),ids[1]);
    const headers=target.locator('#pair-table thead th[scope="col"]');
    assert.equal(await headers.count(),3,'property heading and exactly two item headings');
    for(let index=0;index<2;index++) {
      assert.equal(await headers.nth(index+1).locator('a').innerText(),cats[index].n);
      assert.equal(await headers.nth(index+1).locator('a').getAttribute('href'),`../../${kind}/${ids[index]}.html`);
    }
    const rows=await target.locator('#pair-table tr[data-field]').evaluateAll(nodes=>nodes.map(row=>({
      id:row.dataset.field,different:row.dataset.different,
      cells:[...row.querySelectorAll('td.property-value')].map(cell=>({value:cell.querySelector('.value').textContent,sources:cell.dataset.sources ?? null,missing:cell.classList.contains('missing')})),
    })));
    const expectedFields=data.fields.filter(field=>cats.some(cat=>Object.hasOwn(cat.sp,field.id))).map(field=>field.id);
    assert.deepEqual(rows.map(row=>row.id),expectedFields,'all documented fields survive server rendering');
    const sourceIds=[];
    for(const row of rows) {
      assert.equal(row.cells.length,2);
      const entries=cats.map(cat=>cat.sp[row.id]);
      assert.equal(row.different,String(entries[0]?.v!==entries[1]?.v));
      for(let index=0;index<2;index++) {
        const entry=entries[index], cell=row.cells[index];
        assert.equal(cell.value,entry?.v ?? 'Not documented',`${kind}/${row.id} exact value`);
        assert.equal(cell.sources,entry ? (entry.s || []).join(' ') : null,`${kind}/${row.id} exact source IDs`);
        assert.equal(cell.missing,!entry);
        for(const sid of entry?.s || []) if(!sourceIds.includes(sid))sourceIds.push(sid);
      }
    }
    const sources=await target.locator('#sources li[data-source-id]').evaluateAll(nodes=>nodes.map(node=>({id:node.dataset.sourceId,text:node.textContent,href:node.querySelector('a')?.getAttribute('href')})));
    assert.deepEqual(sources.map(source=>source.id),sourceIds,'one source record for each actually cited document');
    for(const source of sources) {
      const expected=data.src[source.id];
      if(expected.u)assert.equal(source.href,expected.u);
      for(const key of ['t','p','d','k']) if(expected[key])assert.ok(source.text.includes(expected[key]),source.id+' '+key);
    }
    assert.equal(await target.locator('#pair-interactive').getAttribute('href'),`../../${fixture.interactive}?compare=${ids.join(',')}`);
    assert.equal(await target.locator('link[rel="canonical"]').getAttribute('href'),`https://sfmth.github.io${prefix}${pairFile(kind,ids)}`);
    const metadata=await target.locator('script[type="application/ld+json"]').evaluateAll(nodes=>nodes.map(node=>JSON.parse(node.textContent)));
    const declared=[];
    const walk=value=>{if(value && typeof value==='object'){if(value['@type'])declared.push(...[].concat(value['@type']));Object.values(value).forEach(walk);}};
    metadata.forEach(walk);
    assert.ok(declared.includes('WebPage') && !declared.includes('Product') && !declared.includes('Dataset'));
    return rows;
  }
  async function openPairCitation(target) {
    const citation=target.locator('#pair-table a.source-ref').first();
    const href=await citation.getAttribute('href');
    await citation.focus();
    await target.keyboard.press('Enter');
    assert.equal(new URL(target.url()).hash,href);
    assert.equal(await target.locator(href).isVisible(),true,'pair citation reaches its full dated source');
  }
  async function verifyAnalyticsConsent() {
    const consent = await browser.newContext({viewport:{width:390,height:844}});
    const requests = [], consentErrors = [];
    const google = url => /https:\/\/[^/]*(?:google-analytics\.com|googletagmanager\.com)\//.test(url);
    consent.on('request', request => { if(google(request.url())) requests.push(request.url()); });
    consent.on('page', target => target.on('pageerror', error => consentErrors.push(error.message)));
    await consent.route('https://**/*', async route => {
      if(route.request().url().startsWith('https://www.googletagmanager.com/gtag/js')) {
        await route.fulfill({contentType:'application/javascript',body:`
          if (!window['ga-disable-G-12FDG0Z8JB']) {
            document.cookie='3dpi_ga=fixture; path=${prefix}; SameSite=Lax';
            window.__analyticsProbe=()=>window['ga-disable-G-12FDG0Z8JB'] ? undefined : fetch('https://www.google-analytics.com/g/collect?fixture=1');
            window.__analyticsProbe();
          }`});
      } else if(google(route.request().url())) await route.fulfill({status:204,headers:{'access-control-allow-origin':'*'}});
      else await route.abort();
    });
    const target=await consent.newPage();
    async function assertOff(message) {
      await target.waitForLoadState('networkidle');
      assert.equal(await target.locator('script[src*="googletagmanager.com/gtag/js"]').count(),0,message);
      assert.equal(await target.evaluate(()=>(window.dataLayer || []).filter(entry=>entry[0]==='config').length),0,message+' has no config');
      assert.equal(await target.evaluate(()=>window.__analyticsProbe===undefined),true,message+' has no running library');
    }
    await target.goto(base,{waitUntil:'networkidle'});
    await assertOff('Analytics starts off before a choice');
    assert.equal(requests.length,0,'no Google script, collection or consent request before opt-in');
    assert.equal(await target.locator('#analytics-consent').isVisible(),true);
    assert.equal(await target.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'consent controls fit 390px');
    await target.screenshot({path:path.join(root,'test-results/analytics-consent-mobile.png')});
    await target.getByRole('button',{name:'Decline analytics',exact:true}).click();
    assert.equal(await target.evaluate(()=>localStorage.getItem('3dpi.analyticsConsent.v1')),'denied');
    for(const file of ['comparison.html','filaments.html','materials/pla.html','printers/bambu-x1c.html','articles/','privacy.html']) {
      await target.goto(base+file,{waitUntil:'networkidle'});
      await assertOff('Persistent decline on '+file);
      assert.equal(await target.locator('#analytics-consent').isVisible(),false,'decline survives navigation');
      assert.equal(await target.locator('footer [data-analytics-settings]').isVisible(),true,file+' has settings');
      if(file==='privacy.html') {
        await target.getByRole('link',{name:'3D Printing Info',exact:true}).click();
        assert.equal(target.url(),base,'privacy brand returns to the project home');
        await assertOff('Privacy-to-home navigation preserves decline');
      }
    }
    assert.equal(requests.length,0,'declining and navigating sends nothing to Google');
    await target.locator('footer [data-analytics-settings]').click();
    assert.equal(await target.locator('#analytics-settings').isVisible(),true);
    await target.keyboard.press('Escape');
    assert.equal(await target.locator('#analytics-settings').isVisible(),false);
    assert.equal(await target.locator('footer [data-analytics-settings]').evaluate(element=>element===document.activeElement),true,'closing settings restores focus');
    await target.locator('footer [data-analytics-settings]').click();
    // A previously idle document can still report networkidle before the newly
    // inserted async loader executes. Observe the mock's collection response.
    await Promise.all([
      target.waitForResponse(response=>response.url()==='https://www.google-analytics.com/g/collect?fixture=1' && response.status()===204),
      target.locator('#analytics-settings [data-analytics-allow]').click()
    ]);
    assert.equal(requests.filter(url=>url.includes('googletagmanager.com/gtag/js')).length,1,'explicit grant loads one tag');
    assert.equal(requests.filter(url=>url.includes('google-analytics.com/g/collect')).length,1,'mock collection only after grant');
    const queue=await target.evaluate(()=>window.dataLayer.map(entry=>Array.from(entry)));
    const configurations=queue.filter(entry=>entry[0]==='config');
    assert.equal(configurations.length,1,'one config after grant');
    assert.equal(configurations[0][1],'G-12FDG0Z8JB');
    assert.equal(configurations[0][2].allow_google_signals,false);
    assert.equal(configurations[0][2].allow_ad_personalization_signals,false);
    assert.deepEqual(queue.filter(entry=>entry[0]==='consent').map(entry=>[entry[1],entry[2].analytics_storage,entry[2].ad_storage,entry[2].ad_user_data,entry[2].ad_personalization]),[
      ['default','denied','denied','denied','denied'],['update','granted','denied','denied','denied']
    ]);
    await Promise.all([
      target.waitForResponse(response=>response.url()==='https://www.google-analytics.com/g/collect?fixture=1' && response.status()===204),
      target.goto(base+'comparison.html?private=do-not-forward#bambu-x1c',{waitUntil:'networkidle'})
    ]);
    assert.equal(await target.evaluate(()=>window.dataLayer.filter(entry=>entry[0]==='config').length),1,'grant persists on next page');
    assert.equal(await target.evaluate(()=>window.dataLayer.find(entry=>entry[0]==='config')[2].page_location),base+'comparison.html','page location excludes query and fragment');
    assert.equal(requests.filter(url=>url.includes('googletagmanager.com/gtag/js')).length,2);
    await target.evaluate(()=>{document.cookie='_ga=legacy; path=/';document.cookie='unrelated=keep; path=/';});
    const beforeWithdrawal=requests.length;
    await target.locator('footer [data-analytics-settings]').click();
    await Promise.all([target.waitForNavigation({waitUntil:'networkidle'}),target.locator('#analytics-settings [data-analytics-decline]').click()]);
    await assertOff('Withdrawing reloads without the running tag');
    assert.equal(requests.length,beforeWithdrawal,'withdrawal sends no further Google requests');
    const cookies=await consent.cookies();
    assert.ok(!cookies.some(cookie=>/^(?:_ga(?:_|$)|3dpi_ga(?:_|$))/.test(cookie.name)),'withdrawal removes accessible old and current Analytics cookies');
    assert.ok(cookies.some(cookie=>cookie.name==='unrelated'),'withdrawal preserves unrelated cookies');
    await target.goto(base+'materials/pla.html',{waitUntil:'networkidle'});
    await assertOff('Withdrawal persists across navigation');
    assert.equal(requests.length,beforeWithdrawal);
    await target.locator('footer [data-analytics-settings]').click();
    await Promise.all([
      target.waitForResponse(response=>response.url()==='https://www.google-analytics.com/g/collect?fixture=1' && response.status()===204),
      target.locator('#analytics-settings [data-analytics-allow]').click()
    ]);
    await target.locator('footer [data-analytics-settings]').click();
    await target.locator('#analytics-settings [data-analytics-allow]').click();
    assert.equal(await target.evaluate(()=>window.dataLayer.filter(entry=>entry[0]==='config').length),1,'repeated grant does not duplicate config');
    const other=await consent.newPage();
    await Promise.all([
      other.waitForResponse(response=>response.url()==='https://www.google-analytics.com/g/collect?fixture=1' && response.status()===204),
      other.goto(base+'privacy.html',{waitUntil:'networkidle'})
    ]);
    await other.locator('footer [data-analytics-settings]').click();
    const beforeOtherWithdrawal=requests.length;
    await Promise.all([target.waitForNavigation({waitUntil:'networkidle'}),other.waitForNavigation({waitUntil:'networkidle'}),other.locator('#analytics-settings [data-analytics-decline]').click()]);
    await assertOff('Withdrawal in another tab stops an existing grant');
    assert.equal(requests.length,beforeOtherWithdrawal);
    assert.deepEqual(consentErrors,[],'consent flow has no browser errors');
    await consent.close();
    const blocked=await browser.newContext();
    const blockedRequests=[];
    blocked.on('request',request=>{if(google(request.url()))blockedRequests.push(request.url());});
    await blocked.route('https://**/*',route=>route.abort());
    await blocked.addInitScript(()=>Object.defineProperty(window,'localStorage',{get(){throw new Error('Storage unavailable');}}));
    const blockedPage=await blocked.newPage();
    await blockedPage.goto(base,{waitUntil:'networkidle'});
    await blockedPage.locator('[data-analytics-decline]').first().click();
    assert.equal(await blockedPage.locator('#analytics-consent').isVisible(),false,'decline works on the current page when storage is blocked');
    await blockedPage.reload({waitUntil:'networkidle'});
    assert.equal(await blockedPage.locator('#analytics-consent').isVisible(),true,'storage failure returns to unchosen, never granted');
    assert.equal(blockedRequests.length,0);
    await blocked.close();
    step('Analytics sends zero Google requests before consent/after decline; explicit grant, persistent choices, withdrawal/cookie cleanup, cross-tab withdrawal and blocked storage work');
  }
  await verifyAnalyticsConsent();
  async function verifyGenericTables(target, article) {
    assert.equal(await target.locator('table[data-evidence-table]').count(),article.tables.length,article.id);
    for(const table of article.tables) {
      const rendered=target.locator(`table[data-evidence-table="${table.id}"]`);
      assert.equal(await rendered.isVisible(),true,table.id);
      assert.equal(await target.locator('#table-'+table.id).count(),1);
      assert.equal(await rendered.getAttribute('aria-describedby'),'table-'+table.id+'-caption');
      assert.equal(await target.locator('#table-'+table.id+'-caption').innerText(),table.caption);
      if(table.kind==='observations') {
        assert.equal(await rendered.locator('tr[data-observation]').count(),table.rows.length);
        for(const row of table.rows) {
          const shown=rendered.locator(`tr[data-observation="${row.id}"]`);
          const text=await shown.innerText();
          for(const value of [row.grade,row.process,row.orientation,row.conditioning,row.observation,...Object.values(row.exposure)]) {
            assert.ok(text.includes(value===null?'Not reported':value),row.id+' retains observation context');
          }
          const source=articleEvidence.sources[articleEvidence.claims[row.refs[0]].source_id];
          assert.ok(text.toLowerCase().includes(source.kind.replaceAll('-',' ')));
          for(const ref of row.refs) {
            assert.equal(await shown.locator(`a.evidence-link[href="#evidence-${ref}"]`).count(),1);
            assert.ok((await shown.locator('a.claim-citation').allTextContents()).length>0);
            assert.ok((await shown.locator('a.claim-citation').evaluateAll(links=>links.map(a=>a.href))).includes(source.url));
          }
          for(const item of await shown.locator('.result-context').all()) assert.equal(await item.isVisible(),true);
        }
        continue;
      }
      assert.equal(await rendered.locator('tr[data-test-series]').count(),table.rows.length);
      for(const column of table.columns) {
        assert.ok((await rendered.locator('thead').innerText()).includes(column.label),column.label);
        assert.ok((await rendered.locator('thead').innerText()).includes(column.unit),column.unit);
      }
      for(const row of table.rows) {
        const shown=rendered.locator(`tr[data-test-series="${row.series_id}"]`);
        const series=articleEvidence.series[row.series_id];
        const source=articleEvidence.sources[series.source_id];
        assert.ok((await shown.locator('th').innerText()).includes(series.grade));
        const detailFields=new Set(['recommended_filament_drying','recommended_chamber','orientation_support','specimen_settings_scope','dry_status_definition','annealing','thermal_state','filler_status','annealing_temperature_c','annealing_duration_h','uptake_condition_is_separate','strength_endpoint']);
        const adjacentContext=Object.entries(series.context || {}).filter(([key])=>!detailFields.has(key));
        const context=shown.locator('.result-context');
        assert.ok(await context.count()>=4+adjacentContext.length,'adjacent specimen and source conditions');
        const contextText=(await context.allTextContents()).join('\n');
        assert.ok(contextText.toLowerCase().includes(source.kind.replaceAll('-',' ')),'source evidence type remains visible');
        for(const value of [series.process,series.conditioning,series.post_processing,...adjacentContext.map(([,value])=>value)]) {
          assert.ok(contextText.includes(value===null?'Not reported':String(value)),row.series_id+' preserves context: '+value);
        }
        for(const item of await context.all()) assert.equal(await item.isVisible(),true,'essential conditions are visible beside results');
        assert.ok((await shown.innerText()).includes(series.orientation===null?'Not reported':series.orientation));
        assert.ok((await shown.innerText()).includes(series.test_standard));
        for(let index=0;index<table.columns.length;index++) {
          const ref=row.values[table.columns[index].key];
          const cell=shown.locator('td').nth(index+1);
          if(ref===null) {
            assert.equal(await cell.getAttribute('class'),'evidence-gap');
            assert.equal(await cell.innerText(),'Not reported');
          } else {
            assert.equal(await cell.getAttribute('data-result'),ref);
            const measurement=articleEvidence.measurements[ref];
            const value=await cell.evaluate(td=>td.firstChild.textContent.trim());
            const [nominal,spread]=value.split(/\s*±\s*/);
            assert.equal(Number(nominal.replace(/^(?:>=|<=|>|<|≥|≤|≈|~)\s*/,'')),measurement.value,ref+' value');
            if(measurement.qualifier!=='=') assert.ok(nominal.startsWith(measurement.qualifier),ref+' bound');
            assert.equal(spread===undefined?null:Number(spread),measurement.spread,ref+' reported scatter');
            assert.equal(await cell.locator('a.claim-citation').getAttribute('href'),source.url);
            assert.equal(await cell.locator('a.evidence-link').getAttribute('href'),'#evidence-'+ref);
          }
        }
        assert.equal(await shown.locator('a[href="#series-'+row.series_id+'"]').count(),1);
        assert.equal(await target.locator('#series-'+row.series_id).count(),1);
        const allMethodContext=await target.locator('#series-'+row.series_id).textContent();
        for(const value of Object.values(series.context || {})) assert.ok(allMethodContext.includes(value===null?'Not reported':String(value)),'complete context retained in specimen record');
      }
    }
  }
  async function verifyPrinterRecord(target, printer) {
    assert.equal(await target.locator('body.printer-page.printer-detail').count(),1,printer.id);
    assert.equal(await target.locator('details.printer-spec-group[open]').count(),0,printer.id+' specifications start collapsed');
    const rows=await target.locator('tr[data-field]').evaluateAll(nodes=>nodes.map(row=>({
      id:row.dataset.field,
      label:row.querySelector('th')?.textContent,
      value:row.querySelector('.printer-property-value')?.textContent.trim(),
      group:row.closest('details.printer-spec-group')?.id,
      sources:row.querySelector('.printer-row-sources')?.textContent || '',
      urls:[...row.querySelectorAll('a[href]')].map(link=>link.getAttribute('href'))
    })));
    assert.deepEqual(rows.map(row=>row.id).sort(),Object.keys(printer.sp).sort(),printer.id+' retains every published field once');
    for(const row of rows) {
      const field=printers.fields.find(field=>field.id===row.id),value=printer.sp[row.id];
      assert.equal(row.value,value.v.trim(),printer.id+'/'+row.id+' preserves complete conditions and qualifiers');
      assert.ok(row.label.includes(field.name),printer.id+'/'+row.id+' field name');
      if(field.unit) assert.ok(row.label.includes(field.unit),printer.id+'/'+row.id+' unit');
      assert.equal(row.group,'spec-'+field.sec.toLowerCase(),printer.id+'/'+row.id+' native disclosure');
      for(const id of value.s || []) {
        const source=printers.src[id];
        if(source.u) assert.ok(row.urls.includes(source.u),printer.id+'/'+row.id+' source URL');
        for(const key of ['t','d','k']) if(source[key]) assert.ok(row.sources.includes(source[key]),printer.id+'/'+row.id+' source '+key);
      }
    }
    const record=printerResources[printer.id];
    const ownership=await target.locator('.printer-context-note').evaluateAll(nodes=>nodes.map(note=>({
      kind:note.dataset.resourceKind, section:note.dataset.resourceSection,
      topic:note.closest('[data-printer-topic]')?.dataset.printerTopic,
      chapter:note.closest('.printer-spec-chapter')?.id,
      title:note.querySelector('h4')?.textContent, text:note.textContent,
      links:[...note.querySelectorAll('a')].map(link=>link.getAttribute('href')),
      visible:note.getBoundingClientRect().height>0
    })));
    const expected=Object.entries(record).filter(([kind])=>kind!=='reviewed_sources').flatMap(([kind,entries])=>entries.map(entry=>({kind,...entry})));
    assert.equal(ownership.length,expected.length,printer.id+' retains every ownership resource');
    for(const entry of expected) {
      const notes=ownership.filter(note=>note.kind===entry.kind && note.title===entry.title);
      assert.equal(notes.length,1,printer.id+' resource identity');
      const note=notes[0];
      assert.equal(note.section,entry.section); assert.equal(note.topic,entry.section);
      assert.equal(note.chapter,Object.entries({machine:'ABCD',printing:'EFGHIJKLRW',workflow:'MNOPQ',ownership:'STUV'}).find(([,sections])=>sections.includes(entry.section))[0]);
      assert.ok(note.visible && note.text.includes(entry.summary) && note.text.includes(entry.compatibility),printer.id+' visible diagnostic or modification context');
      assert.ok(note.text.includes(entry.evidence[0].toUpperCase()+entry.evidence.slice(1)),printer.id+' evidence type');
      for(const source of entry.sources) assert.ok(note.links.includes(source.url) && note.text.includes(source.checked),printer.id+' dated source');
    }
    assert.equal(await target.locator('#sources .printer-resource-review').count(),1,printer.id+' coverage notes remain with guide sources');
    const visual=target.locator('.printer-visual');
    const image=printerPhotos[printer.id];
    if(image) {
      const photo=visual.locator('img[data-printer-image]');
      assert.equal(await photo.count(),1,printer.id);
      assert.equal(await photo.getAttribute('data-printer-image'),printer.id);
      assert.equal(await photo.getAttribute('src'),'../'+image.image);
      assert.equal(await photo.getAttribute('alt'),image.alt);
      await photo.evaluate(img=>img.decode());
      assert.deepEqual(await photo.evaluate(img=>[img.naturalWidth,img.naturalHeight]),[image.width,image.height],printer.id+' exact model photo decodes');
      assert.equal(await visual.locator(`a[href="${image.source_url}"]`).count(),1,printer.id+' source credit');
      assert.ok((await visual.innerText()).includes(image.credit));
      if(image.reuse.license_url) {
        assert.equal(await visual.locator(`a[href="${image.reuse.license_url}"]`).count(),1,printer.id+' licence is adjacent to photo');
        assert.ok((await visual.innerText()).includes(image.reuse.changes),printer.id+' photo changes disclosed');
      }
    } else {
      assert.equal(await visual.locator('img[data-printer-image]').count(),0,printer.id+' does not borrow a sibling photo');
      assert.equal(await visual.locator(`img[data-printer-diagram="${printer.f.toLowerCase()}"]`).count(),1,printer.id+' has its actual architecture fallback');
      assert.match(await visual.innerText(),/generic/i);
    }
  }
  async function openPrinterField(target, fieldId) {
    const row=target.locator(`tr[data-field="${fieldId}"]`);
    const group=row.locator('xpath=ancestor::details[contains(concat(" ",normalize-space(@class)," ")," printer-spec-group ")]');
    if(await group.getAttribute('open')===null) {
      await group.locator(':scope > summary').focus();
      await target.keyboard.press('Enter');
    }
    assert.equal(await row.isVisible(),true,'native printer specification opens from keyboard');
    const value=row.locator('.printer-property-value');
    const layout=await value.evaluate(cell=>{
      const style=getComputedStyle(cell);
      return {horizontal:cell.scrollWidth<=cell.clientWidth+1,vertical:cell.scrollHeight<=cell.clientHeight+1,
        ellipsis:style.textOverflow==='ellipsis',lineClamp:style.webkitLineClamp};
    });
    assert.ok(layout.horizontal && layout.vertical && !layout.ellipsis && ['none','0',''].includes(layout.lineClamp),'full printer property text wraps without clipping');
    return row;
  }
  await visit('');
  for (const [key,n] of Object.entries({printers:printers.cats.length,'printer-fields':printers.fields.length,materials:materials.cats.length,products:productCount})) {
    for (const s of await page.locator(`[data-summary="${key}"]`).allTextContents()) assert.equal(Number(s),n);
  }
  await page.screenshot({path:path.join(root,'test-results/home.png')});
  assert.equal(await page.locator('#featured-comparisons a[data-discovery-pair]').count(),8,'homepage exposes eight curated pairs as ordinary HTML links');
  await page.locator('#featured-comparisons').screenshot({path:path.join(root,'test-results/home-comparisons.png')});
  await page.locator('#featured-comparisons a[href="compare/materials/petg-vs-pla.html"]').click();
  await verifyPair(page,pairCases[0]);
  await visit('materials/pla.html');
  await page.locator('#selected-comparisons a[href="../compare/materials/asa-vs-pla.html"]').click();
  assert.match(await page.locator('h1').innerText(),/ASA vs PLA/);
  await visit('updates/');
  assert.equal(await page.locator('link[rel="alternate"][type="application/rss+xml"]').getAttribute('href'),'https://sfmth.github.io/3d_printing_info/feed.xml');
  assert.equal(await page.locator('.updates-list > article').count(),siteUpdates.length);
  await page.screenshot({path:path.join(root,'test-results/updates-desktop.png')});
  step('Homepage and guide links open the exact pair directly; dated updates expose RSS and Atom');
  await visit('');
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
  assert.equal(await page.locator('[data-printer-card]').count(),printers.cats.length);
  assert.deepEqual((await page.locator('[data-printer-card]').evaluateAll(cards=>cards.map(card=>card.dataset.printerId))).sort(),printers.cats.map(printer=>printer.id).sort());
  assert.equal(await page.locator('.pl-feature-card').count(),6);
  await page.screenshot({path:path.join(root,'test-results/printer-directory-desktop.png')});
  await page.getByLabel('Search by brand or model',{exact:true}).fill('Photon P1 Max');
  assert.equal(await page.locator('[data-printer-card]:not([hidden])').count(),1);
  assert.equal(await page.locator('#printer-starting-points').isVisible(),false,'featured suggestions hide when searching the complete library');
  await page.locator('[data-printer-id="anycubic-photon-p1-max"] .pl-card-compare').click();
  await page.locator('#mtbody tr.row.open').waitFor({state:'visible'});
  assert.equal(await page.locator('#q').inputValue(),'Anycubic Photon P1 Max');
  await visit('printers/');
  await page.locator('[data-printer-filter="RESIN"]').click();
  assert.equal(await page.locator('#printer-starting-points').isVisible(),false,'featured suggestions respect family filters');
  assert.equal(await page.locator('[data-printer-card]:not([hidden])').count(),printers.cats.filter(printer=>printer.f==='RESIN').length);
  assert.equal(await page.locator('[data-printer-filter="RESIN"]').getAttribute('aria-pressed'),'true');
  await page.getByLabel('Search by brand or model',{exact:true}).fill('Anycubic');
  assert.equal(await page.locator('[data-printer-card]:not([hidden])').count(),printers.cats.filter(printer=>printer.f==='RESIN' && /anycubic/i.test(printer.brand+' '+printer.n)).length);
  await page.screenshot({path:path.join(root,'test-results/printer-directory-filtered.png')});
  await page.getByLabel('Search by brand or model',{exact:true}).fill('no-such-printer-xyz');
  assert.equal(await page.locator('#printer-no-results').isVisible(),true);
  assert.equal(await page.locator('[data-printer-card]:not([hidden])').count(),0);
  await page.locator('#clear-printer-search').click();
  assert.equal(await page.getByLabel('Search by brand or model',{exact:true}).inputValue(),'');
  assert.equal(await page.locator('[data-printer-card]:not([hidden])').count(),printers.cats.length);
  assert.equal(await page.locator('#printer-starting-points').isVisible(),true,'clearing filters restores the full library and suggestions');
  step('Printer detail-page round trip and complete crawlable printer directory');
  step('Printer library search, combined family/brand filtering, empty/reset states and exact-model comparison links');
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
        assert.equal(await photo.evaluate(img=>getComputedStyle(img).objectFit),'contain',id+' full source image is shown');
      }
      assert.equal(await story.locator('h3 a').getAttribute('href'),e.url);
      await story.locator('.inline-sources > summary').click();
      assert.ok((await story.innerText()).includes(e.evidence));
      assert.ok((await story.innerText()).includes(e.creator));
      assert.match(await story.innerText(),/listing uploaded by/i);
      assert.doesNotMatch(await story.innerText(),/Photo & model by|Photo and model:/);
      assert.ok(await story.locator(`a[href="${e.license_url}"]`).count()>0);
      if(e.image) assert.ok(await story.locator(`a[href="${e.image_url}"]`).count()>0,'original image remains linked');
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
    assert.equal(await page.locator('script[src*="googletagmanager.com/gtag/js"]').count(),0);
    const metadata=await referenceMetadata();
    assert.ok(!metadata.types.includes('Product'),c.id);
    const article=metadata.documents.find(document=>document['@type']==='WebPage').mainEntity;
    assert.equal(article['@type'],'TechArticle',c.id);
    assert.equal(article.about['@type'],'Thing',c.id);
    assert.equal(article.about.name,c.n,c.id);
    await verifyPrinterRecord(page,c);
  }
  step(`All ${printers.cats.length} printer guides render technical-article metadata without unsupported Product entities, matching canonical URLs and a local opt-in analytics gate`);
  step(`All ${printers.cats.length} printer guides integrate dated firmware, modifications and diagnostic evidence within the matching technical topics`);
  step(`All ${printers.cats.length} printer guides retain every complete field and its own sources inside native disclosures, with exact-model photos or labeled architecture diagrams`);
  const picturedPrinter=printers.cats.find(printer=>printer.id==='bambu-p1s' && printerPhotos[printer.id]) || printers.cats.find(printer=>printerPhotos[printer.id]);
  await visit('printers/'+picturedPrinter.id+'.html');
  await page.locator('.printer-visual img').evaluate(img=>img.decode());
  await page.screenshot({path:path.join(root,'test-results/printer-detail-overview.png')});
  await page.emulateMedia({colorScheme:'dark'});
  await page.screenshot({path:path.join(root,'test-results/printer-detail-dark.png')});
  await page.emulateMedia({colorScheme:'light'});
  await visit('printers/bambu-x1c.html');
  await page.locator('#workflow').scrollIntoViewIfNeeded();
  const firmwareEvidence=page.locator('[data-resource-kind="firmware"] .printer-resource-evidence');
  await firmwareEvidence.locator('summary').focus(); await page.keyboard.press('Enter');
  assert.equal(await firmwareEvidence.locator('a').first().isVisible(),true,'firmware evidence opens from the keyboard');
  await page.screenshot({path:path.join(root,'test-results/printer-ownership-firmware.png')});
  await visit('printers/creality-ender-3-v3-se.html');
  await page.locator('#printing').scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(root,'test-results/printer-ownership-hardware.png')});
  await visit('printers/neptune4pro.html');
  const longPrinterRow=await openPrinterField(page,'E5');
  const printerSource=longPrinterRow.locator('.printer-row-sources');
  await printerSource.locator(':scope > summary').focus();
  await page.keyboard.press('Enter');
  assert.equal(await printerSource.locator('li').first().isVisible(),true,'keyboard reveals source citations beside their field');
  await longPrinterRow.evaluate(row=>row.scrollIntoView({block:'start'}));
  await page.screenshot({path:path.join(root,'test-results/printer-detail-specifications.png')});
  step('Printer detail photographs, full long-form properties, source disclosures, keyboard focus and dark theme remain readable');
  const articlePath='articles/choosing-fdm-material-load-bearing-part.html';
  const articleTitle='Choosing an FDM material for a load-bearing part';
  await visit('');
  await page.getByRole('navigation',{name:'Primary',exact:true}).getByRole('link',{name:'Selection articles',exact:true}).click();
  assert.equal(new URL(page.url()).pathname,new URL(base+'articles/').pathname);
  await visit('articles/');
  assert.equal(await page.locator('[data-article-card]').count(),articles.length,'article hub lists every published article');
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
  for(const article of genericArticles) {
    await visit('articles/');
    await page.locator(`a[data-article-card][href="${article.id}.html"]`).click();
    await visit('articles/'+article.id+'.html');
    assert.equal(await page.locator('main h1').innerText(),article.title);
    const metadata=(await referenceMetadata()).documents.find(document=>document['@type']==='WebPage');
    assert.equal(metadata.url,'https://sfmth.github.io/3d_printing_info/articles/'+article.id+'.html');
    assert.equal(metadata.mainEntity['@type'],'TechArticle');
    assert.equal(metadata.mainEntity.author.name,article.author.name);
    assert.equal(metadata.mainEntity.dateModified,article.modified);
    await verifyGenericTables(page,article);
    const methodLink=page.locator('table[data-evidence-table] a[href^="#series-"]').first();
    if(await methodLink.count()) {
      const methodTarget=await methodLink.getAttribute('href');
      await methodLink.click();
      assert.equal(await page.locator(methodTarget+' dl').isVisible(),true,'table link opens its specimen conditions');
    }
    const evidenceLink=page.locator('table[data-evidence-table] a.evidence-link').first();
    const evidenceTarget=await evidenceLink.getAttribute('href');
    await evidenceLink.click();
    assert.equal(await page.locator(evidenceTarget).isVisible(),true,'result link opens its precise evidence record');
    await page.locator('#measurements').evaluate(el=>el.scrollIntoView({block:'start'}));
    await page.screenshot({path:path.join(root,'test-results/'+article.id+'-desktop.png')});
  }
  if(genericArticles.length) step(`All ${genericArticles.length} expanded articles retain exact measurements, explicit gaps, adjacent specimen context and source/method navigation`);
  await visit('');
  await page.locator('a[href="compare/"]').click();
  await page.locator('main a[href="materials/"]').click();
  await page.locator('main a[href="pla/"]').click();
  await page.locator('main a[href="../petg-vs-pla.html"]').click();
  await verifyPair(page,pairCases[0]);
  step('Comparison hub and bounded per-item directories reach a complete pair through ordinary links');
  for(const fixture of pairCases) {
    const file=pairFile(fixture.kind,fixture.ids);
    await visit(file);
    const rows=await verifyPair(page,fixture);
    assert.equal(await page.locator('#pair-picker').isVisible(),true,'JavaScript enables the pair picker');
    assert.ok(rows.some(row=>row.different==='true'),'representative pair exercises different properties');
    if(fixture.kind==='materials')assert.ok(rows.some(row=>row.different==='false'),'material pair also exercises hiding equal properties');
    const total=await page.locator('#pair-table tr[data-different]').count();
    await page.locator('#pair-differences').click();
    assert.equal(await page.locator('#pair-differences').getAttribute('aria-pressed'),'true');
    assert.equal(await page.locator('#pair-table tr[data-different="false"]:visible').count(),0,'equal values hide without removing records');
    assert.equal(await page.locator('#pair-table tr[data-different]').count(),total);
    assert.match(await page.locator('#pair-status').innerText(),/different values/);
    await page.emulateMedia({media:'print'});
    assert.equal(await page.locator('#pair-table tr[data-different="false"]:visible').count(),await page.locator('#pair-table tr[data-different="false"]').count(),'printing includes equal properties while difference filter is active');
    await page.emulateMedia({media:'screen'});
    await page.locator('#pair-differences').click();
    assert.equal(await page.locator('#pair-table tr[data-different][hidden]').count(),0);
    await page.screenshot({path:path.join(root,`test-results/pair-${fixture.kind==='materials'?'material':'printer'}-desktop.png`)});
    await openPairCitation(page);
    await page.locator('#pair-interactive').click();
    assert.equal(new URL(page.url()).searchParams.get('compare'),[...fixture.ids].sort().join(','));
    assert.equal(await page.locator('#cmpout table thead th').count(),3,'interactive deep link preselects exactly two entries');
    assert.equal(await page.locator('#pair-link').getAttribute('href'),file,'interactive comparison links back to its permanent static URL');
    await page.locator('#pair-link').click();
    await verifyPair(page,fixture);
    const ids=[...fixture.ids].sort();
    await page.locator('#pair-picker select[name="first"]').selectOption(ids[1]);
    await page.locator('#pair-picker select[name="second"]').selectOption(ids[0]);
    await page.locator('#pair-picker button[type="submit"]').click();
    assert.match(await page.locator('#pair-status').innerText(),/already open/,'reversed input maps to the same unordered pair');
    await page.locator('#pair-picker select[name="first"]').selectOption(ids[0]);
    await page.locator('#pair-picker button[type="submit"]').click();
    assert.equal(await page.locator('#pair-picker select[name="second"]').getAttribute('aria-invalid'),'true','same-item selection gets an actionable error');
    assert.match(await page.locator('#pair-status').innerText(),/two different/);
    const other=fixture.data.cats.find(cat=>!ids.includes(cat.id)).id;
    await page.locator('#pair-picker select[name="second"]').selectOption(other);
    const next=pairFile(fixture.kind,[ids[0],other]);
    await Promise.all([
      page.waitForURL(base+next),
      page.locator('#pair-picker button[type="submit"]').click(),
    ]);
    await verifyPair(page,{...fixture,ids:[ids[0],other]});
  }
  step('Filament and printer pairs retain every sourced value, filter differences, print complete records, reject self-pairs, navigate the picker and round-trip through interactive deep links');
  await visit('materials/peba.html');
  await page.screenshot({path:path.join(root,'test-results/peba-guide.png')});
  await page.setViewportSize({width:390,height:844});
  for(const fixture of pairCases) {
    await visit(pairFile(fixture.kind,fixture.ids));
    await verifyPair(page,fixture);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,fixture.kind+' pair fits 390px viewport');
    const scroll=await page.locator('.pair-table-wrap').evaluate(wrapper=>{
      wrapper.scrollLeft=wrapper.scrollWidth;
      const result={overflow:wrapper.scrollWidth>wrapper.clientWidth,scrolled:wrapper.scrollLeft>0};
      wrapper.scrollLeft=0;
      return result;
    });
    assert.ok(scroll.overflow && scroll.scrolled,'both comparison columns scroll inside their wrapper on mobile');
    const valuesFit=await page.locator('td.property-value').evaluateAll(cells=>cells.every(cell=>{
      const style=getComputedStyle(cell);
      return cell.scrollWidth<=cell.clientWidth+1 && cell.scrollHeight<=cell.clientHeight+1 && style.textOverflow!=='ellipsis' && ['none','0',''].includes(style.webkitLineClamp);
    }));
    assert.ok(valuesFit,'long property values wrap in full without clipping');
    await page.screenshot({path:path.join(root,`test-results/pair-${fixture.kind==='materials'?'material':'printer'}-mobile.png`)});
    await openPairCitation(page);
  }
  step('Both pair layouts retain complete values and keyboard source navigation at 390px with scrolling contained inside the table');
  await page.goto(base,{waitUntil:'networkidle'});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'homepage mobile width');
  await page.locator('#featured-comparisons').screenshot({path:path.join(root,'test-results/home-comparisons-mobile.png')});
  await visit('updates/');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'updates archive mobile width');
  await page.screenshot({path:path.join(root,'test-results/updates-mobile.png')});
  await visit('');
  await page.getByRole('link',{name:'Filaments',exact:true}).click();
  await page.locator('#mtbody tr.row[data-id="peba"]').waitFor({state:'visible'});
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
  assert.equal(await page.locator('[data-material="tpu-85a"] img').evaluate(img=>getComputedStyle(img).objectFit),'contain','ND directory image is never cropped on mobile');
  await page.screenshot({path:path.join(root,'test-results/mobile-material-library.png')});
  await page.getByLabel('Search material guides',{exact:true}).fill('nylon');
  assert.ok(await page.locator('[data-material]:not([hidden])').count()>0);
  await page.screenshot({path:path.join(root,'test-results/mobile-material-search.png')});
  await page.goto(base+'printers/anycubic-photon-p1-max.html',{waitUntil:'networkidle'});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'printer guide mobile width');
  await page.screenshot({path:path.join(root,'test-results/mobile-printer-guide.png')});
  await visit('printers/neptune4pro.html');
  const mobilePrinterRow=await openPrinterField(page,'E5');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'long printer property does not overflow mobile page');
  const printerLabelBox=await mobilePrinterRow.locator('th').boundingBox();
  const printerValueBox=await mobilePrinterRow.locator('.printer-property-value').boundingBox();
  assert.ok(printerLabelBox && printerValueBox && printerValueBox.y>=printerLabelBox.y+printerLabelBox.height-1,'mobile printer specification stacks its value below the field label');
  await mobilePrinterRow.evaluate(row=>row.scrollIntoView({block:'start'}));
  await page.screenshot({path:path.join(root,'test-results/mobile-printer-specifications.png')});
  await visit('printers/bambu-a1.html');
  await page.locator('#printing').scrollIntoViewIfNeeded();
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'ownership prose and evidence fit mobile width');
  await page.screenshot({path:path.join(root,'test-results/mobile-printer-ownership.png')});
  await visit('printers/');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'printer library mobile width');
  await page.screenshot({path:path.join(root,'test-results/mobile-printer-library.png')});
  await page.getByLabel('Search by brand or model',{exact:true}).fill('Photon P1 Max');
  assert.equal(await page.locator('[data-printer-card]:not([hidden])').count(),1);
  await page.locator('[data-printer-id="anycubic-photon-p1-max"] .pl-card-link').click();
  assert.equal(await page.locator('main h1').innerText(),'Anycubic Photon P1 Max');
  step('Printer library search, guide navigation and complete stacked specification values work at 390 px');
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
  for(const article of genericArticles) {
    await visit('articles/'+article.id+'.html');
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,article.id+' mobile width');
    for(const table of article.tables) {
      const state=await page.locator(`table[data-evidence-table="${table.id}"]`).evaluate(table=>{
        const wrapper=table.closest('.table-scroll');
        if(!wrapper) return null;
        wrapper.scrollLeft=wrapper.scrollWidth;
        const result={scrollable:wrapper.scrollWidth>wrapper.clientWidth,scrolled:wrapper.scrollLeft>0};
        wrapper.scrollLeft=0;
        return result;
      });
      assert.ok(state && state.scrollable && state.scrolled,table.id+' is scrollable inside its mobile wrapper');
    }
    await page.locator('#measurements').evaluate(el=>el.scrollIntoView({block:'start'}));
    await page.screenshot({path:path.join(root,'test-results/'+article.id+'-mobile.png')});
  }
  if(genericArticles.length) step('Expanded article comparisons keep horizontal scrolling inside their tables at 390 px');
  step('Mobile navigation, filtering, material and printer guide layouts at 390 px');
  const nojs=await browser.newContext({javaScriptEnabled:false});
  const staticPage=await nojs.newPage();
  await staticPage.goto(base);
  assert.equal(await staticPage.locator('#featured-comparisons a[data-discovery-pair]').count(),8);
  await staticPage.locator('#featured-comparisons a[href="compare/materials/petg-vs-pla.html"]').click();
  await verifyPair(staticPage,pairCases[0]);
  await staticPage.goto(base+'printers/bambu-a1.html');
  await staticPage.locator('#selected-comparisons a[href="../compare/printers/bambu-a1-vs-bambu-p1s.html"]').click();
  assert.match(await staticPage.locator('h1').innerText(),/A1 vs Bambu Lab P1S|A1 vs.*P1S/);
  await staticPage.goto(base+'updates/');
  assert.equal(await staticPage.locator('.updates-list > article').count(),siteUpdates.length);
  assert.equal(await staticPage.getByRole('link',{name:'Subscribe with RSS',exact:true}).getAttribute('href'),'../feed.xml');
  step('Featured comparisons, contextual guide links and the updates archive work without JavaScript');
  for(const fixture of pairCases) {
    await staticPage.goto(base+pairFile(fixture.kind,fixture.ids));
    await verifyPair(staticPage,fixture);
    assert.equal(await staticPage.locator('#pair-differences').isVisible(),false,'inactive difference control stays hidden without JavaScript');
    assert.equal(await staticPage.locator('#pair-picker').isVisible(),false,'inactive pair picker stays hidden without JavaScript');
    assert.equal(await staticPage.locator('#pair-table tr[data-field][hidden]').count(),0,'all pair values are readable without JavaScript');
    await openPairCitation(staticPage);
    await staticPage.locator('#pair-interactive').click();
    assert.equal(await staticPage.locator('#static > table').first().locator('tbody tr').count(),fixture.data.cats.length,'interactive link still exposes the complete static catalog fallback');
  }
  await staticPage.goto(base+'compare/');
  await staticPage.locator('main a[href="printers/"]').click();
  await staticPage.locator('main a[href="bambu-a1/"]').click();
  await staticPage.locator('main a[href="../bambu-a1-vs-neptune4pro.html"]').click();
  await verifyPair(staticPage,pairCases[1]);
  await staticPage.screenshot({path:path.join(root,'test-results/pair-printer-nojs.png')});
  step('Complete pair tables, dated source anchors, directory crawl routes and original catalog fallbacks work with JavaScript disabled');
  await staticPage.goto(base+'printers/');
  assert.equal(await staticPage.locator('script[src*="googletagmanager.com/gtag/js"]').count(),0,'no remote analytics script without JavaScript');
  assert.equal(await staticPage.locator('footer [data-analytics-settings]').isVisible(),false,'inactive settings control stays hidden without JavaScript');
  assert.equal(await staticPage.locator('footer a[href="../privacy.html"]').isVisible(),true,'privacy disclosure remains available without JavaScript');
  assert.equal(await staticPage.locator('[data-printer-card]').count(),printers.cats.length);
  assert.equal(await staticPage.locator('#printer-search-panel').isVisible(),false,'inactive printer filters are hidden without JavaScript');
  assert.equal(await staticPage.locator('details.pl-family[open]').count(),printers.families.length);
  await staticPage.locator('[data-printer-id="neptune4pro"] .pl-card-link').click();
  await verifyPrinterRecord(staticPage,printers.cats.find(printer=>printer.id==='neptune4pro'));
  const staticPrinterRow=await openPrinterField(staticPage,'E5');
  await staticPrinterRow.locator('.printer-row-sources > summary').focus();
  await staticPage.keyboard.press('Enter');
  assert.equal(await staticPrinterRow.locator('.printer-row-sources li').first().isVisible(),true,'printer field sources work without JavaScript');
  await staticPage.screenshot({path:path.join(root,'test-results/nojs-printer-specifications.png')});
  const resourceEvidence=staticPage.locator('.printer-resource-evidence').first();
  await resourceEvidence.locator('summary').focus(); await staticPage.keyboard.press('Enter');
  assert.equal(await resourceEvidence.locator('a').first().isVisible(),true,'ownership sources work without JavaScript');
  await staticPage.locator('#printing').scrollIntoViewIfNeeded();
  await staticPage.screenshot({path:path.join(root,'test-results/nojs-printer-ownership.png')});
  await staticPage.getByRole('link',{name:'Open in interactive comparison',exact:true}).click();
  assert.equal(await staticPage.locator('#static tbody tr').count(),printers.cats.length);
  step('Printer directory, exact-model links, keyboard specification/source disclosures and complete comparison fallback work without JavaScript');
  await staticPage.goto(base+'comparison.html');
  assert.equal(await staticPage.locator('#static tbody tr').count(),printers.cats.length);
  await staticPage.locator('#static a[href="printers/anycubic-photon-p1-max.html"]').click();
  assert.equal(await staticPage.locator('h1').innerText(),'Anycubic Photon P1 Max');
  assert.equal(await staticPage.locator('main table').count()>0,true);
  assert.equal(await staticPage.locator('.printer-spec-group table:visible').count(),0,'fresh printer sections start collapsed');
  await staticPage.emulateMedia({media:'print'});
  assert.equal(await staticPage.locator('.printer-spec-group table:visible').count(),await staticPage.locator('.printer-spec-group table').count(),'printing includes specifications from closed native sections');
  assert.ok(await staticPage.locator('.printer-row-sources li:visible').count()>0,'printing includes field citations without JavaScript');
  await staticPage.emulateMedia({media:'screen'});
  assert.equal(await staticPage.locator('.printer-spec-group table:visible').count(),0,'printing leaves screen reading sections collapsed');
  step('Printer print layout includes all specifications and citations without changing native screen disclosure state');
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
  for(const article of genericArticles) {
    await staticPage.goto(base+'articles/');
    assert.equal(await staticPage.locator('[data-article-card]').count(),articles.length);
    await staticPage.locator(`a[data-article-card][href="${article.id}.html"]`).click();
    assert.equal(await staticPage.locator('main h1').innerText(),article.title);
    await verifyGenericTables(staticPage,article);
    const methodLink=staticPage.locator('table[data-evidence-table] a[href^="#series-"]').first();
    if(await methodLink.count()) {
      const methodTarget=await methodLink.getAttribute('href');
      await methodLink.click();
      assert.equal(await staticPage.locator(methodTarget+' dl').isVisible(),true,'specimen context opens through its fragment without JavaScript');
    }
    const evidenceLink=staticPage.locator('table[data-evidence-table] a.evidence-link').first();
    const target=await evidenceLink.getAttribute('href');
    await evidenceLink.click();
    assert.equal(await staticPage.locator(target).isVisible(),true,'evidence record opens without JavaScript');
    assert.ok(await staticPage.locator('#sources li[data-source] a[href^="https://"]').count()>0);
    assert.equal(await staticPage.locator('#verification').isVisible(),true);
  }
  if(genericArticles.length) step('Expanded articles preserve all results, unknown cells, visible test conditions and native source/method navigation without JavaScript');
  assert.deepEqual(errors,[],'uncaught JavaScript errors');
  assert.deepEqual(missing,[],'missing local assets');
  step('No uncaught JavaScript exceptions or missing local assets');
  const result={commit:execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(),browser:await browser.version(),counts:{printers:printers.cats.length,materials:materials.cats.length,products:productCount,detailPages:printers.cats.length+materials.cats.length,articles:articles.length,pairComparisons:[printers,materials].reduce((total,data)=>total+data.cats.length*(data.cats.length-1)/2,0),pairDirectories:3+printers.cats.length+materials.cats.length},analytics:'Zero Google requests before consent/after decline; grant, withdrawal, cookie cleanup and cross-tab/storage behavior checked with intercepted loader/collection; ingestion not verified',steps};
  await fs.writeFile(path.join(root,'test-results/browser-results.json'),JSON.stringify(result,null,2)+'\n');
} finally {
  if(browser) await browser.close();
  await new Promise(resolve=>server.close(resolve));
}
