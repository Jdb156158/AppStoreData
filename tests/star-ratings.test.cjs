const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = vm.createContext({document:{getElementById:()=>({addEventListener(){}})},window:{}});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../star-ratings.js'),'utf8'),context);
const sample = {status:'ok',country:'us',scope:'current_cumulative',byStar:[10,5,14,23,48],total:100};

test('star rate uses all stars including unwritten ratings, not written-review counts',()=>{
  const result = context.cumulativeStarRate({...sample,writtenReviewCount:4,negativeWrittenReviewCount:3});
  assert.equal(result.total,100);
  assert.equal(result.negative,29);
  assert.ok(Math.abs(result.percent-29)<1e-10);
});

test('missing, wrong-region, wrong-period, inconsistent and negative counts do not produce a rate',()=>{
  for (const candidate of [null,{...sample,status:'unavailable'},{...sample,country:'cn'},
    {...sample,scope:'last30days'},{...sample,total:99},{...sample,byStar:[10,5,14,23]},
    {...sample,byStar:[-10,5,14,23,48]},{...sample,total:0,byStar:[0,0,0,0,0]}]) {
    assert.equal(context.cumulativeStarRate(candidate),null);
  }
});
