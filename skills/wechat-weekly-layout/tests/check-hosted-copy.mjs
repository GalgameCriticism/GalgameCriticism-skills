// Exercise both clipboard actions and native paste with real public images.
import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
const [source, origin] = process.argv.slice(2);
if (!source || !origin) throw Error('Usage: node check-hosted-copy.mjs <preview-hosted.html> <public-origin>');
const browser = await chromium.launch({executablePath: process.env.CHROME_PATH || undefined, args: process.env.CHROME_NO_PROXY === '1' ? ['--no-proxy-server'] : []});
try {
  const context = await browser.newContext({permissions: ['clipboard-read', 'clipboard-write']});
  const page = await context.newPage();
  await context.setOffline(true);
  await page.goto(pathToFileURL(source).href);
  await page.waitForFunction(() => [...document.querySelectorAll('#article img')].every(i => i.complete && i.naturalWidth));
  const report = [];
  for (const id of ['copy', 'copy-safe']) {
    await context.setOffline(true);
    await page.locator('#' + id).click();
    await page.waitForFunction(id => !document.getElementById(id).disabled, id);
    assert((await page.locator('#toast').textContent()).includes('已复制'));
    const clipboard = await page.evaluate(async () => {
      const item = (await navigator.clipboard.read()).find(i => i.types.includes('text/html'));
      const html = await (await item.getType('text/html')).text();
      const doc = new DOMParser().parseFromString(html, 'text/html');
      return {bytes: new Blob([html]).size, sources: [...doc.images].map(i => i.src), titles: doc.querySelectorAll('strong').length};
    });
    assert(clipboard.sources.length > 0);
    assert(clipboard.sources.every(src => new URL(src).origin === origin && src.startsWith('https://')));
    assert(clipboard.bytes < 1024 * 1024, 'Clipboard should contain URLs, not embedded image bytes');
    await context.setOffline(false);
    const pasted = await context.newPage();
    const failures = [];
    pasted.on('requestfailed', request => failures.push({url: request.url(), error: request.failure()?.errorText}));
    await pasted.setContent('<main contenteditable="true"></main>');
    await pasted.locator('main').focus();
    await pasted.keyboard.press(process.platform === 'darwin' ? 'Meta+V' : 'Control+V');
    const progress = setInterval(() => pasted.evaluate(() => ({total: document.images.length, loaded: [...document.images].filter(i => i.complete && i.naturalWidth).length})).then(stats => console.log(JSON.stringify({variant: id, ...stats}))).catch(() => {}), 15000);
    try {
      await pasted.waitForFunction(n => document.images.length === n && [...document.images].every(i => i.complete && i.naturalWidth), clipboard.sources.length, {timeout: 360000});
    } catch (error) {
      console.error(JSON.stringify({failures: failures.slice(0, 5), images: await pasted.evaluate(() => ({total: document.images.length, loaded: [...document.images].filter(i => i.complete && i.naturalWidth).length}))}));
      throw error;
    } finally {
      clearInterval(progress);
    }
    report.push({variant: id, images: clipboard.sources.length, titles: clipboard.titles, clipboardBytes: clipboard.bytes, nativePasteLoaded: true});
    await pasted.close();
  }
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}
