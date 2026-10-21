const {test}=require('node:test');
const assert=require('node:assert/strict');
const {analyze}=require('../assets/network-data.js');
const reports={items:[{id:'a',year:2022,url:'https://nkis.re.kr/a'},{id:'b',year:2023,url:'https://nkis.re.kr/b'},{id:'c',year:2022,url:'https://nkis.re.kr/c'},{id:'d',year:2022,url:'https://nkis.re.kr/d'}]};
const cache={reports:{a:{url:reports.items[0].url,status:'ok',keywords:['관광','지역','관광']},b:{url:reports.items[1].url,status:'ok',keywords:['지역','관광','문화']},c:{url:reports.items[2].url,status:'empty',keywords:[]}}};
test('year filtering and within-report deduplication',()=>{const m=analyze(reports,cache,2022);assert.equal(m.nodes.find(n=>n.id==='관광').count,1);assert.equal(m.edges.length,1);assert.equal(m.edges[0].count,1);assert.deepEqual(m.stats,{total:3,ok:1,empty:1,missing:0,failed:0,pending:1});});
test('integrated period counts cooccurrence and related documents',()=>{const m=analyze(reports,cache,'',50,2);assert.equal(m.edges.length,1);assert.equal(m.edges[0].count,2);assert.equal(m.documents.get('관광').length,2);});
test('empty year and stale cached URL are excluded',()=>{assert.equal(analyze(reports,cache,2026).nodes.length,0);const changed=structuredClone(cache);changed.reports.a.url='https://nkis.re.kr/changed';const m=analyze(reports,changed,2022);assert.equal(m.stats.ok,0);assert.equal(m.stats.pending,2);});
