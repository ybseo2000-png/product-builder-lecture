"""나라장터 API가 반환한 실제 상세 링크만 엑셀 공고의 번호/차수에 대응시킴."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import sys
import time
import socket
import ssl
from urllib.error import HTTPError,URLError
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


def request_json(key,number,page,attempts=2):
 if '-' in number:raise LinkError('API에는 차수를 제외한 공고 본번호만 전달해야 합니다')
 params={'serviceKey':unquote(key),'inqryDiv':2,'bidNtceNo':number,'numOfRows':100,'pageNo':page,'type':'json'}
 for attempt in range(attempts):
  diagnostic=None
  try:
   req=Request(ENDPOINT+'?'+urlencode(params),headers={'Accept':'application/json','User-Agent':'ResearchDiscovery/1.0'})
   with build_opener(NoRedirect()).open(req,timeout=20) as response:
    raw=response.read(5_000_001)
    status=getattr(response,'status',200)
   if len(raw)>5_000_000:raise LinkError('RESPONSE_TOO_LARGE: 응답 크기 제한 초과')
   prefix=raw.lstrip(b'\xef\xbb\xbf \r\n\t').lower()
   kind='JSON' if prefix.startswith((b'{',b'[')) else 'HTML' if prefix.startswith((b'<!doctype html',b'<html')) else 'XML' if prefix.startswith(b'<') else 'OTHER'
   print(f'API 응답: HTTP {status} · 형식 {kind} · {len(raw)} bytes',flush=True)
   if any(code in raw for code in [b'SERVICE_KEY_IS_NOT_REGISTERED',b'SERVICE_ACCESS_DENIED',b'UNREGISTERED_IP']):raise AuthError('나라장터 서비스 활용 승인 또는 인증 설정 확인 필요')
   if kind!='JSON':raise LinkError('NON_JSON_'+kind+': JSON 대신 다른 형식의 응답을 받았습니다 (본문/URL 비공개)')
   try:return json.loads(raw.decode('utf-8-sig'))
   except (UnicodeError,json.JSONDecodeError):raise LinkError('INVALID_JSON: JSON 응답이 손상되거나 인코딩이 맞지 않습니다') from None
  except AuthError:raise
  except HTTPError as exc:
   if exc.code in [401,403]:raise AuthError('HTTP 인증/접근 거부. 서비스 활용 승인을 확인하세요') from None
   diagnostic=f'HTTP_ERROR: HTTP {exc.code}'
   if exc.code not in [408,429,500,502,503,504]:raise LinkError(diagnostic) from None
  except (TimeoutError,socket.timeout):diagnostic='TIMEOUT: 나라장터 API 응답이 20초 안에 오지 않았습니다'
  except ssl.SSLError:diagnostic='TLS_ERROR: 인증서/TLS 연결 오류 (검증 유지)'
  except URLError as exc:
   diagnostic='TIMEOUT: API 연결 시간 초과' if isinstance(exc.reason,(TimeoutError,socket.timeout)) else 'NETWORK_ERROR: DNS/연결/TLS 단계 실패'
  except LinkError:raise
  except Exception:raise LinkError('REQUEST_INTERNAL: 요청 처리 중 예상하지 못한 예외 (원문/URL 비공개)') from None
  print(f'API 요청 진단 {attempt+1}/{attempts}: {diagnostic}',flush=True)
  if attempt+1==attempts:raise LinkError(diagnostic) from None
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


def department_from_ref(ref_no):
 if ref_no is None:return None
 # 문자와 공백만 남기므로 하이픈/괄호 등의 기호 및 숫자를 제거합니다.
 text=''.join(c for c in str(ref_no) if c.isalpha() or c.isspace())
 return ' '.join(text.split()) or None


def match_link(items,number,order):
 matches=[r for r in items if str(r.get('bidNtceNo',''))==number and str(r.get('bidNtceOrd','')).zfill(3)==order]
 if not matches:return {'status':'not_found','url':None,'refNo':None,'department':None}
 refs={str(r.get('refNo') or '').strip() for r in matches};refs.discard('')
 if len(refs)>1:raise LinkError('동일 공고번호/차수의 참조번호 충돌')
 ref_no=next(iter(refs),None)
 metadata={'refNo':ref_no,'department':department_from_ref(ref_no)}
 urls={str(r.get('bidNtceDtlUrl') or '').strip() for r in matches}
 urls.discard('')
 if not urls:return {'status':'no_url','url':None,**metadata}
 if len(urls)>1:raise LinkError('동일 번호/차수의 상세 URL 충돌')
 url=next(iter(urls));u=urlsplit(url)
 if u.scheme not in {'https','http'} or not u.hostname or not (u.hostname=='g2b.go.kr' or u.hostname.endswith('.g2b.go.kr')) or u.username or u.password:raise LinkError('나라장터 공식 도메인이 아닌 상세 URL')
 query=parse_qs(u.query)
 if 'bidPbancNo' in query and query['bidPbancNo']!=[number]:raise LinkError('상세 URL의 공고번호 불일치')
 if 'bidPbancOrd' in query and query['bidPbancOrd']!=[order]:raise LinkError('상세 URL의 차수 불일치')
 return {'status':'ok','url':url,**metadata}


def collect(data,key,previous=None,fetch=request_json,pause=time.sleep,refresh=False,on_progress=None):
 old=(previous or {}).get('links',{});ids={r['id'] for r in data['items']}
 links={k:v for k,v in old.items() if k in ids};responses={};consecutive_failures=0
 def snapshot(processed,completed=False):
  counts={state:sum(r['status']==state for r in links.values()) for state in ['ok','not_found','no_url','failed']}
  return {'updatedAt':datetime.now(timezone.utc).isoformat(),'source':'조달청 나라장터 입찰공고정보서비스','counts':counts,'links':dict(links),'processedCount':processed,'totalTargets':len(ids),'completed':completed,'departmentCount':sum(bool(r.get('department')) for r in links.values())}
 for index,notice in enumerate(data['items'],1):
  identity=notice['id'];number,order=split_notice(identity)
  if not refresh and old.get(identity,{}).get('status')=='ok' and 'refNo' in old[identity]:
   # 캐시도 동일한 공식 도메인/번호/차수 규칙으로 재검사합니다.
   try:result=match_link([{'bidNtceNo':number,'bidNtceOrd':order,'bidNtceDtlUrl':old[identity]['url'],'refNo':old[identity].get('refNo')}],number,order)
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
  attempt_status=result['status']
  if attempt_status=='failed':
   consecutive_failures+=1
   if old.get(identity,{}).get('status')=='ok':result={**old[identity],'lastAttemptStatus':'failed'}
  else:consecutive_failures=0
  links[identity]={**result,'checkedAt':datetime.now(timezone.utc).isoformat()}
  if on_progress:on_progress(snapshot(index))
  print(f'나라장터 상세 {index}/{len(data["items"])} · 호출 {attempt_status} · refNo {bool(result.get("refNo"))} · 담당부서 {bool(result.get("department"))}',flush=True)
  if consecutive_failures>=3:raise LinkError('CIRCUIT_BREAK: 연속 3건 실패로 전체 수집을 중단합니다. 기존 정상 링크와 중간 결과는 보존합니다')
 return snapshot(len(data['items']),completed=True)


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--refresh',action='store_true',help='기존 성공 링크도 API에서 다시 조회');parser.add_argument('--diagnose-notice',help='지정한 공고 한 건만 진단하고 공개 파일은 수정하지 않음');args=parser.parse_args()
 key=os.environ.get('PRISM_API_KEY','').strip()
 if not key:print('PRISM_API_KEY Secret이 없습니다.',file=sys.stderr);return 1
 try:
  if args.diagnose_notice:
   number,order=split_notice(args.diagnose_notice)
   print(f'단일 진단: inqryDiv=2 · bidNtceNo={number} · 차수={order} · type=json · numOfRows=100 · pageNo=1',flush=True)
   payload=request_json(key,number,1,attempts=1)
   total,rows=parse_response(payload)
   result=match_link(rows,number,order)
   message=f'단일 결과: totalCount={total} · 일치 상태={result["status"]} · refNo={bool(result.get("refNo"))} · 담당부서={result.get("department") or "미확보"}'
   for secret in {key,unquote(key)}:message=message.replace(secret,'[보호됨]')
   message=message.replace('%','%25').replace('\r','%0D').replace('\n','%0A')
   print('::notice title=Nara single notice diagnostic::'+message,flush=True)
   return 0
  data=json.loads(Path('data/nara.json').read_text(encoding='utf-8'))
  old=json.loads(OUTPUT.read_text(encoding='utf-8')) if OUTPUT.exists() else None
  print('조회 방식: inqryDiv=2 · bidNtceNo=차수를 제외한 본번호 · PRISM_API_KEY 사용 · 전체 재조회='+str(args.refresh),flush=True)
  def save_result(result):
   text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
   if key in text or unquote(key) in text:raise LinkError('공개 결과에서 인증정보 감지')
   temp=OUTPUT.with_suffix('.json.tmp');temp.write_text(text,encoding='utf-8');temp.replace(OUTPUT)
  result=collect(data,key,old,refresh=args.refresh,on_progress=save_result)
  save_result(result)
  print('상세 링크 집계:',json.dumps(result['counts']))
  print(f'::notice title=Nara collection result::처리 {result["processedCount"]}/{result["totalTargets"]}건 · 담당부서 {result["departmentCount"]}건 · 완료={result["completed"]}',flush=True)
  return 0
 except AuthError:
  print(('::error title=Nara diagnostic::' if args.diagnose_notice else '::error title=Nara collection::')+'NARA_AUTH: 나라장터 입찰공고정보서비스의 활용 승인 및 인증키를 확인하세요. 기존 PRISM_API_KEY의 나라장터 서비스 활용 승인 상태를 확인하세요. 기존 파일은 유지합니다.',file=sys.stderr);return 1
 except LinkError as exc:print(('::error title=Nara diagnostic::' if args.diagnose_notice else '::error title=Nara collection::')+'나라장터 상세 조회 실패: '+str(exc),file=sys.stderr);return 1
 except Exception:print('나라장터 상세 조회/저장 실패 (원문 및 키 비공개)',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
