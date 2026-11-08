// Checks the actual preview file with no network and no adjacent asset files.
import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const source=process.argv[2];
if(!source)throw Error('Usage: node tests/check-local-copy.mjs <output/preview.html>');
const directory=fs.mkdtempSync(path.join(os.tmpdir(),'wechat-copy-check-'));
const isolated=path.join(directory,'preview.html');fs.copyFileSync(source,isolated);
const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||undefined});
try{
 const context=await browser.newContext({permissions:['clipboard-read','clipboard-write'],offline:true});
 const requests=[];await context.route('**/*',route=>{const url=route.request().url();if(/^https?:/.test(url)){requests.push(url);return route.abort()}return route.continue()});
 const page=await context.newPage();await page.goto(pathToFileURL(isolated).href,{waitUntil:'load'});
 await page.waitForFunction(()=>[...document.querySelectorAll('#article img')].every(i=>i.complete&&i.naturalWidth));
 const expected=await page.locator('#article img').count();assert(expected>0);
 const results={previewImages:expected,variants:[],externalRequests:requests};
 for(const [id,label] of [['copy','standard'],['copy-safe','compatible']]){
  await page.locator('#'+id).click();await page.waitForFunction(id=>!document.getElementById(id).disabled,id);
  assert((await page.locator('#toast').textContent()).includes('已复制'));
  const clipboard=await page.evaluate(async()=>{
   const items=await navigator.clipboard.read();const item=items.find(i=>i.types.includes('text/html'));assertClipboard(item);
   const text=await(await item.getType('text/html')).text();const doc=new DOMParser().parseFromString(text,'text/html');
   function assertClipboard(value){if(!value)throw Error('No HTML on clipboard')}
   return {images:doc.images.length,embedded:[...doc.images].every(i=>i.src.startsWith('data:image/')),titles:doc.querySelectorAll('strong').length};
  });
  assert(clipboard.images>0&&clipboard.embedded);
  const pasted=await context.newPage();await pasted.setContent('<main contenteditable="true"></main>');
  await pasted.locator('main').focus();await pasted.keyboard.press(process.platform==='darwin'?'Meta+V':'Control+V');
  await pasted.waitForFunction(n=>document.images.length===n&&[...document.images].every(i=>i.complete&&i.naturalWidth),clipboard.images);
  assert(await pasted.evaluate(()=>[...document.images].every(i=>i.src.startsWith('data:image/'))));
  results.variants.push({variant:label,images:clipboard.images,titles:clipboard.titles,embedded:true,nativePasteImages:await pasted.locator('img').count()});
  await pasted.close();
 }
 assert.deepEqual(requests,[]);console.log(JSON.stringify(results,null,2));
}finally{await browser.close();fs.rmSync(directory,{recursive:true,force:true})}
