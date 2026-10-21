"""NKIS 공식 ReportList 명세 기반 수집기. 실제 인증 응답으로 추가 검증 필요."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET

ENDPOINT = 'https://nkis.re.kr/nkisApi/search/ReportList.do'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('인증 요청의 리다이렉트를 허용하지 않습니다')



def parse_page(payload):
    if b'<!DOCTYPE' in payload.upper() or b'<!ENTITY' in payload.upper():
        raise ValueError('지원하지 않는 XML 선언')
    root = ET.fromstring(payload)
    for node in root.iter():
        node.tag = node.tag.rsplit('}', 1)[-1].upper()
    # 오류 메시지와 응답 원문은 인증정보 유출 방지를 위해 출력하지 않습니다.
    if any(node.tag == 'ERROR' and (node.text or '').strip() not in ('', '0', '000', '00') for node in root.iter()):
        raise ValueError('NKIS가 오류를 반환했습니다. 인증/요청 조건을 확인하세요')
    totals = {(n.text or '').strip() for n in root.iter('TOTAL_COUNT')}
    if len(totals) != 1 or not next(iter(totals)).isdigit():
        raise ValueError('TOTAL_COUNT 누락 또는 응답 형식 변경')
    records = []
    for node in root.iter():
        fields = {c.tag: ''.join(c.itertext()).strip() for c in node}
        if 'OTP_ID' not in fields:
            continue
        required = ['OTP_ID', 'OTP_SEQ', 'OTP_HAN_NM', 'PUBAGC', 'PBL_YY']
        if any(not fields.get(k) for k in required):
            raise ValueError('필수 보고서 필드 누락')
        if not re.fullmatch(r'[A-Za-z0-9_-]+', fields['OTP_ID']) or not fields['OTP_SEQ'].isdigit():
            raise ValueError('보고서 식별자 형식 오류')
        if not re.fullmatch(r'202[2-6]', fields['PBL_YY']):
            raise ValueError('조회 범위 밖 발행연도')
        records.append({
            'id': fields['OTP_ID'] + ':' + fields['OTP_SEQ'],
            'year': int(fields['PBL_YY']),
            'title': fields['OTP_HAN_NM'],
            'org': fields['PUBAGC'],
            # 포털 홈에서 확인한 공식 상세 페이지 형식. 인증 URL은 공개하지 않음.
            'url': 'https://nkis.re.kr/subject_view1.do?' + urlencode({'otpId': fields['OTP_ID'], 'otpSeq': fields['OTP_SEQ'], 'menuNo': '103000'}),
        })
    return int(next(iter(totals))), records


def fetch_page(key, page, rows):
    params = {'serviceKey': key, 'pageNo': page, 'rowCnt': rows,
              'pblYyBegin': 2022, 'pblYyEnd': 2026}
    req = Request(ENDPOINT + '?' + urlencode(params), headers={'User-Agent': 'TourismResearchDiscovery/1.0'})
    # URL과 예외 원문에는 인증키가 포함될 수 있으므로 상위에서 출력하지 않음.
    with build_opener(NoRedirect()).open(req, timeout=45) as response:
        payload = response.read(10_000_001)
    if len(payload) > 10_000_000:
        raise ValueError('응답 크기 제한 초과')
    return parse_page(payload)


def collect(key, max_pages, rows=10, fetch=fetch_page, pause=time.sleep):
    all_records, seen = [], set()
    expected = None
    for page in range(1, max_pages + 1):
        total, records = fetch(key, page, rows)
        if expected is None:
            expected = total
        if total != expected:
            raise ValueError('수집 중 총 건수 변경. 이전 파일을 유지합니다')
        if len(records) > rows:
            raise ValueError('요청한 페이지 크기와 응답 불일치')
        for item in records:
            if item['id'] in seen:
                raise ValueError('페이지 간 중복. 전체 수집으로 처리할 수 없습니다')
            seen.add(item['id'])
            all_records.append(item)
        if len(all_records) > expected:
            raise ValueError('총 건수 초과')
        if len(all_records) == expected:
            return {
                'kind': 'research', 'status': 'ready',
                'period': {'start': '2022-01-01', 'end': '2026-12-31'},
                'updatedAt': datetime.now(timezone.utc).isoformat(),
                'sources': ['NKIS 연구보고서 목록 API (발행연도 기준)'],
                'recordType': 'research-report', 'expectedCount': expected,
                'items': sorted(all_records, key=lambda x: (-x['year'], x['id'])),
            }
        if not records:
            raise ValueError('총 건수에 도달하기 전 빈 페이지')
        pause(0.3)
    raise ValueError('페이지 제한 초과. 부분 수집은 저장하지 않습니다')


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
            raise ValueError('응답에 인증키가 포함되어 공개할 수 없습니다')
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix('.json.tmp')
        temporary.write_text(serialized, encoding='utf-8')
        temporary.replace(output)
        print(f'NKIS 보고서 {len(data["items"])}건 저장 완료')
        return 0
    except Exception:
        print('NKIS 수집 실패. 이전 데이터는 유지됩니다. 인증 승인, 접속 및 응답 명세를 확인하세요. 인증정보 보호를 위해 상세 응답은 출력하지 않습니다.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
