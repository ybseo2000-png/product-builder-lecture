(function(root) {
  function analyze(research, cache, year, limit=50, minimum=1) {
    const reports = research.items.filter(r => !year || r.year === Number(year));
    const counts = new Map(), pairs = new Map(), documents = new Map();
    const stats = {total:reports.length,ok:0,empty:0,missing:0,failed:0,pending:0};
    for (const report of reports) {
      const saved = cache.reports?.[report.id];
      const state = saved && saved.url === report.url ? saved.status : 'pending';
      stats[state in stats ? state : 'pending']++;
      if (state !== 'ok') continue;
      const terms = [...new Set(saved.keywords.map(x => x.trim()).filter(Boolean))].sort();
      for (const term of terms) {
        counts.set(term,(counts.get(term)||0)+1);
        if (!documents.has(term)) documents.set(term,[]);
        documents.get(term).push(report);
      }
      for (let i=0;i<terms.length;i++) for(let j=i+1;j<terms.length;j++) {
        const key=JSON.stringify([terms[i],terms[j]]);
        pairs.set(key,(pairs.get(key)||0)+1);
      }
    }
    const allNodes = [...counts].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0],'ko')).map(([id,count])=>({id,count}));
    const nodes = allNodes.slice(0,limit);
    const selected = new Set(nodes.map(n=>n.id));
    const edges = [...pairs].filter(([,count])=>count>=minimum).map(([key,count])=>({source:JSON.parse(key)[0],target:JSON.parse(key)[1],count})).filter(e=>selected.has(e.source)&&selected.has(e.target));
    return {nodes,allNodes,edges,stats,documents};
  }
  root.KeywordNetwork={analyze};
  if(typeof module!=='undefined') module.exports={analyze};
})(globalThis);
