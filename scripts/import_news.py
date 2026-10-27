"""Import editorial spreadsheet and optionally fetch public link-preview metadata."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlsplit,urljoin
from urllib.request import Request,urlopen

def safe_url(value):
 try:
  u=urlsplit(value)
  return value if u.scheme in ('https','http') and u.hostname and not u.username and not u.password else ''
 except ValueError:return ''
class Metadata(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.meta={}
 def handle_starttag(self,tag,attrs):
  if tag!='meta':return
  d=dict(attrs);key=(d.get('property') or d.get('name') or '').lower()
  if key and d.get('content'):self.meta.setdefault(key,d['content'])
def clean(value):return ' '.join(unescape(value or '').split())
def preview(item):
 if not item['url']:return item
 try:
  req=Request(item['url'],headers={'User-Agent':'Mozilla/5.0 (compatible; ResearchDiscovery/1.0)','Accept':'text/html'})
  with urlopen(req,timeout=12) as response:
   if 'html' not in response.headers.get('Content-Type','').lower():raise ValueError()
   raw=response.read(1_500_000);encoding=response.headers.get_content_charset()
   if not encoding:
    match=re.search(br'charset=["\s\']*([A-Za-z0-9_-]+)',raw[:8192],re.I);encoding=match.group(1).decode() if match else 'utf-8'
   p=Metadata();p.feed(raw.decode(encoding,errors='replace'));meta=p.meta
   item['description']=clean(meta.get('og:description') or meta.get('description') or meta.get('twitter:description'))[:500]
   image=meta.get('og:image') or meta.get('twitter:image') or ''
   item['image']=safe_url(urljoin(response.url,image)) if image else ''
   item['previewStatus']='available' if item['description'] or item['image'] else 'missing'
 except Exception:item['previewStatus']='unavailable'
 return item

def read_workbook(path):
 import openpyxl
 sheet=openpyxl.load_workbook(path,data_only=True).active;items=[]
 for row in list(sheet.rows)[1:]:
  date,text=row[0].value,row[1].value
  if not text:continue
  text=clean(str(text));tags=[]
  match=re.match(r'^\[([^]]+)\]\s*',text)
  if match:tags=[clean(v) for v in match[1].split(',')];text=text[match.end():]
  match=re.match(r'^\(([^)]+)\)\s*',text);publisher=match[1] if match else ''
  if match:text=text[match.end():]
  parts=re.findall(r'\d+',str(date));date='-'.join([parts[0],parts[1].zfill(2),parts[2].zfill(2)]) if len(parts)==3 else ''
  url=safe_url(row[1].hyperlink.target) if row[1].hyperlink else ''
  items.append(dict(id=f'news-{row[0].row}',date=date,title=text,publisher=publisher,tags=tags,url=url,description='',image='',previewStatus='pending' if url else 'no_url'))
 return sorted(items,key=lambda r:(r['date'],int(r['id'].split('-')[1])),reverse=True)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('file',nargs='?');parser.add_argument('--refresh',action='store_true');parser.add_argument('--previews',action='store_true');args=parser.parse_args()
 previous=json.loads(Path('data/news.json').read_text()) if args.refresh else None
 if not args.refresh and not args.file:parser.error('file 또는 --refresh가 필요합니다')
 items=previous['items'] if args.refresh else read_workbook(args.file)
 if args.previews or args.refresh:
  with ThreadPoolExecutor(max_workers=6) as pool:items=list(pool.map(preview,items))
 data=dict(updatedAt=datetime.now(timezone.utc).isoformat(),source=previous['source'] if previous else Path(args.file).name,totalCount=len(items),items=items)
 Path('data/news.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f'::notice title=News previews::기사 {len(items)}건 · 링크 {sum(bool(r["url"]) for r in items)}건 · 설명 {sum(bool(r["description"]) for r in items)}건 · 이미지 {sum(bool(r["image"]) for r in items)}건')
if __name__=='__main__':main()
