// Run against a generated pure-article preview; never needs a logged-in browser.
import {chromium} from 'playwright';
import assert from 'node:assert/strict';
const url=process.argv[2];
if(!url)throw Error('Usage: node tests/check-layout.mjs http://127.0.0.1:8765/output/article-local.html');
const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||undefined});
const results=[];
async function bounded(page){
  const issues=await page.evaluate(()=>{
    const root=document.querySelector('main');
    return [...root.querySelectorAll('section,svg,img,p')].flatMap(e=>{
      const r=e.getBoundingClientRect(),parent=e.parentElement.getBoundingClientRect();
      return r.width>parent.width+2?[{tag:e.tagName,width:r.width,parent:parent.width,style:e.getAttribute('style')}]:[];
    });
  });
  assert.deepEqual(issues,[],'An internal box is wider than its parent');
}
try{
 for(const width of [320,375,430,768]){
  const page=await browser.newPage({viewport:{width,height:1000}});
  await page.goto(url,{waitUntil:'networkidle'});
  await page.locator('main').evaluate(e=>e.style.overflow='visible');
  const baseline=await page.evaluate(()=>({images:document.images.length,broken:[...document.images].filter(i=>!i.complete||!i.naturalWidth).map(i=>i.src),titles:document.querySelectorAll('strong').length}));
  assert.equal(baseline.broken.length,0,'Image loading failed');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),width,'Document overflows horizontally');
  await bounded(page);
  const folds=page.locator('svg').filter({has:page.locator(':scope > animate')});
  for(let i=0;i<await folds.count();i++){
    const svg=folds.nth(i),before=await svg.boundingBox();
    await svg.locator('rect').first().click({force:true,position:{x:12,y:12}});
    await page.waitForTimeout(2300);
    const after=await svg.boundingBox();
    assert(after.height>before.height+10,'Fold did not open');
    assert(Math.abs(after.width-before.width)<1,'Opening a fold changed its width');
    await bounded(page);
    const clip=await svg.evaluate(e=>{
      let stack=e.parentElement;
      while(stack&&!stack.querySelector('section[style*="height: 0px"],section[style*="height:0"]'))stack=stack.parentElement;
      if(!stack)return null;
      const last=[...stack.querySelectorAll('img')].at(-1);
      return last?{bottom:last.getBoundingClientRect().bottom,frame:stack.getBoundingClientRect().bottom}:null;
    });
    if(clip)assert(clip.bottom<=clip.frame+2,`Last fold image is clipped at ${width}px: ${JSON.stringify(clip)}`);
  }
  const swipes=await page.evaluate(()=>[...document.querySelectorAll('section')].filter(e=>getComputedStyle(e).overflowX==='auto').map(e=>{e.scrollLeft=e.scrollWidth;return {total:e.scrollWidth,client:e.clientWidth,left:e.scrollLeft}}));
  for(const swipe of swipes)if(swipe.total>swipe.client+1)assert(swipe.left>0,'Gallery cannot scroll');
  results.push({width,...baseline,folds:await folds.count(),swipes:swipes.length,internal_overflows:0});
  await page.close();
 }
 console.log(JSON.stringify(results,null,2));
}finally{await browser.close()}
