(function(root){
 function selectPage(items,{query='',scope='all',year='',page=1,pageSize=30}={}){
  const q=query.trim().toLocaleLowerCase('ko');
  const filtered=items.filter(item=>{
   if(year&&String(item.year)!==String(year))return false;
   const text=scope==='title'?item.title:scope==='org'?item.org:`${item.title} ${item.org}`;
   return text.toLocaleLowerCase('ko').includes(q);
  });
  const pages=Math.ceil(filtered.length/pageSize);
  const current=Math.max(1,Math.min(page,Math.max(1,pages)));
  return {items:filtered.slice((current-1)*pageSize,current*pageSize),count:filtered.length,pages,page:current};
 }
 function pageNumbers(current,total){
  if(!total)return [];
  const start=Math.max(1,Math.min(current-2,total-4));
  const numbers=new Set([1,total]);
  for(let i=start;i<=Math.min(total,start+4);i++)numbers.add(i);
  const result=[];let previous=0;
  for(const n of [...numbers].sort((a,b)=>a-b)){if(previous&&n-previous>1)result.push('…');result.push(n);previous=n;}
  return result;
 }
 root.ResearchList={selectPage,pageNumbers};
 if(typeof module!=='undefined')module.exports={selectPage,pageNumbers};
})(globalThis);
