'use strict';
// Real browser acceptance against an installed, exported composer. No model or network service.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require('playwright');

async function main() {
  const source = path.resolve(process.env.COHORTFRAME_STUDIO || '/tmp/cohortframe-studio');
  const output = path.resolve(process.env.COHORTFRAME_BROWSER_OUTPUT || 'browser-results');
  await fs.mkdir(output, { recursive: true });
  const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml' };
  const server = http.createServer(async (req, res) => {
    const name = req.url === '/' ? 'index.html' : req.url.slice(1);
    if (!['index.html', 'model.js', 'app.js', 'style.css', 'mark.svg'].includes(name)) {
      res.writeHead(404); res.end(); return;
    }
    try {
      res.writeHead(200, { 'Content-Type': types[path.extname(name)] });
      res.end(await fs.readFile(path.join(source, name)));
    } catch { res.writeHead(500); res.end(); }
  });
  await new Promise((resolve, reject) => {
    server.once('error', reject); server.listen(0, '127.0.0.1', resolve);
  });
  let browser;
  const results = [];
  try {
    browser = await chromium.launch({ headless: true });
    const origin = 'http://127.0.0.1:' + server.address().port;
    for (const [name, width, height] of [['desktop', 1440, 1000], ['mobile', 390, 844]]) {
      const context = await browser.newContext({ viewport: { width, height }, acceptDownloads: true });
      const page = await context.newPage();
      const errors = [];
      const remoteRequests = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.route('**/*', route => {
        const url = route.request().url();
        if (url.startsWith(origin + '/')) return route.continue();
        remoteRequests.push(url); return route.abort();
      });
      await page.goto(origin + '/', { waitUntil: 'networkidle' });
      await page.locator('#composer').scrollIntoViewIfNeeded();
      await page.locator('#template').selectOption('research');
      await page.locator('#name').fill('Browser acceptance ' + name);
      await page.locator('#title').fill('A CHECKABLE CLAIM');
      await page.locator('#duplicate').click();
      assert.equal(await page.locator('#scenes li').count(), 4);
      await page.locator('#title').fill('SECOND CHECK');
      await page.locator('#up').click();
      assert.equal(await page.locator('#title').inputValue(), 'SECOND CHECK');
      await page.locator('#undo').click();
      await page.locator('#redo').click();
      assert.equal(await page.locator('#title').inputValue(), 'SECOND CHECK');
      await page.locator('#title').fill('Unsupported \u2603');
      assert.equal(await page.locator('#export').isDisabled(), true);
      await page.locator('#title').fill('SECOND CHECK');
      await page.locator('#format').selectOption(name === 'desktop' ? '720x1280' : '1080x1080');
      const dimensions = await page.locator('#preview').evaluate(canvas => [canvas.width, canvas.height]);
      assert.deepEqual(dimensions, name === 'desktop' ? [720, 1280] : [1080, 1080]);
      const downloading = page.waitForEvent('download');
      await page.locator('#export').click();
      const download = await downloading;
      const briefPath = path.join(output, name + '-brief.json');
      await download.saveAs(briefPath);
      const brief = JSON.parse(await fs.readFile(briefPath, 'utf8'));
      assert.equal(brief.name, 'Browser acceptance ' + name);
      assert.equal(brief.scenes.length, 4);
      assert.equal(brief.scenes[0].title, 'SECOND CHECK');

      await page.locator('#file').setInputFiles({ name: 'duplicate.json', mimeType: 'application/json', buffer: Buffer.from('{"version":1,"version":1}') });
      await page.waitForFunction(() => document.getElementById('feedback').textContent.startsWith('Import rejected:'));
      assert.equal(await page.locator('#scenes li').count(), 4);
      await page.reload({ waitUntil: 'networkidle' });
      assert.equal(await page.locator('#name').inputValue(), brief.name);
      assert.equal(await page.locator('#scenes li').count(), 4);
      const playbackBrief = { ...brief, scenes: brief.scenes.map(scene => ({ ...scene, duration: 0.1 })) };
      await page.locator('#file').setInputFiles({ name: 'playback.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(playbackBrief)) });
      await page.waitForFunction(() => document.getElementById('feedback').textContent.startsWith('Brief imported.'));
      await page.locator('#play').click();
      await page.waitForFunction(() => document.getElementById('play').getAttribute('aria-label') === 'Play scene sequence');
      await page.locator('#file').setInputFiles(briefPath);
      await page.waitForFunction(() => document.getElementById('feedback').textContent.startsWith('Brief imported.'));
      assert.equal(await page.locator('#title').inputValue(), 'SECOND CHECK');
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
      if (overflow) {
        const layout = await page.evaluate(() => [...document.querySelectorAll('body *')].map(element => ({ tag: element.tagName, id: element.id, className: typeof element.className === 'string' ? element.className : '', left: element.getBoundingClientRect().left, right: element.getBoundingClientRect().right, width: element.getBoundingClientRect().width })).filter(box => box.right > innerWidth + 1 || box.left < -1));
        await fs.writeFile(path.join(output, name + '-overflow.json'), JSON.stringify(layout, null, 2));
        await page.screenshot({ path: path.join(output, name + '-overflow.png'), fullPage: true });
        console.error(JSON.stringify(layout, null, 2));
      }
      assert.equal(overflow, false, name + ' page must not overflow horizontally');
      const timelineOverlapsNote = await page.evaluate(() => Math.max(...[...document.querySelectorAll('#timeline button')].map(button => button.getBoundingClientRect().bottom)) > document.querySelector('.preview-note').getBoundingClientRect().top);
      assert.equal(timelineOverlapsNote, false, name + ' timeline controls must not overlap the preview note');
      await page.locator('#composer').scrollIntoViewIfNeeded();
      await page.screenshot({ path: path.join(output, name + '-full.png'), fullPage: true });
      await page.locator('#preview').scrollIntoViewIfNeeded();
      await page.screenshot({ path: path.join(output, name + '-preview.png') });
      await page.locator('#clear').click();
      assert.equal(await page.evaluate(() => localStorage.getItem('cohortframe-studio-v1')), null);
      await page.reload({ waitUntil: 'networkidle' });
      assert.notEqual(await page.locator('#name').inputValue(), brief.name);
      assert.deepEqual(errors, [], 'No browser execution errors');
      assert.deepEqual(remoteRequests, [], 'Composer must not contact external services');
      results.push({ viewport: name, width, height, passed: true, exportedBrief: path.basename(briefPath), checks: ['editing', 'duplicate/reorder', 'undo/redo', 'unsupported text rejected', 'format change', 'JSON download', 'duplicate-key import rejected', 'draft reload', 'sequence playback', 'valid import', 'no horizontal overflow', 'no timeline overlap', 'draft clear', 'no page errors', 'no external requests'] });
      await context.close();
    }
    const evidence = { browser: await browser.version(), sourceRevision: process.env.GITHUB_SHA || null, results, scope: 'Scripted Chromium acceptance of the installed offline composer; not independent user, accessibility, or live-site validation.' };
    await fs.writeFile(path.join(output, 'browser-evidence.json'), JSON.stringify(evidence, null, 2) + '\n');
    console.log(JSON.stringify(evidence, null, 2));
  } finally {
    await browser?.close();
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
