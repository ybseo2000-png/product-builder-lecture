(async function(){
 const el=id=>document.getElementById(id),fields=['research_name','charge_person_department','research_organName','researcher_name','issued_year'];
 let data,page=1;
 const pageSize=10;
 function render(){
  const q=el('prism-search').value.trim().toLocaleLowerCase('ko'),year=el('prism-year').value,scope=el('prism-scope').value,hideMissing=el('prism-hide-missing').checked;
  const searchFields=scope==='all'?fields:[scope];
  const rows=data.items.filter(r=>(!year||r.issued_year===year)&&(!q||searchFields.some(f=>String(r[f]||'').toLocaleLowerCase('ko').includes(q)))&&(!hideMissing||r.detailStatus==='failed'||r.downloads?.length>0));
  const totalPages=Math.ceil(rows.length/pageSize);page=Math.max(1,Math.min(page,Math.max(1,totalPages)));
  const visible=rows.slice((page-1)*pageSize,page*pageSize);
  el('prism-rows').replaceChildren(...visible.map(r=>{
   const tr=document.createElement('tr');for(const field of fields){const td=document.createElement('td'),text=document.createElement('span');text.className='cell-content';text.textContent=r[field]||'—';text.title=String(r[field]||'—');td.append(text);tr.append(td);}
   const td=document.createElement('td');
   if(r.detailStatus==='failed'){td.textContent='조회 실패';}
   else if(!r.downloads?.length){td.textContent='미제공';}
   else r.downloads.forEach((file,i)=>{
    let u;try{u=new URL(file.url);if(!['https:','http:'].includes(u.protocol)||u.username||u.password)return;}catch{return;}
    const a=document.createElement('a');a.className='cell-content';a.href=u.href;a.textContent=r.downloads.length===1?'보고서 원본':`보고서 원본 ${i+1}`;a.title=file.name||'보고서 원본';a.target='_blank';a.rel='noopener noreferrer';a.style.textDecoration='underline';a.style.display='block';td.append(a);
   });tr.append(td);return tr;
  }));
  el('prism-count').textContent=data.status==='pending'?'실제 수집 대기 중 · 아직 과제 건수를 확인하지 않았습니다.':`조회 ${rows.length}건 / 전체 ${data.items.length}건 · ${rows.length?(page-1)*pageSize+1:0}~${Math.min(page*pageSize,rows.length)}건 표시 · ${totalPages?page:0}/${totalPages}페이지 (페이지당 10건)`;
  el('prism-empty').hidden=data.status==='pending'||rows.length>0;
  const pagination=el('prism-pagination');pagination.replaceChildren();pagination.hidden=totalPages<=1;
  if(totalPages>1){
   function add(label,target,disabled=false,current=false){const b=document.createElement('button');b.type='button';b.textContent=label;b.disabled=disabled;b.setAttribute('aria-label',typeof label==='number'?`${label}페이지`:`${label} 페이지`);if(current)b.setAttribute('aria-current','page');b.onclick=()=>{page=target;render();el('prism-results').scrollIntoView({block:'start',behavior:'auto'});pagination.querySelector('[aria-current="page"]')?.focus({preventScroll:true});};pagination.append(b);}
   add('이전',page-1,page===1);
   for(const number of ResearchList.pageNumbers(page,totalPages)){if(number==='…'){const span=document.createElement('span');span.textContent='…';span.setAttribute('aria-hidden','true');pagination.append(span);}else add(number,number,false,number===page);}
   add('다음',page+1,page===totalPages);add('마지막',totalPages,page===totalPages);
  }
 }
 try{
  const response=await fetch('data/prism.json',{cache:'no-cache'});if(!response.ok)throw Error();data=await response.json();
  if(!['ready','pending'].includes(data.status)||!Array.isArray(data.items))throw Error();
  for(const year of [...new Set(data.items.map(r=>r.issued_year).filter(Boolean))].sort().reverse()){const opt=document.createElement('option');opt.value=year;opt.textContent=year;el('prism-year').append(opt);}
  el('prism-status').textContent=data.status==='pending'?'GitHub Actions에서 첫 실제 수집을 준비하고 있습니다.':`최종 수집: ${new Date(data.updatedAt).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'})} (한국시간) · 목록 ${data.totalCount}건 · 상세 조회 실패 ${data.detailFailed}건 · 출처: ${data.source}`;
  function setPlaceholder(){const labels={all:'연구명·담당과·수행기관·수행자·발행연도 검색',research_name:'연구명 입력',charge_person_department:'담당과 입력',research_organName:'연구수행기관 입력'};el('prism-search').placeholder=labels[el('prism-scope').value];}
  function filterChanged(){page=1;render();}
  render();el('prism-search').oninput=filterChanged;el('prism-year').onchange=filterChanged;el('prism-scope').onchange=()=>{setPlaceholder();filterChanged();};el('prism-hide-missing').onchange=filterChanged;el('prism-reset').onclick=()=>{el('prism-search').value='';el('prism-year').value='';el('prism-scope').value='all';el('prism-hide-missing').checked=false;setPlaceholder();filterChanged();};
 }catch{el('prism-status').textContent='자료를 불러오지 못했습니다. 잠시 후 새로고침해 주세요. 검색 결과 0건을 의미하지 않습니다.';}
})();
