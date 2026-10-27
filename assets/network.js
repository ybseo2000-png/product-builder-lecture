(async function(){
  const el=id=>document.getElementById(id), ns='http://www.w3.org/2000/svg';
  let research,cache,model,selected=null,shown=20,zoom=1;
  function svg(tag,attrs){const n=document.createElementNS(ns,tag);for(const [k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;}
  function button(text,fn){const b=document.createElement('button');b.type='button';b.textContent=text;b.onclick=fn;return b;}
  function choose(id){selected=id;shown=20;details();highlight();terms();}
  function details(){
    el('neighbors').replaceChildren();el('report-list').replaceChildren();
    if(!selected){el('selected-title').textContent='주제어를 선택하세요';el('selected-summary').textContent='네트워크의 점이나 주제어 목록을 선택하세요.';el('more-reports').hidden=true;return;}
    const docs=model.documents.get(selected)||[];
    el('selected-title').textContent=selected;el('selected-summary').textContent=`현재 기간의 관련 보고서 ${docs.length}건 · 연결은 현재 표시 조건 기준`;
    const neighbors=model.edges.filter(e=>e.source===selected||e.target===selected).sort((a,b)=>b.count-a.count);
    for(const e of neighbors){const id=e.source===selected?e.target:e.source;el('neighbors').append(button(`${id} · ${e.count}건`,()=>choose(id)));}
    for(const r of docs.slice(0,shown)){
      const box=document.createElement('div');box.className='report-item';const a=document.createElement('a');
      try{const u=new URL(r.url);if(u.protocol!=='https:')continue;}catch{continue;}
      a.href=r.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=r.title;
      const p=document.createElement('p');p.textContent=`${r.year} · ${r.org}`;box.append(a,p);el('report-list').append(box);
    }
    el('more-reports').hidden=docs.length<=shown;
  }
  function terms(){el('term-list').replaceChildren();const q=el('term-search').value.trim().toLowerCase();for(const n of model.allNodes.filter(n=>n.id.toLowerCase().includes(q))){const b=button(`${n.id} · ${n.count}`,()=>choose(n.id));b.setAttribute('aria-pressed',String(n.id===selected));el('term-list').append(b);}}
  function highlight(){
    const q=el('term-search').value.trim().toLowerCase();const adjacent=new Set([selected]);for(const e of model.edges)if(e.source===selected||e.target===selected){adjacent.add(e.source);adjacent.add(e.target);}
    for(const n of el('graph').querySelectorAll('.node')){n.classList.toggle('dim',(selected&&!adjacent.has(n.dataset.term))||!!(q&&!n.dataset.term.toLowerCase().includes(q)));n.classList.toggle('selected',n.dataset.term===selected);}
  }
  function draw(){
    const graph=el('graph');graph.replaceChildren();zoom=1;setZoom();
    const nodes=model.nodes.map((n,i)=>({...n,x:450+245*Math.cos(i*2*Math.PI/model.nodes.length),y:325+225*Math.sin(i*2*Math.PI/model.nodes.length)}));
    const lookup=new Map(nodes.map(n=>[n.id,n]));
    // 제한된 횟수의 스프링 배치로 외부 라이브러리 없이 그립니다.
    for(let step=0;step<180;step++){
      const force=nodes.map(()=>({x:0,y:0}));
      for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){
        const dx=nodes[i].x-nodes[j].x,dy=nodes[i].y-nodes[j].y,d2=Math.max(64,dx*dx+dy*dy),f=25/d2;
        force[i].x+=dx*f;force[i].y+=dy*f;force[j].x-=dx*f;force[j].y-=dy*f;
      }
      const index=new Map(nodes.map((n,i)=>[n.id,i]));
      for(const e of model.edges){const a=lookup.get(e.source),b=lookup.get(e.target),dx=b.x-a.x,dy=b.y-a.y;const distance=Math.max(1,Math.hypot(dx,dy));const f=.018*(distance-90)/distance*Math.min(2,Math.sqrt(e.count));force[index.get(a.id)].x+=dx*f;force[index.get(a.id)].y+=dy*f;force[index.get(b.id)].x-=dx*f;force[index.get(b.id)].y-=dy*f;}
      nodes.forEach((n,i)=>{n.x=Math.max(75,Math.min(825,n.x+Math.max(-8,Math.min(8,force[i].x+(450-n.x)*.015))));n.y=Math.max(45,Math.min(590,n.y+Math.max(-8,Math.min(8,force[i].y+(325-n.y)*.015))));});
    }
    for(const e of model.edges){const a=lookup.get(e.source),b=lookup.get(e.target);const line=svg('line',{x1:a.x,y1:a.y,x2:b.x,y2:b.y,stroke:'#8b9ab0','stroke-opacity':'.45','stroke-width':Math.min(7,.6+Math.sqrt(e.count))});const title=svg('title',{});title.textContent=`${e.source} ↔ ${e.target}: ${e.count}개 보고서`;line.append(title);graph.append(line);}
    for(const n of nodes){const g=svg('g',{class:'node',tabindex:0,role:'button','aria-label':`${n.id}, ${n.count}개 보고서`});g.dataset.term=n.id;g.append(svg('circle',{cx:n.x,cy:n.y,r:Math.min(25,7+Math.sqrt(n.count)*2),fill:'#304f78'}));const text=svg('text',{x:n.x,y:n.y+34,'text-anchor':'middle'});text.textContent=n.id.length>15?n.id.slice(0,14)+'…':n.id;g.append(text);const title=svg('title',{});title.textContent=`${n.id}: ${n.count}개 보고서`;g.append(title);g.onclick=()=>choose(n.id);g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(n.id);}};graph.append(g);}
    el('graph-empty').hidden=nodes.length!==0;el('graph-count').textContent=`주제어 ${nodes.length}개 · 관계 ${model.edges.length}개`;
  }
  function setZoom(){const w=900/zoom,h=650/zoom;el('graph').setAttribute('viewBox',`${450-w/2} ${325-h/2} ${w} ${h}`);}
  function render(){
    model=KeywordNetwork.analyze(research,cache,el('period').value,Number(el('node-limit').value),Number(el('min-count').value));selected=null;
    const s=model.stats,pct=s.total?Math.round(s.ok/s.total*100):0;
    el('coverage').textContent=`대상 ${s.total}건 · 주제어 확보 ${s.ok}건 (${pct}%) · 주제어 없음 ${s.empty}건 · 항목 미확인 ${s.missing}건 · 접속 실패 ${s.failed}건 · 미수집 ${s.pending}건`;
    draw();terms();details();highlight();
  }
  try{
    [research,cache]=await Promise.all(['data/research.json','data/keywords.json'].map(async url=>{const r=await fetch(url,{cache:'no-cache'});if(!r.ok)throw Error();return r.json();}));
    if(!Array.isArray(research.items)||!cache.reports)throw Error();
    if(research.coverageNote){const note=document.createElement('p');note.className='collection-note';note.textContent='※ '+research.coverageNote;el('coverage-note').append(note);}
    render();
    for(const id of ['period','node-limit','min-count'])el(id).addEventListener('change',render);
    el('term-search').addEventListener('input',()=>{terms();highlight();});
    el('more-reports').onclick=()=>{shown+=20;details();};el('zoom-in').onclick=()=>{zoom=Math.min(3,zoom*1.3);setZoom();};el('zoom-out').onclick=()=>{zoom=Math.max(.6,zoom/1.3);setZoom();};el('zoom-reset').onclick=()=>{zoom=1;setZoom();};
  }catch{el('coverage').textContent='분석 자료를 불러오지 못했습니다. 잠시 후 새로고침해 주세요.';}
})();
