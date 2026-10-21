// 공식 API 응답을 공개 화면용으로 정리한 데이터의 형식 검사입니다.
// 기관 소속 및 원문과의 일치 여부는 수집 단계에서 별도로 검증해야 합니다.
(function (root) {
  function validateDataset(data, kind) {
    if (!data || data.kind !== kind || !['pending', 'ready'].includes(data.status)) throw new Error('자료 상태 오류');
    if (!Array.isArray(data.items) || !Array.isArray(data.sources)) throw new Error('자료 형식 오류');
    if (data.period?.start !== '2022-01-01' || data.period?.end !== '2026-12-31') throw new Error('조회 범위 오류');
    if (data.status === 'pending' && data.items.length) throw new Error('미연결 자료에 실제 목록이 있습니다');
    if (data.status === 'ready' && (!data.updatedAt || !Number.isFinite(Date.parse(data.updatedAt)) || !data.sources.length)) throw new Error('수집 정보 누락');
    const ids = new Set();
    for (const item of data.items) {
      if (typeof item.id !== 'string' || !item.id || ids.has(item.id)) throw new Error('중복 또는 누락된 자료 ID');
      ids.add(item.id);
      if (!Number.isInteger(item.year) || item.year < 2022 || item.year > 2026) throw new Error('연도 오류');
      if (typeof item.title !== 'string' || !item.title.trim() || typeof item.org !== 'string' || !item.org.trim()) throw new Error('제목 또는 기관 누락');
      let url;
      try { url = new URL(item.url); } catch { throw new Error('원문 주소 오류'); }
      if (url.protocol !== 'https:' || url.username || url.password) throw new Error('안전하지 않은 원문 주소');
      if (kind === 'bids' && (item.org !== '문화체육관광부' || !Array.isArray(item.industryCodes) || !item.industryCodes.includes('1169'))) throw new Error('입찰 조건 불일치');
    }
    return data;
  }
  root.ResearchData = { validateDataset };
  if (typeof module !== 'undefined') module.exports = { validateDataset };
})(globalThis);
