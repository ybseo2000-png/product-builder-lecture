const {test}=require('node:test'),assert=require('node:assert/strict');
const {selectPage,pageNumbers}=require('../assets/research-list.js');
const items=Array.from({length:65},(_,i)=>({id:String(i),year:i<30?2022:2023,title:i===0?'관광 정책':`연구 ${i}`,org:i===1?'관광 기관':'시험기관'}));
test('30 rows per page and final remainder without duplicates',()=>{const pages=[1,2,3].map(page=>selectPage(items,{page}));assert.deepEqual(pages.map(p=>p.items.length),[30,30,5]);assert.equal(new Set(pages.flatMap(p=>p.items.map(i=>i.id))).size,65);});
test('all/title/organization searches select different reports',()=>{assert.equal(selectPage(items,{query:'관광'}).count,2);assert.equal(selectPage(items,{query:'관광',scope:'title'}).items[0].id,'0');assert.equal(selectPage(items,{query:'관광',scope:'org'}).items[0].id,'1');});
test('year combines with scope and empty results have zero pages',()=>{assert.equal(selectPage(items,{year:2023,scope:'org',query:'관광'}).pages,0);assert.equal(selectPage(items,{year:2022}).count,30);});
test('page clamping and compact numbered navigation include last',()=>{assert.equal(selectPage(items,{page:100}).page,3);assert.deepEqual(pageNumbers(1,113),[1,2,3,4,5,'…',113]);assert.deepEqual(pageNumbers(113,113),[1,'…',109,110,111,112,113]);});
