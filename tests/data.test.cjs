const { test } = require('node:test');
const assert = require('node:assert/strict');
const { validateDataset } = require('../assets/data.js');
const item = {id:'fixture-1',year:2026,title:'테스트 자료',org:'문화체육관광부',industryCodes:['1169'],url:'https://www.g2b.go.kr/'};
function fixture() { return {kind:'bids',status:'ready',period:{start:'2022-01-01',end:'2026-12-31'},updatedAt:'2026-10-21T00:00:00Z',sources:['테스트 출처'],items:[{...item}]}; }
test('accept matching agency and code; reject incorrect agency or code', () => {
  assert.doesNotThrow(() => validateDataset(fixture(),'bids'));
  for (const changes of [{org:'다른 기관'},{industryCodes:['11690']}]) {
    const d=fixture();Object.assign(d.items[0],changes);assert.throws(()=>validateDataset(d,'bids'));
  }
});
test('reject duplicate notices, out-of-range years and unsafe links', () => {
  for (const change of [d=>d.items.push({...item}),d=>d.items[0].year=2021,d=>d.items[0].url='javascript:alert(1)']) {
    const d=fixture();change(d);assert.throws(()=>validateDataset(d,'bids'));
  }
});
test('pending is distinct from verified empty data', () => {
  const d=fixture();d.status='pending';assert.throws(()=>validateDataset(d,'bids'));
  d.items=[];assert.doesNotThrow(()=>validateDataset(d,'bids'));
  d.status='ready';d.updatedAt=null;assert.throws(()=>validateDataset(d,'bids'));
});
