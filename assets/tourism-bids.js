(async function(){
 const el=id=>document.getElementById('tourism-'+id);let data,page=1;const size=10;
 function render(){
  const q=el('search').value.trim().toLocaleLowerCase('ko'),scope=el('scope').value,year=el('year').value,type=el('type').value,classification=el('classification').value;
  const rows=data.items.filter(r=>(!year||r.postedAt.slice(0,4)===year)&&(!type||r.noticeType===type)&&(!classification||r.classification===classification)&&(!q||(scope==='all'?[r.title,r.agency,r.classification]:[r[scope]]).some(v=>String(v||'').toLocaleLowerCase('ko').includes(q))));
  const pages=Math.ceil(rows.length/size);page=Math.max(1,Math.min(page,pages||1));
  el('rows').replaceChildren(...rows.slice((page-1)*size,page*size).map(r=>{
   const tr=document.createElement('tr');
   for(const value of [r.noticeType,r.title,r.agency,r.classification]){const td=document.createElement('td'),span=document.createElement('span');span.className='cell-content';span.textContent=value||'—';span.title=value||'—';td.append(span);tr.append(td);}
   const td=document.createElement('td');let valid=false;
   try{const u=new URL(r.url);if(['http:','https:'].includes(u.protocol)&&(u.hostname==='g2b.go.kr'||u.hostname.endsWith('.g2b.go.kr'))&&!u.username&&!u.password){const a=document.createElement('a');a.href=u.href;a.textContent='공고 세부 정보 보기';a.className='cell-content';a.target='_blank';a.rel='noopener noreferrer';a.style.textDecoration='underline';td.append(a);valid=true;}}catch{}
   if(!valid){td.textContent='링크 미제공';td.title=r.id;}tr.append(td);return tr;
  }));
  el('empty').hidden=rows.length>0||data.status==='pending';
  el('count').textContent=`조회 ${rows.length}건 / 저장 ${data.items.length}건 · ${rows.length?(page-1)*size+1:0}~${Math.min(page*size,rows.length)}건 · 페이지당 10건`;
  const nav=el('pagination');nav.replaceChildren();nav.hidden=pages<=1;
  if(pages>1){
   const add=(label,target,disabled=false)=>{const b=document.createElement('button');b.type='button';b.textContent=label;b.disabled=disabled;if(target===page&&typeof label==='number')b.setAttribute('aria-current','page');b.onclick=()=>{page=target;render();el('results').scrollIntoView({block:'start'});};nav.append(b);};
   add('이전',page-1,page===1);for(const n of ResearchList.pageNumbers(page,pages)){if(n==='…'){const s=document.createElement('span');s.textContent=n;nav.append(s);}else add(n,n);}add('다음',page+1,page===pages);add('마지막',pages,page===pages);
  }
 }
 try{
  const response=await fetch('data/tourism-bids.json',{cache:'no-cache'});if(!response.ok)throw Error();data=await response.json();if(!Array.isArray(data.items))throw Error();
  for(const [id,values] of [['year',['2026','2025','2024','2023','2022']],['type',[...new Set(data.items.map(r=>r.noticeType))].filter(Boolean).sort()],['classification',[...new Set(data.items.map(r=>r.classification))].filter(Boolean).sort((a,b)=>a.localeCompare(b,'ko'))]]){for(const value of values){const o=document.createElement('option');o.value=value;o.textContent=value;el(id).append(o);}}
  el('status').textContent=data.status==='pending'?'자동 수집 대기 중입니다. 아직 조회 결과가 확보되지 않았습니다.':`저장 ${data.items.length}건 · 월별 조회 완료 ${data.completedMonths}/60개월 · ${data.completed?'전체 월 조회 완료':'일부 기간 수집 중 또는 중단: 전체 목록이 아닙니다'} · 마지막 반영 ${new Date(data.updatedAt).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'})} (한국시간)`;
  for(const id of ['scope','year','type','classification'])el(id).onchange=()=>{page=1;render();};el('search').oninput=()=>{page=1;render();};el('reset').onclick=()=>{for(const id of ['search','year','type','classification'])el(id).value='';el('scope').value='all';page=1;render();};render();
 }catch{el('status').textContent='자료를 불러오지 못했습니다. 잠시 후 새로고침해 주세요. 조회 결과 0건을 의미하지 않습니다.';}
})();
