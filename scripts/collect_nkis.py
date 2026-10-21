"""NKIS 공식 ReportList 명세 기반 수집기. 실제 인증 응답으로 추가 검증 필요."""
import argparse
from datetime import datetime, timezone
import json
import http.client
import os
from pathlib import Path
import re
import sys
import socket
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET

ENDPOINT = 'https://nkis.re.kr/nkisApi/search/ReportList.do'


class CollectorError(Exception):
    """Only fixed, credential-free diagnostic text may be used here."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CollectorError('인증 요청의 리다이렉트를 허용하지 않습니다')



def decode_xml(payload):
    # ElementTree는 EUC-KR/CP949 다중 바이트 XML을 bytes로 직접 처리하지 못합니다.
    # 선언된 인코딩만 엄격하게 해석하고 디코딩 오류를 무시하지 않습니다.
    declaration = re.search(br'^\s*<\?xml[^>]*encoding=[\'"]([^\'"]+)[\'"]', payload[:256], re.I)
    encoding = declaration.group(1).decode('ascii').lower() if declaration else 'utf-8-sig'
    allowed = {'utf-8', 'utf8', 'utf-8-sig', 'euc-kr', 'euc_kr', 'cp949', 'ks_c_5601-1987'}
    if encoding not in allowed:
        raise CollectorError('XML_ENCODING: 지원하지 않는 XML 인코딩 선언')
    try:
        text = payload.decode(encoding)
    except (UnicodeError, LookupError):
        raise CollectorError('XML_ENCODING: 선언된 인코딩과 응답 바이트 불일치') from None
    return text


def safe_exception_location(exc):
    # 예외 메시지, 소스 코드, 프레임 변수는 출력하지 않습니다.
    kind = type(exc).__name__
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,79}', kind):
        kind = 'Exception'
    locations = []
    tb = exc.__traceback__
    while tb is not None:
        frame = tb.tb_frame
        if frame.f_code.co_filename == __file__:
            locations.append(f'{frame.f_code.co_name}:{tb.tb_lineno}')
        tb = tb.tb_next
    return kind + (' [' + ' > '.join(locations) + ']' if locations else '')


def parse_page(payload):
    if b'<!DOCTYPE' in payload.upper() or b'<!ENTITY' in payload.upper():
        raise CollectorError('지원하지 않는 XML 선언')
    root = ET.fromstring(decode_xml(payload))
    for node in root.iter():
        node.tag = node.tag.rsplit('}', 1)[-1].upper()
    # 오류 메시지와 응답 원문은 인증정보 유출 방지를 위해 출력하지 않습니다.
    if any(node.tag == 'ERROR' and (node.text or '').strip() not in ('', '0', '000', '00') for node in root.iter()):
        raise CollectorError('API_ERROR: NKIS가 오류 XML을 반환했습니다. 승인된 키 및 연구보고서 API 사용 권한을 확인하세요 (응답 원문 비공개)')
    totals = {(n.text or '').strip() for n in root.iter('TOTAL_COUNT')}
    if len(totals) != 1 or not next(iter(totals)).isdigit():
        raise CollectorError('SCHEMA_TOTAL: TOTAL_COUNT가 없거나 올바른 정수가 아닙니다. 인증 또는 실제 XML 구조 확인이 필요합니다')
    records = []
    for node in root.iter():
        fields = {c.tag: ''.join(c.itertext()).strip() for c in node}
        if 'OTP_ID' not in fields:
            continue
        required = ['OTP_ID', 'OTP_SEQ', 'OTP_HAN_NM', 'PUBAGC', 'PBL_YY']
        if any(not fields.get(k) for k in required):
            raise CollectorError('SCHEMA_RECORD: 보고서 필수 필드가 비어 있습니다')
        if not re.fullmatch(r'[A-Za-z0-9_-]+', fields['OTP_ID']) or not fields['OTP_SEQ'].isdigit():
            raise CollectorError('보고서 식별자 형식 오류')
        if not re.fullmatch(r'202[2-6]', fields['PBL_YY']):
            raise CollectorError('조회 범위 밖 발행연도')
        records.append({
            'id': fields['OTP_ID'] + ':' + fields['OTP_SEQ'],
            'year': int(fields['PBL_YY']),
            'title': fields['OTP_HAN_NM'],
            'org': fields['PUBAGC'],
            # 포털 홈에서 확인한 공식 상세 페이지 형식. 인증 URL은 공개하지 않음.
            'url': 'https://nkis.re.kr/subject_view1.do?' + urlencode({'otpId': fields['OTP_ID'], 'otpSeq': fields['OTP_SEQ'], 'menuNo': '103000'}),
        })
    total = int(next(iter(totals)))
    if total > 0 and not records:
        raise CollectorError('SCHEMA_ROWS: 총 건수는 있지만 문서상 필드의 보고서 행을 찾지 못했습니다')
    return total, records


def fetch_page(key, page, rows):
    params = {'serviceKey': key, 'pageNo': page, 'rowCnt': rows,
              'pblYyBegin': 2022, 'pblYyEnd': 2026}
    req = Request(ENDPOINT + '?' + urlencode(params), headers={'User-Agent': 'TourismResearchDiscovery/1.0'})
    # URL과 예외 원문에는 인증키가 포함될 수 있으므로 상위에서 출력하지 않음.
    with build_opener(NoRedirect()).open(req, timeout=45) as response:
        print(f'NKIS HTTP 응답 상태: {response.status}', flush=True)
        payload = response.read(10_000_001)
    if len(payload) > 10_000_000:
        raise CollectorError('응답 크기 제한 초과')
    print(f'NKIS 응답 수신: {len(payload)} bytes; XML 해석 시작', flush=True)
    return parse_page(payload)


def collect(key, max_pages, rows=10, fetch=fetch_page, pause=time.sleep):
    all_records, seen = [], {}
    page_signatures = set()
    received = duplicates = 0
    expected = None
    for page in range(1, max_pages + 1):
        print(f'NKIS 요청 페이지: {page}', flush=True)
        total, records = fetch(key, page, rows)
        if page == 1 or page % 25 == 0:
            print(f'NKIS 페이지 {page}: 응답 {len(records)}건 / 전체 {total}건', flush=True)
        if expected is None:
            expected = total
        if total != expected:
            raise CollectorError('수집 중 총 건수 변경. 이전 파일을 유지합니다')
        if len(records) > rows:
            raise CollectorError('요청한 페이지 크기와 응답 불일치')
        signature = tuple(sorted(item['id'] for item in records))
        if records and signature in page_signatures:
            raise CollectorError('PAGINATION_REPEAT: 동일한 보고서 페이지가 반복됐습니다. 페이지 번호 적용 여부를 확인하세요')
        page_signatures.add(signature)
        received += len(records)
        page_duplicates = 0
        for item in records:
            if item['id'] in seen:
                if seen[item['id']] != item:
                    raise CollectorError('DUPLICATE_CONFLICT: 같은 보고서 ID에 서로 다른 정보가 있습니다')
                duplicates += 1
                page_duplicates += 1
                continue
            seen[item['id']] = item
            all_records.append(item)
        if page_duplicates:
            print(f'페이지 {page}: 중복 {page_duplicates}건 제거 (누적 {duplicates}건)', flush=True)
        if received > expected:
            raise CollectorError('총 건수 초과')
        if received == expected:
            print(f'수집 종료: API 수신 {received}건 / 고유 보고서 {len(all_records)}건 / 중복 {duplicates}건', flush=True)
            return {
                'kind': 'research', 'status': 'ready',
                'period': {'start': '2022-01-01', 'end': '2026-12-31'},
                'updatedAt': datetime.now(timezone.utc).isoformat(),
                'sources': ['NKIS 연구보고서 목록 API (발행연도 기준)'],
                'recordType': 'research-report', 'expectedCount': expected,
                'receivedCount': received, 'duplicateCount': duplicates,
                'uniqueCount': len(all_records),
                'coverageNote': ('API 페이지에 중복이 있어 일부 보고서 누락 가능성이 있습니다. 전체 과제/보고서의 완전한 목록으로 해석하지 마세요.' if duplicates else 'API가 반환한 페이지 기준이며 전체 연구과제 목록이 아닙니다.'),
                'items': sorted(all_records, key=lambda x: (-x['year'], x['id'])),
            }
        if not records:
            raise CollectorError('총 건수에 도달하기 전 빈 페이지')
        pause(0.3)
    raise CollectorError('페이지 제한 초과. 부분 수집은 저장하지 않습니다')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='data/research.json')
    parser.add_argument('--max-pages', type=int, default=10000)
    args = parser.parse_args()
    key = os.environ.get('NKIS_API_KEY', '').strip()
    if not key:
        print('NKIS_API_KEY Secret이 필요합니다. 키를 채팅/파일에 적지 마세요.', file=sys.stderr)
        return 1
    if args.max_pages < 1:
        print('--max-pages는 양수여야 합니다.', file=sys.stderr)
        return 1
    try:
        data = collect(key, args.max_pages)
        serialized = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
        if key in serialized:
            raise CollectorError('응답에 인증키가 포함되어 공개할 수 없습니다')
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix('.json.tmp')
        temporary.write_text(serialized, encoding='utf-8')
        temporary.replace(output)
        print(f'NKIS 보고서 {len(data["items"])}건 저장 완료')
        return 0
    except Exception as exc:
        # str(HTTPError/URLError)나 traceback은 요청 URL과 키를 노출할 수 있습니다.
        if isinstance(exc, CollectorError):
            diagnostic = str(exc)
        elif isinstance(exc, http.client.HTTPException):
            diagnostic = 'HTTP_PROTOCOL: 응답 중단 또는 HTTP 프로토콜 오류'
        elif isinstance(exc, HTTPError):
            diagnostic = f'HTTP_ERROR: HTTP 상태 {exc.code}. 인증/접근 제한 또는 서버 상태를 확인하세요'
        elif isinstance(exc, (TimeoutError, socket.timeout)):
            diagnostic = 'TIMEOUT: NKIS 응답 대기 시간 초과'
        elif isinstance(exc, ssl.SSLError):
            diagnostic = 'TLS_ERROR: 인증서 또는 TLS 연결 오류 (검증은 유지됩니다)'
        elif isinstance(exc, URLError):
            diagnostic = 'NETWORK_ERROR: NKIS 연결 실패. DNS/TLS/네트워크 정책을 확인하세요'
        elif isinstance(exc, ET.ParseError):
            diagnostic = 'XML_ERROR: XML로 해석할 수 없는 응답입니다'
        elif isinstance(exc, OSError):
            diagnostic = 'FILE_ERROR: 공개 데이터 파일 저장 실패'
        else:
            diagnostic = 'UNEXPECTED_ERROR: 예상하지 못한 내부 오류 (상세 응답 비공개)'
        diagnostic += ' · 예외 종류/위치: ' + safe_exception_location(exc)
        print('NKIS 수집 실패: ' + diagnostic + '. 기존 데이터 파일은 교체하지 않았습니다.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
