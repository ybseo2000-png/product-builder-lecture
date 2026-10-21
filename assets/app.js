const tbody = document.querySelector('#rows');
if (tbody) {
  const kind = tbody.dataset.kind;
  const search = document.querySelector('#search');
  const year = document.querySelector('#year');
  const count = document.querySelector('#count');
  const empty = document.querySelector('#empty');
  const status = document.querySelector('#data-status');
  let dataset;
  function render() {
    const query = search.value.trim().toLocaleLowerCase('ko');
    const filtered = dataset.items.filter(item => (!year.value || String(item.year) === year.value) && `${item.title} ${item.org}`.toLocaleLowerCase('ko').includes(query));
    tbody.replaceChildren(...filtered.map(item => {
      const row = document.createElement('tr');
      for (const value of [item.year, item.title, item.org]) {
        const cell = document.createElement('td');
        cell.textContent = value;
        row.append(cell);
      }
      const cell = document.createElement('td');
      const link = document.createElement('a');
      link.href = item.url;
      link.textContent = '원문 보기 ↗';
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      cell.append(link);
      row.append(cell);
      return row;
    }));
    if (dataset.status === 'pending') {
      count.textContent = '데이터 연계 대기 중 · 실제 수집 건수는 아직 확인되지 않았습니다.';
      empty.hidden = true;
    } else {
      count.textContent = `조회 ${filtered.length}건 / 저장된 자료 ${dataset.items.length}건`;
      empty.hidden = filtered.length !== 0;
    }
  }
  async function load() {
    count.textContent = '자료를 불러오는 중입니다…';
    try {
      const response = await fetch(`data/${kind}.json`, { cache: 'no-cache' });
      if (!response.ok) throw new Error('자료 요청 실패');
      dataset = ResearchData.validateDataset(await response.json(), kind);
      status.textContent = dataset.status === 'pending'
        ? '공식 데이터 연결을 준비 중입니다. 예시 자료는 실제 검색 결과와 혼동되지 않도록 표시하지 않습니다.'
        : `수집 기준: ${dataset.period.start}~${dataset.period.end} (현재까지) · 마지막 수집: ${dataset.updatedAt} · 출처: ${dataset.sources.join(', ')}. 저장된 자료를 표시하며 전체 수집 범위는 수집 기록을 확인해야 합니다.`;
      render();
    } catch {
      status.textContent = '자료를 불러오지 못했습니다. 잠시 후 새로고침해 주세요.';
      count.textContent = '불러오기 오류 · 검색 결과 0건을 의미하지 않습니다.';
      empty.hidden = true;
    }
  }
  search.addEventListener('input', () => { if (dataset) render(); });
  year.addEventListener('change', () => { if (dataset) render(); });
  document.querySelector('#reset').addEventListener('click', () => {
    search.value = ''; year.value = ''; if (dataset) render();
  });
  load();
}
