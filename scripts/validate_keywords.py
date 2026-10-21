"""공개용 주제어 체크포인트의 형식 검사. 수집 완전성은 보장하지 않습니다."""
import json
from pathlib import Path
from urllib.parse import urlsplit

def validate(data):
    assert data['version']==1 and isinstance(data['reports'],dict)
    for key, item in data['reports'].items():
        assert key==item['id'] and item['status'] in {'ok','empty','missing','failed'}
        assert isinstance(item['year'],int) and 2022<=item['year']<=2026
        assert isinstance(item['title'],str) and isinstance(item['keywords'],list)
        assert all(isinstance(t,str) and t.strip() for t in item['keywords'])
        assert len(item['keywords'])==len(set(item['keywords']))
        assert bool(item['keywords'])==(item['status']=='ok')
        u=urlsplit(item['url'])
        assert u.scheme=='https' and u.hostname in {'nkis.re.kr','www.nkis.re.kr'} and not u.username and not u.password
    return len(data['reports'])

if __name__=='__main__':
    n=validate(json.loads(Path('data/keywords.json').read_text(encoding='utf-8')))
    print(f'Keyword checkpoint: {n} report records; schema OK')
