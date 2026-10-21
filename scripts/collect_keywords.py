"""NKIS 상세 HTML의 주제어 추출 및 재개 가능한 소량 수집. 외부 패키지 불필요."""
import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
import unicodedata
from urllib.parse import urlsplit
from urllib.request import Request, build_opener

try:
    from .collect_nkis import NoRedirect
except ImportError:
    from collect_nkis import NoRedirect


class Node:
    def __init__(self, tag):
        self.tag, self.children = tag, []

    def text(self):
        return ''.join(c.text() if isinstance(c, Node) else c for c in self.children)

    def descendants(self, tag):
        for child in self.children:
            if isinstance(child, Node):
                if child.tag == tag:
                    yield child
                yield from child.descendants(tag)


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('root')
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag)
        self.stack[-1].children.append(node)
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack)-1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def extract_keywords(html):
    parser = Document()
    parser.feed(html)
    for row in parser.root.descendants('li'):
        labels = list(row.descendants('em'))
        if not any(re.sub(r'\s+', '', label.text()) == '주제어' for label in labels):
            continue
        spans = list(row.descendants('span'))
        if not spans:
            return {'status':'missing', 'keywords':[]}
        raw = unicodedata.normalize('NFC', spans[0].text())
        terms = []
        for part in re.split(r'[,;，；\n]+', raw):
            term = re.sub(r'\s+', ' ', part).strip()
            if term and term not in terms:
                terms.append(term)
        return {'status':'ok' if terms else 'empty', 'keywords':terms}
    return {'status':'missing', 'keywords':[]}


def fetch_html(url):
    parts = urlsplit(url)
    if parts.scheme != 'https' or parts.hostname not in {'nkis.re.kr','www.nkis.re.kr'} or parts.username or parts.password:
        raise ValueError('Unsupported source URL')
    req = Request(url, headers={'User-Agent':'TourismResearchDiscovery/1.0 (keyword metadata pilot)'})
    with build_opener(NoRedirect()).open(req, timeout=40) as response:
        data = response.read(2_000_001)
        charset = response.headers.get_content_charset() or 'utf-8'
    if len(data) > 2_000_000:
        raise ValueError('HTML size limit')
    return data.decode(charset)


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.json.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)


def collect(reports, cache, limit, delay, fetch=fetch_html, pause=time.sleep):
    records = cache.setdefault('reports', {})
    requested = 0
    for report in reports:
        previous = records.get(report['id'], {})
        if previous.get('status') in {'ok','empty'} and previous.get('url') == report['url']:
            continue
        if requested >= limit:
            break
        if requested:
            pause(delay)
        requested += 1
        try:
            result = extract_keywords(fetch(report['url']))
        except Exception:
            result = {'status':'failed','keywords':[]}
        records[report['id']] = {
            'id':report['id'],'year':report['year'],'title':report['title'],
            'url':report['url'], **result,
            'checkedAt':datetime.now(timezone.utc).isoformat(),
        }
        print(f'주제어 요청 {requested}: {result["status"]}, {len(result["keywords"])}개',flush=True)
        yield cache


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--html', help='제공받은 HTML 파일을 오프라인으로 검사')
    parser.add_argument('--reports',default='data/research.json')
    parser.add_argument('--output',default='data/keywords.json')
    parser.add_argument('--limit',type=int,default=20,help='이번 실행의 최대 요청 수; 기본 소량 검증 20')
    parser.add_argument('--delay',type=float,default=1.5)
    args = parser.parse_args()
    if args.html:
        print(json.dumps(extract_keywords(Path(args.html).read_text(encoding='utf-8')),ensure_ascii=False,indent=2))
        return
    if args.limit < 1 or args.delay < 1:
        parser.error('limit은 양수, delay는 1초 이상이어야 합니다')
    output = Path(args.output)
    cache = json.loads(output.read_text()) if output.exists() else {'version':1,'reports':{}}
    reports = json.loads(Path(args.reports).read_text())['items']
    ids = {r['id'] for r in reports}
    cache['reports'] = {key:value for key,value in cache['reports'].items() if key in ids}
    for updated in collect(reports,cache,args.limit,args.delay):
        save(output,updated)
    save(output,cache)
    statuses = {status:sum(r['status']==status for r in cache['reports'].values()) for status in ['ok','empty','missing','failed']}
    print(json.dumps({'totalReports':len(reports),'checked':len(cache['reports']),**statuses},ensure_ascii=False))


if __name__ == '__main__': main()
