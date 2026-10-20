// One-shot Weibo headline-article pipeline: launch the profile's Chrome once, compose, verify, publish.
// Everything runs in a single browser session, so the window is opened once per task and never restarted.
const path = require('node:path');
const fs = require('node:fs');
const { attach } = require('./browser-session.cjs');

const args = { publish: false };
for (let i = 2; i < process.argv.length; i++) {
  const a = process.argv[i];
  if (a === '--publish') args.publish = true;
  else if (a.startsWith('--')) args[a.slice(2)] = process.argv[++i];
}
if (!args.manifest) throw new Error('--manifest <manifest.json> is required');

const manifest = JSON.parse(fs.readFileSync(args.manifest, 'utf8'));
const payloadDir = path.dirname(args.manifest);
const optDir = args.optimized;
const receiptFile = path.join(payloadDir, 'weibo-receipt.json');
const account = process.env.WEIBO_ACCOUNT || 'Galgame批评';
const log = o => console.log(JSON.stringify({ t: new Date().toISOString(), ...(typeof o === 'string' ? { msg: o } : o) }));
const sleep = ms => new Promise(r => setTimeout(r, ms));

const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const marks = node => {
  let h = esc(node.text);
  for (const m of node.marks || []) {
    if (m === 'bold') h = `<strong>${h}</strong>`;
    if (m === 'italic') h = `<em>${h}</em>`;
    if (m === 'underline') h = `<u>${h}</u>`;
  }
  return h;
};

const blocks = manifest.blocks.slice();
if (blocks.length && blocks[0].type !== 'image' && blocks[0].nodes.map(n => n.text).join('').trim() === manifest.source_title.trim()) blocks.shift();

const title = (args.title || manifest.source_title).slice(0, 32);
const summary = (args.summary || '').slice(0, 44);

let imgIndex = 0;
const imageFiles = [];
const htmlParts = [];
for (const b of blocks) {
  if (b.type === 'image') {
    imgIndex++;
    const optimized = optDir ? path.join(optDir, path.basename(b.path).replace(/\.(png|jpg|jpeg)$/i, '.jpg')) : null;
    const file = optimized && fs.existsSync(optimized) ? optimized : path.join(payloadDir, b.path);
    imageFiles.push(file);
    htmlParts.push(`<p>WBIMGPH_${imgIndex}</p>`);
    continue;
  }
  const inner = b.nodes.map(marks).join('') || '<br>';
  const tag = b.type === 'heading' ? 'h2' : 'p';
  htmlParts.push(`<${tag}>${inner}</${tag}>`);
}
const html = htmlParts.join('');
const expectedImages = imageFiles.length;
const expectedText = blocks.filter(b => b.type !== 'image').map(b => b.nodes.map(n => n.text).join('')).join('').replace(/\s+/g, '');

const stats = page => page.evaluate(() => {
  const root = document.querySelector('.ProseMirror');
  if (!root) return null;
  const figures = [...root.querySelectorAll('figure')];
  const srcs = figures.map(f => { const i = f.querySelector('img'); return i ? (i.currentSrc || i.src) : ''; });
  return {
    figures: figures.length,
    srcs,
    hosted: srcs.filter(u => /^https?:\/\//.test(u) && !/tc2\.service/.test(u)).length,
    text: root.innerText.replace(/WBIMGPH_\d+/g, '').replace(/\s+/g, ''),
    placeholders: (root.innerText.match(/WBIMGPH_\d+/g) || []).length,
    title: (document.querySelector('textarea[placeholder*="请输入标题"]') || {}).value || null,
  };
});

// Real mouse click on the placeholder text: ProseMirror only honours its own selection,
// so the token must be selected with real input before the synthetic image paste.
const tokenRect = (page, n) => page.evaluate(idx => {
  const root = document.querySelector('.ProseMirror');
  const token = `WBIMGPH_${idx}`;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node = null;
  while ((node = walker.nextNode())) if (node.nodeValue.includes(token)) break;
  if (!node) return null;
  node.parentElement.scrollIntoView({ block: 'center' });
  const start = node.nodeValue.indexOf(token);
  const r = document.createRange();
  r.setStart(node, start);
  r.setEnd(node, start + 1);
  const b = r.getBoundingClientRect();
  return { x: Math.round(b.x + 2), y: Math.round(b.y + b.height / 2), len: token.length };
}, n);

(async () => {
  const { ctx, port, reused } = await attach(process.env.WEIBO_PROFILE, process.env.CHROME_DEBUG_PORT || 9333);
  log({ step: 'browser', reused, port });
  const page = ctx.pages()[0] || await ctx.newPage();

  await page.goto('https://card.weibo.com/article/v3/editor', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await sleep(7000);
  const writeBtn = page.getByText('写文章', { exact: true }).first();
  if (await writeBtn.count()) { await writeBtn.click().catch(() => {}); await sleep(5000); }

  const nick = await page.evaluate(() => {
    const hit = [...document.querySelectorAll('*')].find(e => e.children.length === 0 && e.textContent.trim() === 'Galgame批评');
    return hit ? hit.textContent.trim() : null;
  }).catch(() => null);
  log({ step: 'identity', nick, url: page.url() });
  if (nick !== account) throw new Error(`Unexpected weibo account: ${nick}`);

  const editor = page.locator('.ProseMirror').first();
  await editor.waitFor({ timeout: 30000 });
  await editor.click();
  await sleep(800);

  const titleInput = page.locator('textarea[placeholder*="请输入标题"]').first();
  await titleInput.click();
  await titleInput.fill(title);
  log({ step: 'title_set', title, len: title.length });

  if (summary) {
    const summaryBox = page.locator('textarea[placeholder*="导语"]').first();
    if (await summaryBox.count()) {
      await summaryBox.click();
      await page.keyboard.type(summary);
      log({ step: 'summary_set', len: summary.length });
    }
  }

  await editor.click();
  await page.evaluate(h => {
    const el = document.querySelector('.ProseMirror');
    el.focus();
    const dt = new DataTransfer();
    dt.setData('text/html', h);
    dt.setData('text/plain', h.replace(/<[^>]+>/g, ''));
    el.dispatchEvent(new ClipboardEvent('paste', { bubbles: true, cancelable: true, clipboardData: dt }));
  }, html);
  await sleep(3000);
  let s = await stats(page);
  log({ step: 'body_pasted', placeholders: s.placeholders, chars: s.text.length, expectedChars: expectedText.length });
  if (s.placeholders !== expectedImages) throw new Error(`Placeholder count ${s.placeholders} != ${expectedImages}`);

  for (let n = 1; n <= expectedImages; n++) {
    const file = imageFiles[n - 1];
    // Scrolling changes the layout, so locate the token twice and only trust the post-scroll rect.
    let rect = await tokenRect(page, n);
    if (!rect) throw new Error(`Placeholder ${n} not found`);
    await sleep(700);
    rect = await tokenRect(page, n);
    if (!rect) throw new Error(`Placeholder ${n} lost after scroll`);

    let selected = '';
    for (let attempt = 1; attempt <= 3; attempt++) {
      await page.mouse.click(rect.x, rect.y);
      await sleep(300);
      for (let k = 0; k < rect.len; k++) await page.keyboard.press('Shift+ArrowRight');
      await sleep(200);
      selected = await page.evaluate(() => window.getSelection().toString());
      if (selected === `WBIMGPH_${n}`) break;
      log({ step: 'reselect', index: n, attempt, selected });
      rect = await tokenRect(page, n);
      if (!rect) throw new Error(`Placeholder ${n} vanished while reselecting`);
    }
    if (selected !== `WBIMGPH_${n}`) throw new Error(`Could not select placeholder ${n} (got "${selected}")`);
    await page.keyboard.press('Backspace');
    await sleep(300);

    const b64 = fs.readFileSync(file).toString('base64');
    await page.evaluate(async ([data, name]) => {
      const root = document.querySelector('.ProseMirror');
      const bin = atob(data);
      const arr = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
      const dt = new DataTransfer();
      dt.items.add(new File([arr], name, { type: 'image/jpeg' }));
      root.focus();
      root.dispatchEvent(new ClipboardEvent('paste', { bubbles: true, cancelable: true, clipboardData: dt }));
    }, [b64, path.basename(file)]);

    let uploaded = false;
    const deadline = Date.now() + 180000;
    while (Date.now() < deadline) {
      await sleep(2000);
      const st = await stats(page);
      const src = st.srcs[n - 1] || '';
      if (st.figures >= n && /^https?:\/\//.test(src) && !/tc2\.service/.test(src)) { uploaded = true; break; }
    }
    log({ step: 'image', index: n, total: expectedImages, uploaded });
    if (!uploaded) throw new Error(`Image ${n} did not finish uploading`);
  }

  s = await stats(page);
  const textOk = s.text === expectedText;
  log({ step: 'verify', figures: s.figures, hosted: s.hosted, placeholders: s.placeholders, chars: s.text.length, expectedChars: expectedText.length, textOk });
  await page.screenshot({ path: path.join(payloadDir, 'weibo-composed.png') });

  const state = { title, summary, images: s.figures, hosted: s.hosted, textChars: s.text.length, expectedImages, expectedChars: expectedText.length, textOk, url: page.url(), at: new Date().toISOString() };
  if (!args.publish) {
    fs.writeFileSync(receiptFile, JSON.stringify({ ...state, status: 'prepared' }, null, 2));
    log({ step: 'prepared' });
    await ctx.browser().close();
    return;
  }
  if (!textOk || s.hosted !== expectedImages || s.placeholders !== 0) throw new Error('Fidelity gate failed; not publishing');

  fs.writeFileSync(receiptFile, JSON.stringify({ ...state, status: 'submitting' }, null, 2));

  // v5 renders the publish settings inline; the 下一步 control is often a div, so click through the DOM.
  const clickByText = (label) => page.evaluate(l => {
    const cands = [...document.querySelectorAll('button, [role="button"], div, span, a')]
      .filter(e => e.textContent.trim() === l && e.children.length === 0);
    const el = cands.pop();
    if (!el) return false;
    (el.closest('button') || el).click();
    return true;
  }, label);

  log({ step: 'next_clicked', ok: await clickByText('下一步') });
  await sleep(6000);
  log({ step: 'settings', url: page.url() });
  await page.screenshot({ path: path.join(payloadDir, 'weibo-settings.png') });
  log({ step: 'settings_ui', ...(await page.evaluate(() => ({
    buttons: [...document.querySelectorAll('button')].map(b => b.textContent.trim()).filter(Boolean).slice(0, 40),
    modals: [...document.querySelectorAll('[class*="modal"], [class*="Modal"], [class*="dialog"]')].map(m => m.innerText.slice(0, 100)).slice(0, 3),
  }))) });

  if (args.cover) {
    const coverEntry = page.getByText('设置封面', { exact: false }).first();
    if (await coverEntry.count()) {
      await coverEntry.click().catch(() => {});
      await sleep(2000);
      const input = page.locator('input[type=file]').first();
      if (await input.count()) {
        await input.setInputFiles(args.cover);
        await sleep(8000);
        log({ step: 'cover_uploaded' });
      }
    }
  }

  log({ step: 'publish_clicked', ok: await clickByText('发布') });
  await sleep(4000);
  // confirmation dialog
  const confirmed = await page.evaluate(() => {
    const dlg = [...document.querySelectorAll('[class*="modal"] button, [class*="dialog"] button, .woo-dialog button')]
      .filter(b => /发布|确认/.test(b.textContent.trim()));
    if (!dlg.length) return false;
    dlg[dlg.length - 1].click();
    return true;
  });
  log({ step: 'confirm', clicked: confirmed });

  for (let i = 0; i < 45; i++) {
    await sleep(2000);
    if (/ttarticle\/p\/show/.test(page.url())) break;
  }
  log({ step: 'after_publish', url: page.url() });
  await page.screenshot({ path: path.join(payloadDir, 'weibo-published.png') });
  fs.writeFileSync(receiptFile, JSON.stringify({ ...state, status: /ttarticle\/p\/show/.test(page.url()) ? 'published' : 'unknown', afterUrl: page.url() }, null, 2));
  await ctx.browser().close();
})().catch(e => { console.error('ERR', e && e.message); process.exit(1); });
