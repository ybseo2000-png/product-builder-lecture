"""Monthly tourism notice collection. No credentials in public files."""
import calendar
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import unquote, urlencode
from urllib.request import Request, build_opener
from collect_nara_links import LinkError, parse_response
from collect_nkis import NoRedirect
ENDPOINT='https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch'
OUTPUT=Path('data/tourism-bids.json')
def months():
 for year in range(2022,2027):
  for month in range(1,13):
   yield f'{year}-{month:02}',f'{year}{month:02}010000',f'{year}{month:02}{calendar.monthrange(year,month)[1]:02}2359'
def request_page(key,begin,end,page):
 params=dict(serviceKey=unquote(key),numOfRows=10,pageNo=page,inqryDiv=1,inqryBgnDt=begin,inqryEndDt=end,bidNtceNm='관광',type='json')
 for attempt in range(3):
  try:
   req=Request(ENDPOINT+'?'+urlencode(params),headers={'Accept':'application/json','User-Agent':'ResearchDiscovery/1.0'})
   with build_opener(NoRedirect()).open(req,timeout=30) as response:raw=response.read(5_000_001)
   if len(raw)>5_000_000:raise LinkError('응답 크기 제한 초과')
   return parse_response(json.loads(raw.decode('utf-8-sig')))
  except Exception:
   if attempt==2:raise LinkError('API 요청 실패 (키/응답 원문 비공개)') from None
   time.sleep(2**attempt)
def normalize(row):
 number=str(row.get('bidNtceNo') or '').strip();order=str(row.get('bidNtceOrd') or '').zfill(3)
 if not number or not row.get('bidNtceNm'):raise LinkError('공고번호 또는 공고명 누락')
 return dict(id=f'{number}-{order}',title=str(row['bidNtceNm']),noticeType=str(row.get('ntceKindNm') or ''),agency=str(row.get('ntceInsttNm') or row.get('ntceInstNm') or ''),classification=str(row.get('pubPrcrmntMidClsfcNm') or ''),url=str(row.get('bidNtceDtlUrl') or ''),postedAt=str(row.get('bidNtceDt') or ''))
def collect_month(key,begin,end,fetch=request_page,pause=time.sleep):
 total,rows=fetch(key,begin,end,1);all_rows=list(rows)
 if len(rows)!=min(10,total):raise LinkError('첫 페이지 건수 불일치')
 for page in range(2,(total+9)//10+1):
  pause(.3);count,rows=fetch(key,begin,end,page)
  if count!=total or len(rows)!=min(10,total-(page-1)*10):raise LinkError('페이지 건수 변경 또는 누락')
  all_rows.extend(rows)
 normalized=[normalize(row) for row in all_rows]
 if len({r['id'] for r in normalized})!=total:raise LinkError('월별 페이지 중복')
 if any(not r['postedAt'].startswith(begin[:4]+'-'+begin[4:6]) for r in normalized):raise LinkError('요청 월과 게시일시 불일치')
 return normalized
def save(data,key):
 items={r['id']:r for month in data['months'].values() for r in month.get('items',[])}
 data['items']=sorted(items.values(),key=lambda r:(r['postedAt'],r['id']),reverse=True)
 data['totalCount']=len(items);data['updatedAt']=datetime.now(timezone.utc).isoformat()
 data['completedMonths']=sum(v.get('status')=='complete' for v in data['months'].values());data['completed']=data['completedMonths']==60
 public=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
 if any(secret in public for secret in {key,unquote(key)}):raise LinkError('공개 결과에서 인증정보 감지')
 temp=OUTPUT.with_suffix('.json.tmp');temp.write_text(public,encoding='utf-8');temp.replace(OUTPUT)
def main():
 key=os.environ.get('PRISM_API_KEY','').strip()
 if not key:print('PRISM_API_KEY Secret이 없습니다.',file=sys.stderr);return 1
 data=json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {'months':{}}
 data.update(status='collecting',source='나라장터 검색조건에 의한 입찰공고용역조회',keyword='관광',period='2022-01-01~2026-12-31')
 current_month=datetime.now(timezone.utc).strftime('%Y-%m')
 try:
  for label,begin,end in months():
   old=data['months'].get(label,{})
   if old.get('status')=='complete' and label<current_month:continue
   print(f'수집 월: {label}',flush=True)
   try:rows=collect_month(key,begin,end)
   except LinkError:
    data['months'][label]={**old,'status':'failed'};raise
   data['months'][label]=dict(status='complete',items=rows,totalCount=len(rows),collectedAt=datetime.now(timezone.utc).isoformat())
   save(data,key);print(f'{label}: {len(rows)}건 · 처리 {data["completedMonths"]}/60개월',flush=True);time.sleep(.3)
  data['status']='ready';save(data,key)
  print(f'::notice::관광 용역공고 {data["totalCount"]}건 · 60개월 조회 완료 (미래 기간은 이후 재조회)');return 0
 except Exception:
  data['status']='partial';save(data,key)
  print('::error::월별 수집 중단. 완료된 월은 보존했습니다. 재실행하면 이어서 수집합니다. 인증·활용승인·응답 명세를 확인하세요.',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
