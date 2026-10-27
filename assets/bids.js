(async function(){
 const el=id=>document.getElementById(id);let data,linkData={links:{}},linksUnavailable=false,page=1;
 const pageSize=10;
 function departmentLabel(value){
  const text=String(value||'').trim();
  const compact=text.replace(/\s+/g,'');
  // 부서명이 아닌 기관 명의 공고 문구는 표시에서 제외합니다.
  if(/^문화체육(?:관광|광광)부(?:(?:입찰|용역)?공고)?제(?:호)?$/.test(compact))return '-';
  return text||'—';
 }
 function option(id,value,label=value){const o=document.createElement('option');o.value=value;o.textContent=label;el(id).append(o);}
 async function copy(id){try{await navigator.clipboard.writeText(id);el('bid-copy-status').textContent=`공고번호 ${id}를 복사했습니다. 나라장터에서 검색해 주세요.`;}catch{el('bid-copy-status').textContent=`자동 복사가 지원되지 않습니다. 공고번호를 직접 복사해 주세요: ${id}`;}}
 function render(){
  const q=el('bid-search').value.trim().toLocaleLowerCase('ko'),year=el('bid-year').value,type=el('bid-type').value,scope=el('bid-scope').value;
  const records=data.items.filter(r=>(!year||r.year===Number(year))&&(!type||r.noticeType===type)&&(!q||(scope==='title'?[r.title]:scope==='department'?[departmentLabel(linkData.links[r.id]?.department)]:[r.title,departmentLabel(linkData.links[r.id]?.department)]).some(s=>s.toLocaleLowerCase('ko').includes(q))));
  const pages=Math.ceil(records.length/pageSize);page=Math.max(1,Math.min(page,Math.max(1,pages)));
  const visible=records.slice((page-1)*pageSize,page*pageSize);
  el('bid-rows').replaceChildren(...visible.map(r=>{
   const tr=document.createElement('tr');
   for(const value of [r.title,r.noticeType,departmentLabel(linkData.links[r.id]?.department),String(r.year)]){const td=document.createElement('td'),span=document.createElement('span');span.className='cell-content';span.textContent=value||'—';span.title=value||'—';td.append(span);tr.append(td);}
   const td=document.createElement('td'),saved=linkData.links[r.id];let valid=false;
   if(saved?.status==='ok'&&saved.url){try{const u=new URL(saved.url);if(['https:','http:'].includes(u.protocol)&&(u.hostname==='g2b.go.kr'||u.hostname.endsWith('.g2b.go.kr'))&&!u.username&&!u.password){const a=document.createElement('a');a.href=u.href;a.textContent='공고 세부 정보 보기';a.className='cell-content';a.title='공고 세부 정보 보기 (새 창)';a.target='_blank';a.rel='noopener noreferrer';a.style.textDecoration='underline';td.append(a);valid=true;}}catch{}}
   if(!valid){const p=document.createElement('p');p.className='cell-content';p.textContent=linksUnavailable?'링크 불러오기 실패':saved?.status==='failed'?'세부 조회 실패':saved?.status==='not_found'?'일치 공고 미확인':saved?.status==='no_url'?'세부 URL 미제공':'세부 링크 수집 대기';p.title=p.textContent;td.append(p);const b=document.createElement('button');b.type='button';b.textContent='공고번호 복사';b.setAttribute('aria-label',`${r.id} 공고번호 복사`);b.onclick=()=>copy(r.id);td.append(b);}
   tr.append(td);return tr;
  }));
  el('bid-count').textContent=`조회 ${records.length}건 / 전체 ${data.items.length}건 · ${records.length?(page-1)*pageSize+1:0}~${Math.min(page*pageSize,records.length)}건 표시 · ${pages?page:0}/${pages}페이지 (페이지당 10건) · 게시일시 내림차순`;
  el('bid-empty').hidden=records.length>0;el('bid-copy-status').textContent='';
  const pagination=el('bid-pagination');pagination.replaceChildren();pagination.hidden=pages<=1;
  if(pages>1){
   function add(label,target,disabled=false,current=false){const b=document.createElement('button');b.type='button';b.textContent=label;b.disabled=disabled;b.setAttribute('aria-label',typeof label==='number'?`${label}페이지`:`${label} 페이지`);if(current)b.setAttribute('aria-current','page');b.onclick=()=>{page=target;render();el('bid-results').scrollIntoView({block:'start',behavior:'auto'});pagination.querySelector('[aria-current="page"]')?.focus({preventScroll:true});};pagination.append(b);}
   add('이전',page-1,page===1);
   for(const n of ResearchList.pageNumbers(page,pages)){if(n==='…'){const span=document.createElement('span');span.textContent='…';span.setAttribute('aria-hidden','true');pagination.append(span);}else add(n,n,false,n===page);}
   add('다음',page+1,page===pages);add('마지막',pages,page===pages);
  }
 }
 function changed(){page=1;el('bid-search').placeholder=el('bid-scope').value==='title'?'공고명 입력':el('bid-scope').value==='department'?'담당부서 입력':'공고명 또는 담당부서 검색';render();}
 try{
  const r=await fetch('data/nara.json',{cache:'no-cache'});if(!r.ok)throw Error();data=await r.json();if(data.status!=='ready'||!Array.isArray(data.items))throw Error();
  try{const links=await fetch('data/nara-links.json',{cache:'no-cache'});if(!links.ok)throw Error();linkData=await links.json();if(!linkData.links)throw Error();}catch{linkData={links:{}};linksUnavailable=true;}
  for(const year of [...new Set(data.items.map(r=>r.year))].sort((a,b)=>b-a))option('bid-year',year);
  for(const type of [...new Set(data.items.map(r=>r.noticeType))].sort())option('bid-type',type);
  const linked=data.items.filter(r=>linkData.links[r.id]?.status==='ok').length;
  el('bid-status').textContent=`전체 ${data.totalCount}건 · 반영 시각 ${new Date(data.importedAt).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'})} (한국시간) · 상세 링크 확보 ${linked}/${data.items.length}건`;
  for(const id of ['bid-scope','bid-year','bid-type'])el(id).onchange=changed;
  el('bid-search').oninput=changed;el('bid-reset').onclick=()=>{for(const id of ['bid-search','bid-year','bid-type'])el(id).value='';el('bid-scope').value='all';changed();};render();
 }catch{el('bid-status').textContent='공고 자료를 불러오지 못했습니다. 잠시 후 새로고침해 주세요. 조회 결과 0건을 의미하지 않습니다.';}
})();
