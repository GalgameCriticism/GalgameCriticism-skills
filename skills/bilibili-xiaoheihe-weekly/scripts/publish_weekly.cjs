#!/usr/bin/env node
// Credentials are read only at runtime. No raw request/response/header logging.
const fs = require('node:fs/promises');
const path = require('node:path');
const { createRequire } = require('node:module');

function normalizeCookies(raw) {
  return raw.map(cookie => {
    const c = Object.fromEntries(Object.entries(cookie).map(([key, value]) => [key[0].toLowerCase() + key.slice(1), value]));
    const result = Object.fromEntries(['name', 'value', 'domain', 'path', 'expires', 'httpOnly', 'secure', 'sameSite'].filter(key => c[key] != null).map(key => [key, c[key]]));
    if (typeof result.sameSite === 'number') result.sameSite = ['Strict', 'Lax', 'None'][result.sameSite];
    return result;
  });
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function renderHtml(manifest, uploadedUrls) {
  let index = 0;
  const markup = manifest.blocks.map(block => {
    if (block.type === 'image') {
      const src = uploadedUrls[index++];
      if (!src || !/^https:\/\//.test(src)) throw new Error('Missing uploaded image URL');
      // Native Heybox serialization avoids the generic pasted-img re-upload handler.
      return `<p><img data-type="image" data-original="${escapeHtml(src)}" data-width="${Number(block.width) || ''}" data-height="${Number(block.height) || ''}" data-description=""></p>`;
    }
    const text = block.nodes.map(node => {
      let html = escapeHtml(node.text).replace(/\n/g, '<br>');
      const tags = { bold: 'strong', italic: 'em', underline: 'u', strikethrough: 's' };
      for (const mark of node.marks || []) if (tags[mark]) html = `<${tags[mark]}>${html}</${tags[mark]}>`;
      return html;
    }).join('');
    const tag = block.type === 'heading' ? `h${Math.min(3, (block.level || 1) + 1)}` : 'p';
    return `<${tag}>${text || '<br>'}</${tag}>`;
  }).join('');
  if (index !== uploadedUrls.length) throw new Error('Image mapping count mismatch');
  return markup;
}

async function pasteHtml(editor, html) {
  await editor.click();
  await editor.press('ControlOrMeta+a');
  await editor.evaluate((element, markup) => {
    const clipboardData = new DataTransfer();
    clipboardData.setData('text/html', markup);
    clipboardData.setData('text/plain', new DOMParser().parseFromString(markup, 'text/html').body.innerText);
    element.dispatchEvent(new ClipboardEvent('paste', { bubbles: true, cancelable: true, clipboardData }));
  }, html);
}

async function assertDocument(page, manifest, uploadedUrls) {
  const editor = page.locator('.ProseMirror').nth(1);
  const actualImages = await editor.locator('img').evaluateAll(elements => elements.map(e => e.src.split('?')[0]));
  if (actualImages.length !== uploadedUrls.length || actualImages.some((src, index) => src !== uploadedUrls[index])) throw new Error('Editor image count or order mismatch');
  const actual = (await editor.innerText()).replace(/\s+/g, '');
  const expected = manifest.blocks.filter(b => b.type !== 'image').map(b => b.nodes.map(n => n.text).join('')).join('').replace(/\s+/g, '');
  if (actual !== expected) throw new Error('Editor body differs from the complete source text');
  if ((await page.locator('.ProseMirror').first().innerText()).trim() !== manifest.title) throw new Error('Editor title mismatch');
  return { images: actualImages.length, textCharacters: expected.length };
}

async function uploadImages(page, files) {
  await page.locator('.ProseMirror').nth(1).click();
  await page.locator('.editor-menu-image__btn').click();
  const [chooser] = await Promise.all([page.waitForEvent('filechooser'), page.locator('.editor-image-wrapper__box.upload').click()]);
  await chooser.setFiles(files);
  const deadline = Date.now() + 12 * 60 * 1000;
  while (Date.now() < deadline) {
    const finished = await page.locator('.editor-image-wrapper__box.draggable img').count();
    const pending = await page.locator('.editor-image-wrapper__box-uploading').count();
    console.log(JSON.stringify({ stage: 'upload', finished, expected: files.length, pending }));
    if (finished === files.length && pending === 0) break;
    await page.waitForFunction(expected => document.querySelectorAll('.editor-image-wrapper__box.draggable img').length === expected && document.querySelectorAll('.editor-image-wrapper__box-uploading').length === 0, files.length, { timeout: 15000 }).catch(() => {});
  }
  const urls = await page.locator('.editor-image-wrapper__box.draggable img').evaluateAll(elements => elements.map(e => e.src.split('?')[0]));
  if (urls.length !== files.length || await page.locator('.editor-image-wrapper__box-uploading').count()) throw new Error('Incomplete image upload; retain the draft and inspect before publishing');
  // Large batches can visually overlap the footer; activate the exact confirmed button.
  await page.locator('button.editor-__model-frame-bottom-btn.hb-color__btn--confirm').evaluate(element => element.click());
  await page.locator('.editor-image-wrapper__box.upload').waitFor({ state: 'detached' });
  return urls;
}

async function selectCommunity(page, community) {
  await page.getByRole('button', { name: '添加社区', exact: true }).click();
  await page.locator('.editor__search-input--input').fill(community);
  const items = page.locator('.editor-model__topic-list .editor-model__topic-list-item');
  await items.first().waitFor();
  const matches = [];
  for (let index = 0; index < await items.count(); index++) {
    const text = (await items.nth(index).innerText()).trim();
    if (text.split('\n').some(line => line.trim() === community)) matches.push(index);
  }
  if (matches.length !== 1) throw new Error('Community search did not produce a unique exact match');
  await items.nth(matches[0]).click();
  const selected = await page.locator('.editor__more-info').allTextContents();
  if (!selected.some(text => text.includes(community))) throw new Error('Selected community could not be verified');
}

async function loadPlaywright() {
  if (process.env.PLAYWRIGHT_MODULE_PATH) {
    const requirePackage = createRequire(path.join(path.resolve(process.env.PLAYWRIGHT_MODULE_PATH), 'package.json'));
    return requirePackage('./index.js');
  }
  try { return require('playwright'); } catch { return require('playwright-core'); }
}

function sourceKey(manifest) {
  return `${manifest.source_author_id}:${manifest.article_id}`;
}

function imageKey(url) {
  return url.split('?')[0].replace(/\/thumb\.(png|jpg|jpeg|webp)$/i, '.$1');
}

function isArticleDuplicate(rows, title) {
  const issue = title.match(/(?:周报|速递)\s*(?:第)?\s*(\d+)\s*期/);
  const sameIssue = issue && new RegExp(`(?:^|\\D)${issue[1]}\\s*期`);
  return rows.some(row => row.type?.trim() !== '视频' &&
    (row.title?.trim() === title || (sameIssue && sameIssue.test(row.title || ''))));
}

async function verifyPublished(page, manifest, urls, account, community, postUrl) {
  await page.goto(postUrl, { waitUntil: 'networkidle' });
  const article = page.locator('.hb-article');
  await article.waitFor();
  const author = (await page.locator('.link-user__username').innerText()).trim();
  if (author !== account) throw new Error('Published author mismatch');
  const selected = await page.locator('.link-tags__tag-item .content-tag-text').allTextContents();
  if (!selected.some(text => text.trim() === community)) throw new Error('Published community mismatch');
  if (!await page.getByText(manifest.title, { exact: true }).count()) throw new Error('Published title mismatch');
  const expectedText = manifest.blocks.filter(b => b.type !== 'image').map(b => b.nodes.map(n => n.text).join('')).join('').replace(/\s+/g, '');
  if ((await article.innerText()).replace(/\s+/g, '') !== expectedText) throw new Error('Published text differs from source');
  const images = article.locator('img');
  if (await images.count() !== urls.length) throw new Error('Published image count mismatch');
  // Offscreen images have an empty src until their IntersectionObserver runs.
  for (let index = 0; index < urls.length; index++) {
    await images.nth(index).evaluate(element => element.scrollIntoView({ block: 'center' }));
    await page.waitForFunction(i => document.querySelectorAll('.hb-article img')[i]?.src.includes('imgheybox.max-c.com'), index, { timeout: 10000 });
  }
  const actualUrls = await images.evaluateAll(elements => elements.map(e => e.getAttribute('data-original') || e.src));
  if (actualUrls.some((url, index) => imageKey(url) !== imageKey(urls[index]))) throw new Error('Published image order mismatch');
  return { verifiedTextCharacters: expectedText.length, verifiedImages: urls.length, verifiedImageOrder: true };
}

function argumentsFrom(argv) {
  const args = { publish: false, verify: false };
  for (let index = 0; index < argv.length; index++) {
    const arg = argv[index];
    if (arg === '--publish' || arg === '--verify') args[arg.slice(2)] = true;
    else if (arg === '--account' || arg === '--community') {
      const value = argv[++index];
      if (!value || value.startsWith('--')) throw new Error(`Missing value for ${arg}`);
      args[arg.slice(2)] = value;
    } else if (!arg.startsWith('--') && !args.manifest) args.manifest = path.resolve(arg);
    else throw new Error('Unexpected command-line argument');
  }
  if (!args.manifest || !args.account || !args.community) throw new Error('Usage: publish_weekly.cjs MANIFEST --account NAME --community NAME [--publish | --verify]');
  if (args.publish && args.verify) throw new Error('Choose --publish or --verify');
  return args;
}

async function readJsonIfPresent(file) {
  try { return JSON.parse(await fs.readFile(file, 'utf8')); } catch (error) { if (error.code === 'ENOENT') return null; throw error; }
}

async function main(argv) {
  const args = argumentsFrom(argv);
  const manifest = JSON.parse(await fs.readFile(args.manifest, 'utf8'));
  if (manifest.schema_version !== 1 || [...manifest.title].length > 30) throw new Error('Unsupported manifest or overlong title');
  const directory = path.dirname(args.manifest);
  const receiptFile = path.join(directory, 'publication-receipt.json');
  const uploadedFile = path.join(directory, 'uploaded-images.json');
  const existing = await readJsonIfPresent(receiptFile);
  if (existing && (existing.sourceKey !== sourceKey(manifest) || existing.account !== args.account || existing.community !== args.community)) throw new Error('Existing receipt belongs to another source, account or community');
  if (existing?.status === 'submitting' && !existing.postUrl) throw new Error('An earlier submission has an unknown result; inspect content management before retrying');
  let uploadedUrls = await readJsonIfPresent(uploadedFile);
  const imageBlocks = manifest.blocks.filter(block => block.type === 'image');
  if (uploadedUrls && uploadedUrls.length !== imageBlocks.length) throw new Error('Cached uploaded images do not match the source manifest');
  const cookieFile = process.env.XIAOHEIHE_COOKIE_PATH;
  if (!cookieFile) throw new Error('Set XIAOHEIHE_COOKIE_PATH to a private local Cookie file');
  const rawCookies = JSON.parse(await fs.readFile(cookieFile, 'utf8'));
  const playwright = await loadPlaywright();
  const browser = await playwright.chromium.launch({ headless: true, ...(process.env.XIAOHEIHE_CHROMIUM_PATH ? { executablePath: process.env.XIAOHEIHE_CHROMIUM_PATH } : {}), args: ['--disable-blink-features=AutomationControlled'] });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
    await context.addCookies(normalizeCookies(rawCookies));
    const page = await context.newPage();
    if (existing?.postUrl) {
      if (!uploadedUrls) throw new Error('Published receipt exists without uploaded image mapping; inspect instead of reposting');
      const checked = await verifyPublished(page, manifest, uploadedUrls, args.account, args.community, existing.postUrl);
      const result = { ...existing, ...checked, status: 'published' };
      await fs.writeFile(receiptFile, JSON.stringify(result, null, 2));
      console.log(JSON.stringify({ stage: 'verified_existing', ...result }));
      return;
    }
    if (args.verify) throw new Error('No published receipt to verify');
    const management = await context.newPage();
    await management.goto('https://www.xiaoheihe.cn/creator/content_management/home?article_type=all', { waitUntil: 'networkidle' });
    const rows = await management.locator('.creator-content-item__content').evaluateAll(elements => elements.map(row => ({
      title: row.querySelector('.creator-content-item__title')?.textContent,
      type: row.querySelector('.creator-content-item__type')?.textContent,
    })));
    if (isArticleDuplicate(rows, manifest.title)) throw new Error('This issue already appears as an article in content management; recover its link and verify instead of reposting');
    await page.goto('https://www.xiaoheihe.cn/creator/editor/draft/article', { waitUntil: 'networkidle' });
    await page.locator('.ProseMirror').nth(1).waitFor();
    const author = (await page.locator('.bbs-link-section-author-name').innerText()).trim();
    if (author !== args.account) throw new Error('Cookie belongs to a different target account');
    if (!uploadedUrls) {
      uploadedUrls = await uploadImages(page, imageBlocks.map(block => {
        const imageFile = path.resolve(directory, block.path);
        if (!imageFile.startsWith(directory + path.sep)) throw new Error('Image path escapes the source bundle');
        return imageFile;
      }));
      await fs.writeFile(uploadedFile, JSON.stringify(uploadedUrls));
    }
    await pasteHtml(page.locator('.ProseMirror').first(), `<p>${escapeHtml(manifest.title)}</p>`);
    await pasteHtml(page.locator('.ProseMirror').nth(1), renderHtml(manifest, uploadedUrls));
    const checked = await assertDocument(page, manifest, uploadedUrls);
    await selectCommunity(page, args.community);
    const baseReceipt = { sourceKey: sourceKey(manifest), sourceUrl: manifest.source_url, title: manifest.title, account: args.account, community: args.community, ...checked };
    if (!args.publish) {
      await fs.writeFile(path.join(directory, 'prepared-body.html'), renderHtml(manifest, uploadedUrls));
      await fs.writeFile(receiptFile, JSON.stringify({ ...baseReceipt, status: 'prepared' }, null, 2));
      console.log(JSON.stringify({ stage: 'prepared', ...baseReceipt, note: 'Prepared locally; run --publish when the task authorizes publication.' }));
      return;
    }
    // Mark uncertain submissions before clicking so a timeout cannot trigger blind reposting.
    await fs.writeFile(receiptFile, JSON.stringify({ ...baseReceipt, status: 'submitting' }, null, 2));
    const responsePromise = page.waitForResponse(response => new URL(response.url()).pathname === '/bbs/app/api/link/post' && response.request().method() === 'POST', { timeout: 60000 });
    const [response] = await Promise.all([responsePromise, page.locator('.editor-publish__btn.main-btn').click()]);
    const responseJson = await response.json();
    const id = responseJson.link_id;
    if (!response.ok() || responseJson.status !== 'ok' || !/^\d+$/.test(String(id))) throw new Error('Submission was not confirmed; inspect management before retrying');
    const postUrl = `https://www.xiaoheihe.cn/app/bbs/link/${id}`;
    const submitted = { ...baseReceipt, status: 'submitted', postId: String(id), postUrl };
    await fs.writeFile(receiptFile, JSON.stringify(submitted, null, 2));
    const verified = await verifyPublished(page, manifest, uploadedUrls, args.account, args.community, postUrl);
    await management.reload({ waitUntil: 'networkidle' });
    if (!await management.locator('.creator-content-item__title').filter({ hasText: manifest.title }).count()) throw new Error('Submitted post is not yet visible in management; keep receipt and verify later');
    const result = { ...submitted, ...verified, status: 'published', publishedAt: new Date().toISOString() };
    await fs.writeFile(receiptFile, JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result));
  } finally {
    await browser.close();
  }
}

module.exports = { normalizeCookies, renderHtml, pasteHtml, assertDocument, uploadImages, selectCommunity, loadPlaywright, sourceKey, imageKey, isArticleDuplicate, verifyPublished, main };
if (require.main === module) main(process.argv.slice(2)).catch(() => {
  // Playwright exceptions may contain user paths, URLs or request metadata.
  console.error('Workflow stopped. Inspect the local receipt and browser state before retrying. Cookie values and raw responses are intentionally omitted.');
  process.exitCode = 1;
});
