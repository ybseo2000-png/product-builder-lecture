(function(){
 const hero=document.querySelector('.hero-slideshow');if(!hero)return;
 const slides=[...hero.querySelectorAll('.hero-slides img')],controls=hero.querySelector('.hero-controls');
 if(slides.length<2)return;
 const motion=window.matchMedia('(prefers-reduced-motion: reduce)');
 let current=0,timer=null,paused=motion.matches,request=0;
 function schedule(){
  clearInterval(timer);timer=null;
  if(!paused&&!document.hidden)timer=setInterval(()=>show(current+1),10000);
 }
 async function show(target){
  const next=(target+slides.length)%slides.length,img=slides[next],token=++request;
  try{await img.decode();}catch{if(!img.naturalWidth)return;}
  if(token!==request)return;
  slides[current].classList.remove('is-active');img.classList.add('is-active');current=next;
  controls.querySelector('.hero-slide-count').textContent=`${current+1} / ${slides.length}`;
 }
 controls.hidden=false;
 for(const [direction,offset] of [['previous',-1],['next',1]])controls.querySelector(`[data-slide="${direction}"]`).onclick=()=>{show(current+offset);schedule();};
 document.addEventListener('visibilitychange',schedule);
 motion.addEventListener('change',()=>{paused=motion.matches;schedule();});schedule();
})();
