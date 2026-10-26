const tbody = document.querySelector('#rows');
if (tbody) {
  const kind = tbody.dataset.kind;
  const search = document.querySelector('#search');
  const scope = document.querySelector('#search-scope');
  const year = document.querySelector('#year');
  const count = document.querySelector('#count');
  const empty = document.querySelector('#empty');
  const status = document.querySelector('#data-status');
  const pagination = document.querySelector('#pagination');
  let dataset, page=1;
  function changePage(next){page=next;render();document.querySelector('#report-results').scrollIntoView({block:'start',behavior:'auto'});pagination.querySelector('[aria-current="page"]')?.focus({preventScroll:true});}
  function renderPagination(result){
    pagination.replaceChildren();pagination.hidden=result.pages<=1;
    if(result.pages<=1)return;
    function button(label,target,disabled=false,current=false){
      const b=document.createElement('button');b.type='button';b.textContent=label;b.disabled=disabled;
      b.setAttribute('aria-label',typeof label==='number'?`${label}페이지`:`${label} 페이지`);
      if(current)b.setAttribute('aria-current','page');
      b.onclick=()=>changePage(target);pagination.append(b);
    }
    button('이전',result.page-1,result.page===1);
    for(const number of ResearchList.pageNumbers(result.page,result.pages)){
      if(number==='…'){const span=document.createElement('span');span.textContent='…';span.setAttribute('aria-hidden','true');pagination.append(span);}
      else button(number,number,false,number===result.page);
    }
    button('다음',result.page+1,result.page===result.pages);
    button('마지막',result.pages,result.page===result.pages);
  }
  function render() {
    const result=ResearchList.selectPage(dataset.items,{query:search.value,scope:scope.value,year:year.value,page,pageSize:30});page=result.page;
    tbody.replaceChildren(...result.items.map(item => {
      const row=document.createElement('tr');
      for(const value of [item.year,item.title,item.org]){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}
      const cell=document.createElement('td'),link=document.createElement('a');link.href=item.url;link.textContent='원문 보기 ↗';link.target='_blank';link.rel='noopener noreferrer';cell.append(link);row.append(cell);return row;
    }));
    if(dataset.status==='pending'){
      count.textContent='데이터 연계 대기 중 · 실제 수집 건수는 아직 확인되지 않았습니다.';empty.hidden=true;
    }else{
      const start=result.count?(page-1)*30+1:0,end=Math.min(page*30,result.count);
      count.textContent=`조회 ${result.count}건 / 저장된 자료 ${dataset.items.length}건 · ${start}~${end}건 표시 · ${result.pages?page:0}/${result.pages}페이지 (페이지당 30건)`;
      empty.hidden=result.count!==0;
    }
    renderPagination(result);
  }
  function showStatus(){
    status.replaceChildren();
    if(dataset.status==='pending'){status.textContent='공식 데이터 연결을 준비 중입니다.';return;}
    const lines=[`· 수집 기준: ${dataset.period.start}~${dataset.period.end} (현재까지)`,`· 마지막 수집: ${dataset.updatedAt}`,`· 출처: ${dataset.sources.join(', ')}.`];
    for(const line of lines){const p=document.createElement('p');p.textContent=line;status.append(p);}
    if(dataset.duplicateCount>0){const p=document.createElement('p');p.className='collection-note';p.textContent='※ API를 통해 호출된 기존 데이터에 중복이 있어 일부 보고서 누락 가능성이 있습니다. 전체 과제/보고서의 완전한 목록으로 해석하지 마세요.';status.append(p);}
    else if(dataset.coverageNote){const p=document.createElement('p');p.className='collection-note';p.textContent=dataset.coverageNote;status.append(p);}
  }
  async function load(){
    count.textContent='자료를 불러오는 중입니다…';
    try{
      const response=await fetch(`data/${kind}.json`,{cache:'no-cache'});if(!response.ok)throw Error('자료 요청 실패');
      dataset=ResearchData.validateDataset(await response.json(),kind);showStatus();render();
    }catch{
      status.textContent='자료를 불러오지 못했습니다. 잠시 후 새로고침해 주세요.';count.textContent='불러오기 오류 · 검색 결과 0건을 의미하지 않습니다.';empty.hidden=true;pagination.hidden=true;
    }
  }
  function filterChanged(){page=1;search.placeholder=scope.value==='title'?'보고서 제목 입력':scope.value==='org'?'기관명 입력':'제목 또는 기관명 입력';if(dataset)render();}
  search.addEventListener('input',filterChanged);scope.addEventListener('change',filterChanged);year.addEventListener('change',filterChanged);
  document.querySelector('#reset').addEventListener('click',()=>{search.value='';scope.value='all';year.value='';filterChanged();});load();
}
