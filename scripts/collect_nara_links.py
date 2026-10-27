"""나라장터 API가 반환한 실제 상세 링크만 엑셀 공고의 번호/차수에 대응시킴."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlencode,urlsplit,parse_qs,unquote
from urllib.request import Request,build_opener
try:
 from .collect_nkis import NoRedirect
except ImportError:
 from collect_nkis import NoRedirect

ENDPOINT='https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc'
OUTPUT=Path('data/nara-links.json')
class LinkError(Exception):pass
class AuthError(LinkError):pass


def split_notice(identity):
 match=re.fullmatch(r'([A-Za-z0-9]+)-(\d{3})',identity)
 if not match:raise LinkError('입찰공고번호 형식 오류')
 return match.groups()


def request_json(key,number,page):
 if '-' in number:raise LinkError('API에는 차수를 제외한 공고 본번호만 전달해야 합니다')
 params={'serviceKey':unquote(key),'inqryDiv':2,'bidNtceNo':number,'numOfRows':100,'pageNo':page,'type':'json'}
 for attempt in range(3):
  try:
   req=Request(ENDPOINT+'?'+urlencode(params),headers={'Accept':'application/json','User-Agent':'ResearchDiscovery/1.0'})
   with build_opener(NoRedirect()).open(req,timeout=40) as response:raw=response.read(5_000_001)
   if len(raw)>5_000_000:raise LinkError('응답 크기 제한 초과')
   if any(code in raw for code in [b'SERVICE_KEY_IS_NOT_REGISTERED',b'SERVICE_ACCESS_DENIED',b'UNREGISTERED_IP']):raise AuthError('나라장터 서비스 활용 승인 또는 인증 설정 확인 필요')
   return json.loads(raw.decode('utf-8-sig'))
  except AuthError:raise
  except HTTPError as exc:
   if exc.code in [401,403]:raise AuthError('HTTP 인증/접근 거부. 서비스 활용 승인을 확인하세요') from None
   if attempt==2:raise LinkError('API HTTP 요청 실패 (요청 주소/인증키 비공개)') from None
  except LinkError:raise
  except Exception:
   if attempt==2:raise LinkError('API 연결 또는 JSON 해석 실패 (응답 원문 비공개)') from None
  time.sleep(2**attempt)


def parse_response(payload):
 try:
  response=payload['response'];header=response['header']
 except (TypeError,KeyError):raise LinkError('API 응답 구조 불일치') from None
 code=str(header.get('resultCode',''))
 if code in ['20','21','22','30','31','32']:raise AuthError('API 인증/활용승인 오류. 나라장터 서비스 신청 상태 확인 필요')
 if code not in ['00','0']:raise LinkError('API 비정상 결과 코드 (인증키 보호를 위해 원문 비공개)')
 body=response.get('body')
 if not isinstance(body,dict):raise LinkError('API body 누락')
 total=body.get('totalCount')
 if isinstance(total,bool) or not str(total).isdigit():raise LinkError('API totalCount 형식 오류')
 items=body.get('items')
 if items in (None,'') and int(total)==0:items=[]
 if isinstance(items,dict):items=items.get('item',items)
 if isinstance(items,dict):items=[items]
 if not isinstance(items,list) or any(not isinstance(i,dict) for i in items):raise LinkError('API items 형식 오류')
 return int(total),items


def fetch_notice(key,number,fetch=request_json,pause=time.sleep):
 rows=[];expected=None;page=1
 while True:
  total,items=parse_response(fetch(key,number,page))
  if expected is None:expected=total
  if expected!=total:raise LinkError('페이지 조회 중 totalCount 변경')
  if len(items)!=min(100,max(0,total-(page-1)*100)):raise LinkError('API 페이지 누락/크기 불일치')
  rows.extend(items)
  if page>=max(1,(total+99)//100):return rows
  page+=1;pause(.5)
  if page>100:raise LinkError('페이지 제한 초과')


def match_link(items,number,order):
 matches=[r for r in items if str(r.get('bidNtceNo',''))==number and str(r.get('bidNtceOrd','')).zfill(3)==order]
 if not matches:return {'status':'not_found','url':None}
 urls={str(r.get('bidNtceDtlUrl') or '').strip() for r in matches}
 urls.discard('')
 if not urls:return {'status':'no_url','url':None}
 if len(urls)>1:raise LinkError('동일 번호/차수의 상세 URL 충돌')
 url=next(iter(urls));u=urlsplit(url)
 if u.scheme not in {'https','http'} or not u.hostname or not (u.hostname=='g2b.go.kr' or u.hostname.endswith('.g2b.go.kr')) or u.username or u.password:raise LinkError('나라장터 공식 도메인이 아닌 상세 URL')
 query=parse_qs(u.query)
 if 'bidPbancNo' in query and query['bidPbancNo']!=[number]:raise LinkError('상세 URL의 공고번호 불일치')
 if 'bidPbancOrd' in query and query['bidPbancOrd']!=[order]:raise LinkError('상세 URL의 차수 불일치')
 return {'status':'ok','url':url}


def collect(data,key,previous=None,fetch=request_json,pause=time.sleep,refresh=False):
 old=(previous or {}).get('links',{});links={};responses={}
 for index,notice in enumerate(data['items'],1):
  identity=notice['id'];number,order=split_notice(identity)
  if not refresh and old.get(identity,{}).get('status')=='ok':
   # 캐시도 동일한 공식 도메인/번호/차수 규칙으로 재검사합니다.
   try:result=match_link([{'bidNtceNo':number,'bidNtceOrd':order,'bidNtceDtlUrl':old[identity]['url']}],number,order)
   except LinkError:result=None
   if result:links[identity]={**old[identity],**result};continue
  try:
   if number not in responses:
    responses[number]=fetch_notice(key,number,fetch,pause);pause(.5)
   result=match_link(responses[number],number,order)
  except AuthError:raise
  except LinkError as exc:
   print('상세 조회 진단: '+str(exc),flush=True)
   result={'status':'failed','url':None}
  except Exception:result={'status':'failed','url':None}
  links[identity]={**result,'checkedAt':datetime.now(timezone.utc).isoformat()}
  print(f'나라장터 상세 링크 {index}/{len(data["items"])} · {result["status"]}',flush=True)
 counts={state:sum(r['status']==state for r in links.values()) for state in ['ok','not_found','no_url','failed']}
 return {'updatedAt':datetime.now(timezone.utc).isoformat(),'source':'조달청 나라장터 입찰공고정보서비스','counts':counts,'links':links}


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--refresh',action='store_true',help='기존 성공 링크도 API에서 다시 조회');args=parser.parse_args()
 key=os.environ.get('PRISM_API_KEY','').strip()
 if not key:print('PRISM_API_KEY Secret이 없습니다.',file=sys.stderr);return 1
 try:
  data=json.loads(Path('data/nara.json').read_text(encoding='utf-8'))
  old=json.loads(OUTPUT.read_text(encoding='utf-8')) if OUTPUT.exists() else None
  print('조회 방식: inqryDiv=2 · bidNtceNo=차수를 제외한 본번호 · PRISM_API_KEY 사용 · 전체 재조회='+str(args.refresh),flush=True)
  result=collect(data,key,old,refresh=args.refresh)
  text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
  if key in text or unquote(key) in text:raise LinkError('공개 결과에서 인증정보 감지')
  temp=OUTPUT.with_suffix('.json.tmp');temp.write_text(text,encoding='utf-8');temp.replace(OUTPUT)
  print('상세 링크 집계:',json.dumps(result['counts']))
  return 0
 except AuthError:
  print('NARA_AUTH: 나라장터 입찰공고정보서비스의 활용 승인 및 인증키를 확인하세요. 기존 PRISM_API_KEY의 나라장터 서비스 활용 승인 상태를 확인하세요. 기존 파일은 유지합니다.',file=sys.stderr);return 1
 except LinkError as exc:print('나라장터 상세 조회 실패: '+str(exc),file=sys.stderr);return 1
 except Exception:print('나라장터 상세 조회/저장 실패 (원문 및 키 비공개)',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
