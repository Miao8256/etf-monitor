from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.parse import urlencode, urlparse
from pathlib import Path
import json, concurrent.futures, datetime, time

ROOT=Path(__file__).resolve().parent
CODES=['510300','510310','159919','510050','510500','512100','159845','159633','560010','588000','588080','159915','159952','159949','563360','159352','159338','512050','159361','510180']
NAMES=['沪深300华泰柏瑞','沪深300易方达','沪深300嘉实','上证50华夏','中证500南方','中证1000南方','中证1000华夏','中证1000易方达','中证1000广发','科创50华夏','科创50易方达','创业板易方达','创业板广发','创业板50华安','中证A500华泰柏瑞','中证A500南方','中证A500国泰','中证A500华夏','中证A500易方达','上证180华安']
CACHE={'at':0,'payload':None}

def get_one(code):
    market='1' if code.startswith(('5','6')) else '0'
    params={'fields1':'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13','fields2':'f51,f52,f53,f54,f55,f56,f57,f58','ut':'7eea3edcaed734bea9cbfc24409ed989','ndays':'5','iscr':'0','secid':f'{market}.{code}'}
    url='https://push2his.eastmoney.com/api/qt/stock/trends2/get?'+urlencode(params)
    req=Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://quote.eastmoney.com/'})
    with urlopen(req,timeout=9) as r: raw=json.load(r)
    d=raw.get('data') or {}
    return {'code':code,'name':NAMES[CODES.index(code)] if code in CODES else '上证指数','trends':d.get('trends') or [],'preClose':d.get('preClose')}

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
    def do_GET(self):
        if urlparse(self.path).path != '/api/data':return super().do_GET()
        if time.time()-CACHE['at']<48 and CACHE['payload'] is not None:
            return self.respond(CACHE['payload'])
        codes=CODES+['000001']
        results={}; errors=[]
        with concurrent.futures.ThreadPoolExecutor(max_workers=7) as ex:
            fut={ex.submit(get_one,c):c for c in codes}
            for f in concurrent.futures.as_completed(fut):
                c=fut[f]
                try:results[c]=f.result()
                except Exception as e:errors.append(f'{c}: {str(e)[:85]}')
        payload={'fetchedAt':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'results':results,'errors':errors,'codes':CODES}
        if results:CACHE.update(at=time.time(),payload=payload)
        self.respond(payload,status=200 if results else 502)
    def respond(self,obj,status=200):
        body=json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)

if __name__=='__main__':
    print('打开 http://localhost:8765  查看监测面板；Ctrl+C 停止')
    ThreadingHTTPServer(('0.0.0.0',int(__import__('os').environ.get('PORT','8765'))),Handler).serve_forever()
