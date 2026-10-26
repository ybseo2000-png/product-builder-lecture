// 참고 사이트는 자동 이동하지 않으며 버튼·키보드·터치로 탐색합니다.
for (const footer of document.querySelectorAll('[data-references]')) {
  const bar=footer.querySelector('.reference-bar');
  const track=footer.querySelector('.reference-track');
  const previous=footer.querySelector('[data-direction="previous"]');
  const next=footer.querySelector('[data-direction="next"]');
  function update(){
    const overflow=track.scrollWidth>bar.clientWidth+2;
    bar.dataset.overflow=String(overflow);
    previous.hidden=next.hidden=!overflow;
    const max=track.scrollWidth-track.clientWidth;
    previous.disabled=!overflow||track.scrollLeft<=2;
    next.disabled=!overflow||track.scrollLeft>=max-2;
  }
  function move(direction){
    const behavior=matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth';
    track.scrollBy({left:direction*Math.max(160,track.clientWidth*.75),behavior});
  }
  previous.addEventListener('click',()=>move(-1));
  next.addEventListener('click',()=>move(1));
  track.addEventListener('scroll',update,{passive:true});
  if(typeof ResizeObserver!=='undefined')new ResizeObserver(update).observe(track);
  else window.addEventListener('resize',update);
  if(document.fonts)document.fonts.ready.then(update);
  update();
}
