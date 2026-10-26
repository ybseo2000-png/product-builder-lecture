(async function(){
 const el=id=>document.getElementById(id);let data;
 function option(id,value,label=value){const o=document.createElement('option');o.value=value;o.textContent=label;el(id).append(o);}
 async function copy(id){try{await navigator.clipboard.writeText(id);el('bid-copy-status').textContent=`공고번호 ${id}를 복사했습니다. 나라장터에서 검색해 주세요.`;}catch{el('bid-copy-status').textContent=`자동 복사가 지원되지 않습니다. 공고번호를 직접 복사해 주세요: ${id}`;}}
 function render(){
  const q=el('bid-search').value.trim().toLocaleLowerCase('ko'),year=el('bid-year').value,month=el('bid-month').value,type=el('bid-type').value;
  const records=data.items.filter(r=>(!year||r.year===Number(year))&&(!month||r.month===Number(month))&&(!type||r.noticeType===type)&&(!q||[r.title,r.id,r.org,r.demandOrg].some(s=>s.toLocaleLowerCase('ko').includes(q))));
  el('bid-rows').replaceChildren(...records.map(r=>{
   const tr=document.createElement('tr');
   for(const value of [r.title,r.id,r.noticeType,r.org,r.demandOrg,r.publishedAt.slice(0,16).replace('T',' '),r.deadline.slice(0,16).replace('T',' '),r.business,r.procurement]){const td=document.createElement('td');td.textContent=value||'—';tr.append(td);}
   const td=document.createElement('td'),b=document.createElement('button');b.type='button';b.textContent='공고번호 복사';b.setAttribute('aria-label',`${r.id} 공고번호 복사`);b.onclick=()=>copy(r.id);td.append(b);tr.append(td);return tr;
  }));
  el('bid-count').textContent=`조회 ${records.length}건 / 전체 ${data.items.length}건 · 게시일시 내림차순`;
  el('bid-empty').hidden=records.length>0;el('bid-copy-status').textContent='';
 }
 try{
  const r=await fetch('data/nara.json',{cache:'no-cache'});if(!r.ok)throw Error();data=await r.json();if(data.status!=='ready'||!Array.isArray(data.items))throw Error();
  for(const year of [...new Set(data.items.map(r=>r.year))].sort((a,b)=>b-a))option('bid-year',year);
  for(let month=1;month<=12;month++)option('bid-month',month,`${month}월`);
  for(const type of [...new Set(data.items.map(r=>r.noticeType))].sort())option('bid-type',type);
  el('bid-status').textContent=`전체 ${data.totalCount}건 · 파일 내 게시일 범위 ${data.dateMin}~${data.dateMax} · 반영 시각 ${new Date(data.importedAt).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'})} (한국시간). 해당 기간의 전체 공고를 빠짐없이 포함한다는 뜻은 아닙니다.`;
  for(const id of ['bid-year','bid-month','bid-type'])el(id).onchange=render;
  el('bid-search').oninput=render;el('bid-reset').onclick=()=>{for(const id of ['bid-search','bid-year','bid-month','bid-type'])el(id).value='';render();};render();
 }catch{el('bid-status').textContent='공고 자료를 불러오지 못했습니다. 잠시 후 새로고침해 주세요. 조회 결과 0건을 의미하지 않습니다.';}
})();
