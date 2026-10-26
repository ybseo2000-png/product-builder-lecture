"""PRISM 목록/상세 API 수집. 인증키 및 원본 응답은 로그나 공개 파일에 저장하지 않음."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlencode, urlsplit, unquote
from urllib.request import Request, build_opener
try:
    from .collect_nkis import NoRedirect
except ImportError:
    from collect_nkis import NoRedirect

BASE = 'https://apis.data.go.kr/1741000/prism_v3/'
FIELDS = ['research_name','research_id','charge_person_department','research_organName','researcher_name','issued_year']
PARAMS = {'organ_id':'1371000','start_date':'20220101','end_date':'20270101','numOfRows':50}
OUTPUT = Path('data/prism.json')

class PrismError(Exception): pass


def request_json(key, operation, params):
    url = BASE + operation + '?' + urlencode({'serviceKey':unquote(key), **params})
    for attempt in range(3):
        try:
            req = Request(url, headers={'Accept':'application/json','User-Agent':'TourismResearchDiscovery/1.0'})
            with build_opener(NoRedirect()).open(req,timeout=45) as response:
                raw = response.read(10_000_001)
            if len(raw)>10_000_000: raise PrismError('응답 크기 제한 초과')
            result = json.loads(raw.decode('utf-8-sig'))
            if not isinstance(result,dict): raise PrismError('JSON 객체가 아닌 응답')
            if str(result.get('resultCode')) != '0':
                raise PrismError('API 비정상 결과 코드. 승인 상태와 호출 한도를 확인하세요')
            return result
        except PrismError: raise
        except Exception:
            if attempt==2: raise PrismError('접속 또는 JSON 응답 해석 실패 (원문/요청 주소 비공개)') from None
            time.sleep(2**attempt)


def get_list(key, fetch=request_json, pause=time.sleep):
    items=[];seen=set();expected=None;page=1;received=0
    while True:
        response=fetch(key,'getResearchList_v3',{**PARAMS,'pageNo':page})
        if str(response.get('resultCode'))!='0': raise PrismError('목록 API 비정상 응답')
        if 'organ_id' in response and str(response['organ_id'])!='1371000': raise PrismError('기관 조건 불일치')
        for name in ['start_date','end_date']:
            if name in response and str(response[name])!=PARAMS[name]: raise PrismError('날짜 조건 불일치')
        total=response.get('totalCount')
        if isinstance(total,bool) or not str(total).isdigit(): raise PrismError('totalCount 형식 오류')
        total=int(total)
        if expected is None: expected=total
        if total!=expected: raise PrismError('수집 중 totalCount 변경. 재실행이 필요합니다')
        rows=response.get('research')
        if rows in (None,'') and total==0: rows=[]
        if isinstance(rows,dict): rows=[rows]
        if not isinstance(rows,list) or len(rows)>50: raise PrismError('연구 목록 응답 구조 오류')
        expected_rows=min(50,max(0,total-(page-1)*50))
        if len(rows)!=expected_rows: raise PrismError('페이지 누락 또는 페이지당 응답 건수 불일치')
        received+=len(rows)
        for row in rows:
            if not isinstance(row,dict) or not row.get('research_id'): raise PrismError('연구 ID 누락')
            identity=str(row['research_id'])
            if identity in seen: raise PrismError('목록에 중복 ID가 있어 완전 수집을 확인할 수 없습니다')
            if not identity.startswith('1371000-'): raise PrismError('다른 기관의 연구 ID 반환')
            seen.add(identity)
            items.append({field:str(row.get(field) or '').strip() for field in FIELDS})
        pages=max(1,(total+49)//50)
        print(f'PRISM 목록 {page}/{pages}페이지 · {received}/{total}건',flush=True)
        if page>=pages: return items,total
        page+=1;pause(.5)


def detail_files(response, identity):
    if str(response.get('resultCode'))!='0': raise PrismError('상세 API 비정상 응답')
    if response.get('research_id')!=identity: raise PrismError('상세 연구 ID 불일치')
    info=response.get('reportInfo')
    if info in ('',None):return []
    if not isinstance(info,dict): raise PrismError('reportInfo 구조 오류')
    files=info.get('url')
    if files in ('',None):return []
    if isinstance(files,dict):files=[files]
    if not isinstance(files,list):raise PrismError('첨부파일 구조 오류')
    result=[];seen=set()
    for file in files:
        if not isinstance(file,dict):raise PrismError('첨부파일 항목 구조 오류')
        url=file.get('file_url')
        if not url:continue
        u=urlsplit(url)
        if u.scheme not in {'http','https'} or not u.hostname or u.username or u.password:raise PrismError('안전하지 않은 파일 주소')
        if url not in seen:
            seen.add(url);result.append({'url':url,'name':str(file.get('file_name') or ''),'type':str(file.get('file_type') or '')})
    return result


def collect(key, previous=None, fetch=request_json, pause=time.sleep):
    rows,total=get_list(key,fetch,pause)
    cached={r['research_id']:r for r in (previous or {}).get('items',[])}
    for index,row in enumerate(rows,1):
        old=cached.get(row['research_id'])
        if old and old.get('detailStatus')=='ok':
            row.update(downloads=old['downloads'],detailStatus='ok',detailCheckedAt=old.get('detailCheckedAt'))
        else:
            try:
                response=fetch(key,'getResearchDetail_v3',{'research_id':row['research_id']})
                row.update(downloads=detail_files(response,row['research_id']),detailStatus='ok')
            except PrismError as exc:
                row.update(downloads=[],detailStatus='failed')
                print('PRISM 상세 실패: '+str(exc),flush=True)
            except Exception:
                row.update(downloads=[],detailStatus='failed')
                print('PRISM 상세 실패: 응답 처리 오류 (원문 비공개)',flush=True)
            row['detailCheckedAt']=datetime.now(timezone.utc).isoformat()
            pause(.5)
        print(f'PRISM 상세 {index}/{total} · {row["detailStatus"]}',flush=True)
    failed=sum(r['detailStatus']=='failed' for r in rows)
    return {'status':'ready','organId':'1371000','startDate':'20220101','endDate':'20270101',
            'updatedAt':datetime.now(timezone.utc).isoformat(),'totalCount':total,'detailFailed':failed,
            'source':'행정안전부 정책연구 과제정보 / PRISM','items':rows}


def main():
    key=os.environ.get('PRISM_API_KEY','').strip()
    if not key:print('PRISM_API_KEY Secret이 없습니다.',file=sys.stderr);return 1
    try:
        previous=json.loads(OUTPUT.read_text(encoding='utf-8')) if OUTPUT.exists() else None
        result=collect(key,previous)
        text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
        if key in text or unquote(key) in text:raise PrismError('공개 데이터에서 인증정보 감지')
        OUTPUT.parent.mkdir(parents=True,exist_ok=True)
        temp=OUTPUT.with_suffix('.json.tmp');temp.write_text(text,encoding='utf-8');temp.replace(OUTPUT)
        print(f'목록 {result["totalCount"]}건 저장 · 상세 실패 {result["detailFailed"]}건 (재실행 시 재시도)')
        return 0
    except PrismError as exc:print('PRISM 수집 실패: '+str(exc),file=sys.stderr);return 1
    except Exception:print('PRISM 수집/저장 실패. 기존 데이터 유지 (원문 비공개)',file=sys.stderr);return 1

if __name__=='__main__':sys.exit(main())
