(async function(){
 const el=id=>document.getElementById('news-'+id);let data,page=1;const size=12;
 function url(value){try{const u=new URL(value);return ['http:','https:'].includes(u.protocol)&&!u.username&&!u.password?u.href:null;}catch{return null;}}
 function render(){
  const q=el('search').value.trim().toLocaleLowerCase('ko'),category=el('category').value;
  const items=data.items.filter(r=>(!category||r.tags.includes(category))&&(!q||[r.title,r.publisher,r.description,...r.tags].join(' ').toLocaleLowerCase('ko').includes(q)));
  const pages=Math.ceil(items.length/size);page=Math.max(1,Math.min(page,pages||1));
  el('grid').replaceChildren(...items.slice((page-1)*size,page*size).map(r=>{
   const article=document.createElement('article');article.className='news-card';
   const media=document.createElement('div');media.className='news-media';media.textContent='주요 뉴스';
   const image=url(r.image);if(image){const img=document.createElement('img');img.src=image;img.alt='';img.loading='lazy';img.referrerPolicy='no-referrer';img.onerror=()=>{img.remove();media.textContent='주요 뉴스';};media.replaceChildren(img);}
   const body=document.createElement('div');body.className='news-card-body';const meta=document.createElement('p');meta.className='news-meta';meta.textContent=[r.date,r.publisher].filter(Boolean).join(' · ');
   const title=document.createElement('h2');title.textContent=r.title;
   const tags=document.createElement('p');tags.className='news-tags';tags.textContent=r.tags.join(' · ');
   const description=document.createElement('p');description.className='news-summary';description.textContent=r.description||(r.previewStatus==='pending'?'기사 미리보기 수집 대기 중입니다.':r.url?'미리보기 내용이 제공되지 않습니다. 원문에서 확인해 주세요.':'엑셀에 원문 링크가 등록되어 있지 않습니다.');
   body.append(meta,title,tags,description);const target=url(r.url);
   if(target){const a=document.createElement('a');a.className='news-open';a.href=target;a.target='_blank';a.rel='noopener noreferrer';a.textContent='기사 원문 보기 ↗';a.setAttribute('aria-label',r.title+' — 원문 새 창에서 보기');body.append(a);}else{const note=document.createElement('span');note.className='news-meta';note.textContent='원문 링크 미등록';body.append(note);}
   article.append(media,body);return article;
  }));
  el('count').textContent=`조회 ${items.length}건 · ${items.length?(page-1)*size+1:0}~${Math.min(page*size,items.length)}건 표시 · 최신 날짜순`;
  el('empty').hidden=items.length>0;const nav=el('pagination');nav.replaceChildren();nav.hidden=pages<=1;
  function add(label,target,disabled=false){const b=document.createElement('button');b.type='button';b.textContent=label;b.disabled=disabled;if(typeof label==='number'&&target===page)b.setAttribute('aria-current','page');b.onclick=()=>{page=target;render();el('results').scrollIntoView({block:'start'});};nav.append(b);}
  if(pages>1){add('이전',page-1,page===1);for(const n of ResearchList.pageNumbers(page,pages)){if(n==='…'){const span=document.createElement('span');span.textContent=n;nav.append(span);}else add(n,n);}add('다음',page+1,page===pages);add('마지막',pages,page===pages);}
 }
 try{
  const response=await fetch('data/news.json',{cache:'no-cache'});if(!response.ok)throw Error();data=await response.json();if(!Array.isArray(data.items))throw Error();
  for(const tag of [...new Set(data.items.flatMap(r=>r.tags))].sort((a,b)=>a.localeCompare(b,'ko'))){const o=document.createElement('option');o.value=tag;o.textContent=tag;el('category').append(o);}
  el('status').textContent=`전체 ${data.items.length}건 · 내용 미리보기 ${data.items.filter(r=>r.description).length}건 · 원문 링크 ${data.items.filter(r=>url(r.url)).length}건`;
  el('search').oninput=()=>{page=1;render();};el('category').onchange=()=>{page=1;render();};el('reset').onclick=()=>{el('search').value='';el('category').value='';page=1;render();};render();
 }catch{el('status').textContent='기사 목록을 불러오지 못했습니다. 잠시 후 새로고침해 주세요.';}
})();
