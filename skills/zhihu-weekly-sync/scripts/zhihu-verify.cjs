// Verify the public Zhihu article: title, author, body text and image order.
const path = require('node:path');
const fs = require('node:fs');
const { attach } = require('./browser-session.cjs');

const manifest = JSON.parse(fs.readFileSync(process.env.MANIFEST, 'utf8'));
const blocks = manifest.blocks.slice();
if (blocks.length && blocks[0].type !== 'image' && blocks[0].nodes.map(n => n.text).join('').trim() === manifest.source_title.trim()) blocks.shift();
const expectedText = blocks.filter(b => b.type !== 'image').map(b => b.nodes.map(n => n.text).join('')).join('').replace(/\s+/g, '');
const expectedImages = blocks.filter(b => b.type === 'image').length;

(async () => {
  const { ctx } = await attach(process.env.ZHIHU_PROFILE, process.env.ZHIHU_DEBUG_PORT || 9444);
  const page = await ctx.newPage();
  await page.goto(process.env.ARTICLE, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(4000);
  const title = (await page.locator('h1.Post-Title').innerText().catch(() => '')).trim();
  const author = (await page.locator('.AuthorInfo-name').innerText().catch(() => '')).trim();
  const body = page.locator('.Post-RichTextContainer .RichText');
  await body.waitFor({ timeout: 30000 });
  const text = (await body.innerText()).replace(/\s+/g, '');
  const imgs = await body.locator('img').evaluateAll(els => els.map(e => e.currentSrc || e.src));
  const ids = imgs.map(u => (u.match(/v2-[0-9a-f]{32}/) || [''])[0]);
  const unique = new Set(ids.filter(Boolean));
  console.log(JSON.stringify({
    url: page.url(),
    title,
    titleOk: title === manifest.source_title,
    author,
    authorOk: author === 'Galgame批评',
    textChars: text.length,
    textOk: text === expectedText,
    images: imgs.length,
    uniqueImageIds: unique.size,
    expectedImages,
    sampleImg: imgs[0] ? imgs[0].slice(0, 80) : null,
  }, null, 2));
  await page.close();
})().catch(e => { console.error('ERR', e && e.message); process.exit(1); });
