(function(){
 const hero=document.querySelector('.hero-slideshow');if(!hero)return;
 const slides=[...hero.querySelectorAll('.hero-slides img')],controls=hero.querySelector('.hero-controls');
 if(slides.length<2)return;
 const motion=window.matchMedia('(prefers-reduced-motion: reduce)');
 let current=0,timer=null,paused=motion.matches,request=0;
 const pauseButton=controls.querySelector('[data-slide="pause"]');
 function schedule(){
  clearInterval(timer);timer=null;
  if(!paused&&!document.hidden)timer=setInterval(()=>show(current+1),5000);
  pauseButton.textContent=paused?'재생':'일시정지';
  pauseButton.setAttribute('aria-label',paused?'배경 사진 자동 전환 재생':'배경 사진 자동 전환 일시정지');
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
 pauseButton.onclick=()=>{paused=!paused;schedule();};
 document.addEventListener('visibilitychange',schedule);
 motion.addEventListener('change',()=>{paused=motion.matches;schedule();});schedule();
})();
