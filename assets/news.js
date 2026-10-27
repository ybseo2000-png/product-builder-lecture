(async function(){
 const el=id=>document.getElementById('news-'+id);let data,page=1;const size=12;
 function url(value){try{const u=new URL(value);return ['http:','https:'].includes(u.protocol)&&!u.username&&!u.password?u.href:null;}catch{return null;}}
 function render(){
  const q=el('search').value.trim().toLocaleLowerCase('ko'),category=el('category').value;
  const items=data.items.filter(r=>(!category||r.tags.includes(category))&&(!q||[r.title,r.publisher,...r.tags].join(' ').toLocaleLowerCase('ko').includes(q)));
  const pages=Math.ceil(items.length/size);page=Math.max(1,Math.min(page,pages||1));
  el('grid').replaceChildren(...items.slice((page-1)*size,page*size).map(r=>{
   const article=document.createElement('article');article.className='news-card';
   const body=document.createElement('div');body.className='news-card-body';const meta=document.createElement('p');meta.className='news-meta';meta.textContent=[r.date,r.publisher].filter(Boolean).join(' · ');meta.title=meta.textContent;
   const title=document.createElement('h2');title.textContent=r.title;title.title=r.title;const headlineUrl=url(r.url);if(headlineUrl){const a=document.createElement('a');a.href=headlineUrl;a.textContent=r.title;a.target='_blank';a.rel='noopener noreferrer';title.replaceChildren(a);}
   const tags=document.createElement('p');tags.className='news-tags';tags.textContent=r.tags.join(' · ');tags.title=tags.textContent;
   body.append(meta,title,tags);const target=url(r.url);
   if(target){const a=document.createElement('a');a.className='news-open';a.href=target;a.target='_blank';a.rel='noopener noreferrer';a.textContent='기사 원문 보기 ↗';a.setAttribute('aria-label',r.title+' — 원문 새 창에서 보기');body.append(a);}else{const note=document.createElement('span');note.className='news-meta';note.textContent='원문 링크 미등록';body.append(note);}
   article.append(body);return article;
  }));
  el('count').textContent=`조회 ${items.length}건 · ${items.length?(page-1)*size+1:0}~${Math.min(page*size,items.length)}건 표시 · 최신 날짜순`;
  el('empty').hidden=items.length>0;const nav=el('pagination');nav.replaceChildren();nav.hidden=pages<=1;
  function add(label,target,disabled=false){const b=document.createElement('button');b.type='button';b.textContent=label;b.disabled=disabled;if(typeof label==='number'&&target===page)b.setAttribute('aria-current','page');b.onclick=()=>{page=target;render();el('results').scrollIntoView({block:'start'});};nav.append(b);}
  if(pages>1){add('이전',page-1,page===1);for(const n of ResearchList.pageNumbers(page,pages)){if(n==='…'){const span=document.createElement('span');span.textContent=n;nav.append(span);}else add(n,n);}add('다음',page+1,page===pages);add('마지막',pages,page===pages);}
 }
 try{
  const response=await fetch('data/news.json',{cache:'no-cache'});if(!response.ok)throw Error();data=await response.json();if(!Array.isArray(data.items))throw Error();
  for(const tag of [...new Set(data.items.flatMap(r=>r.tags))].sort((a,b)=>a.localeCompare(b,'ko'))){const o=document.createElement('option');o.value=tag;o.textContent=tag;el('category').append(o);}
  el('status').textContent=`전체 ${data.items.length}건 · 원문 링크 ${data.items.filter(r=>url(r.url)).length}건`;
  el('search').oninput=()=>{page=1;render();};el('category').onchange=()=>{page=1;render();};el('reset').onclick=()=>{el('search').value='';el('category').value='';page=1;render();};render();
 }catch{el('status').textContent='기사 목록을 불러오지 못했습니다. 잠시 후 새로고침해 주세요.';}
})();
