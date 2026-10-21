const tbody = document.querySelector('#rows');
if (tbody) {
  const research = tbody.dataset.kind === 'research';
  const samples = research ? [
    {year:2026,title:'[예시] 관광산업의 미래 변화와 정책 연구',org:'소관 연구기관 (예시)'},
    {year:2025,title:'[예시] 지역관광 활성화 방안 연구',org:'소관 연구기관 (예시)'},
    {year:2024,title:'[예시] 지속가능한 관광정책 연구',org:'경제·인문사회연구회 (예시)'}
  ] : [
    {year:2026,title:'[예시] 관광정책 수립을 위한 학술연구용역',org:'문화체육관광부'},
    {year:2025,title:'[예시] 지역 문화관광 현황 조사 연구',org:'문화체육관광부'}
  ];
  const search = document.querySelector('#search');
  const year = document.querySelector('#year');
  function render() {
    const query = search.value.trim().toLocaleLowerCase('ko');
    const filtered = samples.filter(item => (!year.value || String(item.year) === year.value) && `${item.title} ${item.org}`.toLocaleLowerCase('ko').includes(query));
    tbody.replaceChildren(...filtered.map(item => {
      const row = document.createElement('tr');
      for (const value of [item.year,item.title,item.org,'예시 자료']) {
        const cell = document.createElement('td');
        cell.textContent = value;
        row.append(cell);
      }
      return row;
    }));
    document.querySelector('#count').textContent = `예시 자료 ${filtered.length}건 · 실제 수집 건수가 아닙니다`;
    document.querySelector('#empty').hidden = filtered.length !== 0;
  }
  search.addEventListener('input', render);
  year.addEventListener('change', render);
  document.querySelector('#reset').addEventListener('click', () => {search.value='';year.value='';render();});
  render();
}
