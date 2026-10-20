// Reuse the single persistent Chrome window and wait for a manual Weibo login (QR scan).
// The browser is never closed here: the following publish steps re-attach to the same window.
const path = require('node:path');
const { attach, sleep } = require('./browser-session.cjs');

const WAIT_MINUTES = Number(process.env.WEIBO_LOGIN_WAIT_MIN || 10);

(async () => {
  const { ctx, reused, port } = await attach(process.env.WEIBO_PROFILE);
  console.log(JSON.stringify({ step: 'browser', reused, port }));
  const page = ctx.pages()[0] || await ctx.newPage();

  if (!/login/i.test(page.url())) {
    await page.goto('https://weibo.com/login.php', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(4000);
  }
  console.log(JSON.stringify({ step: 'login_window_ready', url: page.url() }));

  const deadline = Date.now() + WAIT_MINUTES * 60 * 1000;
  let nick = null;
  while (Date.now() < deadline) {
    await sleep(5000);
    const state = await page.evaluate(() => {
      const hit = [...document.querySelectorAll('*')].find(e => e.children.length === 0 && e.textContent.trim() === 'Galgame批评');
      return { nick: hit ? hit.textContent.trim() : null, url: location.href, loginForm: /登录|扫码|二维码/.test(document.body.innerText.slice(0, 500)) };
    }).catch(() => ({ nick: null, url: page.url(), loginForm: true }));
    if (state.nick) { nick = state.nick; break; }
    if (!/login/i.test(state.url) && !state.loginForm) {
      // Logged in, but the nickname is not rendered on this page; confirm via the article editor.
      const probe = await ctx.newPage();
      await probe.goto('https://card.weibo.com/article/v3/editor', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await probe.waitForTimeout(6000);
      const n = await probe.evaluate(() => {
        const hit = [...document.querySelectorAll('*')].find(e => e.children.length === 0 && e.textContent.trim() === 'Galgame批评');
        return hit ? hit.textContent.trim() : null;
      }).catch(() => null);
      await probe.close();
      if (n) { nick = n; break; }
    }
  }
  console.log(JSON.stringify({ step: 'login_result', nick: nick || 'TIMEOUT' }));
})().catch(e => { console.error('ERR', e && e.message); process.exit(1); });
