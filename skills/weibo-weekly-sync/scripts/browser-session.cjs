// Reusable Chrome session: attach to an already-running debug instance instead of relaunching.
// All publish steps share one Chrome window per profile, so the browser is never restarted between steps.
const path = require('node:path');
const { spawn } = require('node:child_process');
const { createRequire } = require('node:module');
const requirePackage = createRequire(path.join(process.env.PLAYWRIGHT_MODULE_PATH, 'package.json'));
const { chromium } = requirePackage('./index.js');

const sleep = ms => new Promise(r => setTimeout(r, ms));
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

async function connect(port) {
  try {
    return await chromium.connectOverCDP(`http://127.0.0.1:${port}`, { timeout: 5000 });
  } catch {
    return null;
  }
}

async function waitForPort(port, timeoutMs = 45000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const b = await connect(port);
    if (b) return b;
    await sleep(600);
  }
  return null;
}

/**
 * Attach to the profile's Chrome, launching it once (detached) if it is not running.
 * Returns { browser, ctx, reused }. Never closes the browser; callers leave it open.
 */
async function attach(profileDir, port) {
  const debugPort = Number(port || process.env.CHROME_DEBUG_PORT || 9333);
  let browser = await connect(debugPort);
  if (browser) return { browser, ctx: browser.contexts()[0], reused: true, port: debugPort };

  spawn(CHROME, [
    `--user-data-dir=${profileDir}`,
    `--remote-debugging-port=${debugPort}`,
    '--no-sandbox',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-blink-features=AutomationControlled',
    '--start-maximized',
    'about:blank',
  ], { detached: true, stdio: 'ignore' }).unref();

  browser = await waitForPort(debugPort);
  if (!browser) throw new Error(`Chrome debug port ${debugPort} not ready for ${profileDir}`);
  return { browser, ctx: browser.contexts()[0], reused: false, port: debugPort };
}

async function getPage(ctx, url) {
  const pages = ctx.pages();
  const page = pages[0] || await ctx.newPage();
  if (url) {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  }
  return page;
}

module.exports = { attach, connect, getPage, sleep };
