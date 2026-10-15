const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = vm.createContext({document:{getElementById:()=>({addEventListener(){}})},window:{}});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../review-analysis.js'),'utf8'),context);
const snapshot = {country:'us',source:{kind:'written_reviews'},window:{startAt:'2026-09-14T10:42:04Z',endAt:'2026-10-14T10:42:04Z'}};
const sample = {country:'us',status:'ok',writtenReviewCount:4,negativeWrittenReviewCount:3,reviews:[{stars:1}]};

test('rate uses all collected written comments, not the displayed negative examples or lifetime ratings',()=>{
  const result = context.writtenReviewRate({...sample,ratings:{byStar:[100,100,100,100,100]}},snapshot);
  assert.equal(result.total,4);
  assert.equal(result.negative,3);
  assert.equal(result.percent,75);
});

test('partial samples produce a sample rate; no negative comments gives a real 0 percent',()=>{
  assert.equal(context.writtenReviewRate({...sample,status:'partial'},snapshot).percent,75);
  assert.equal(context.writtenReviewRate({...sample,negativeWrittenReviewCount:0},snapshot).percent,0);
});

test('empty, unavailable, invalid counts and wrong-region data stay unknown',()=>{
  for (const candidate of [null,{...sample,status:'unavailable'},{...sample,country:'cn'},
    {...sample,writtenReviewCount:0},{...sample,negativeWrittenReviewCount:5},
    {...sample,negativeWrittenReviewCount:-1},{...sample,negativeWrittenReviewCount:null}]) {
    assert.equal(context.writtenReviewRate(candidate,snapshot),null);
  }
  assert.equal(context.writtenReviewRate(sample,{...snapshot,source:{kind:'all_ratings'}}),null);
});
