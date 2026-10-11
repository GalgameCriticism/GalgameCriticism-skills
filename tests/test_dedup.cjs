const assert = require('node:assert/strict');
const mod = require('../skills/bilibili-xiaoheihe-weekly/scripts/publish_weekly.cjs');
assert.equal(typeof mod.isArticleDuplicate, 'function', 'Content-type-aware article deduplication is missing');
assert.equal(mod.isArticleDuplicate([{title:'周报12期', type:'视频'}], '周报12期'), false);
assert.equal(mod.isArticleDuplicate([{title:'周报12期', type:'文章'}], '周报12期'), true);
assert.equal(mod.isArticleDuplicate([{title:'Gal周报12期 不同简称', type:'文章'}], '【Gal周报12期】'), true);
assert.equal(mod.isArticleDuplicate([{title:'周报13期', type:'文章'}], '周报12期'), false);
assert.equal(mod.isArticleDuplicate([{title:'周报112期', type:'文章'}], '周报12期'), false, 'A different issue with a shared number suffix must not match');
console.log('Article/video deduplication checks passed');
