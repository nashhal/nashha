#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nashhal: collect from official/primary sources, editorially rewrite in Arabic and English."""
import hashlib, html, json, os, re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse
import feedparser, requests

OUT='data/news.json'; MAX_ITEMS=120; TIMEOUT=25; AI_TIMEOUT=90
OFFICIAL_RSS=[('وكالة سبأ','https://www.sabanew.net/rss.php?lang=ar','official_agency')]
OFFICIAL_PAGES=[
 ('رئاسة مجلس القيادة الرئاسي','https://www.presidentalalimi.net/cat1.html','official_presidency'),
 ('وزارة الخارجية اليمنية','https://www.mofa-ye.org/Pages/category/mofa-news/','official_ministry'),
 ('وزارة الداخلية اليمنية','https://www.moi-gov-ye.org/page/المركز-الإعلامي','official_security'),
 ('الأمم المتحدة في اليمن','https://yemen.un.org/ar','international_official'),
]
BLOCKED_DOMAINS={'bbc.co.uk','bbc.com','france24.com','aljazeera.net','alayyam.info','adenalghad.net','almasdaronline.com','aljanoubalyoum.tv'}
KEYWORDS=['اليمن','اليمني','اليمنية','عدن','حضرموت','شبوة','أبين','لحج','الضالع','المهرة','سقطرى','الجنوب','الجنوبي','القضية الجنوبية','الحوثي','الحوثيون','أنصار الله','مجلس القيادة الرئاسي','الحكومة اليمنية']
SOUTH=['عدن','حضرموت','شبوة','أبين','لحج','الضالع','المهرة','سقطرى','الجنوب','الجنوبي','القضية الجنوبية']
EXCLUDED=['كرة القدم','كأس العالم','الدوري','المباراة','منتخب','لاعب','مدرب','رياضة','فيفا','football','soccer','fifa','match','موسيقى','أغنية','فنان','ممثل','مشاهير','سينما','مسلسل','فيلم','ترفيه']
HEADERS={'User-Agent':'NahshalNews/6.0 (+https://nashhal.github.io/nashha/)'}

def clean(v): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',str(v or '')))).strip()
def domain(u): return urlparse(str(u)).netloc.lower().removeprefix('www.')
def blocked(source,url):
    d=domain(url); return clean(source) in {'بي بي سي عربي','فرانس 24 عربي','الجزيرة','الأيام','عدن الغد','المصدر أونلاين'} or d in BLOCKED_DOMAINS or any(d.endswith('.'+x) for x in BLOCKED_DOMAINS)
def relevant(t,s):
    x=f'{t} {s}'.lower(); return not any(k.lower() in x for k in EXCLUDED) and any(k.lower() in x for k in KEYWORDS)
def south(t,s):
    x=f'{t} {s}'.lower(); return any(k.lower() in x for k in SOUTH)
def date(v):
    if not v:return None
    for fn in (lambda:parsedate_to_datetime(str(v)),lambda:datetime.fromisoformat(str(v).replace('Z','+00:00'))):
        try:
            d=fn(); d=d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d; return d.astimezone(timezone.utc).isoformat()
        except Exception: pass
    return None
def iid(source,link): return hashlib.sha256(f'{source}|{link}'.encode()).hexdigest()[:20]
def make_item(source,stype,title,link,summary,published):
    title,link,summary=clean(title),clean(link),clean(summary)
    if not title or not link.startswith(('http://','https://')) or blocked(source,link) or not relevant(title,summary): return None
    p=date(published) or datetime.now(timezone.utc).isoformat()
    return {'id':iid(source,link),'title':title,'original_title':title,'source':source,'source_name':source,'source_url':link,'link':link,'published':p,'published_at':p,'collected_at':datetime.now(timezone.utc).isoformat(),'category':'الجنوب' if south(title,summary) else 'اليمن','status':'published','confidence':'high','auto_published':True,'summary':summary[:900],'description':summary[:300],'content':summary[:900],'title_en':'','summary_en':'','platform':'official','source_type':stype,'rewrite_status':'source_text'}
def rss():
    out=[]
    for source,url,stype in OFFICIAL_RSS:
        try:
            f=feedparser.parse(requests.get(url,headers=HEADERS,timeout=TIMEOUT).content)
            for e in f.entries[:60]:
                it=make_item(source,stype,e.get('title'),e.get('link',''),e.get('summary') or e.get('description'),e.get('published') or e.get('updated'))
                if it: it['_raw']=clean(e.get('summary') or e.get('description') or e.get('title'))[:3000]; out.append(it)
        except Exception as ex: print('[WARN] RSS',source,ex)
    return out
def links(base,raw):
    found=[]
    for href,title in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',raw,re.I|re.S):
        title=clean(title); url=urljoin(base,html.unescape(href))
        if len(title)>=25 and url.startswith(('http://','https://')): found.append((title,url))
    seen=set(); out=[]
    for x in found:
        if x not in seen: seen.add(x); out.append(x)
    return out[:45]
def article(url,fallback):
    try:
        r=requests.get(url,headers=HEADERS,timeout=TIMEOUT); r.raise_for_status(); raw=r.text
        hm=re.search(r'<h1[^>]*>(.*?)</h1>',raw,re.I|re.S); t=clean(hm.group(1)) if hm else clean(fallback)
        ps=[clean(x) for x in re.findall(r'<p[^>]*>(.*?)</p>',raw,re.I|re.S)]; ps=[x for x in ps if len(x)>45]
        d=re.search(r'(20\d{2}[-/]\d{1,2}[-/]\d{1,2})',raw); return t,' '.join(ps[:6])[:3200],d.group(1) if d else None
    except Exception:return clean(fallback),'',None
def pages():
    out=[]
    for source,base,stype in OFFICIAL_PAGES:
        try:
            r=requests.get(base,headers=HEADERS,timeout=TIMEOUT); r.raise_for_status()
            for t,u in links(base,r.text):
                if blocked(source,u): continue
                at,s,d=article(u,t)
                it=make_item(source,stype,at,u,s,d)
                if it: it['_raw']=s[:3200]; out.append(it)
        except Exception as ex: print('[WARN] PAGE',source,ex)
    return out
def ai(item):
    token=os.getenv('XAI_API_KEY'); raw=clean(item.get('_raw','')); title=clean(item.get('original_title',item.get('title','')))
    if not token or not raw:return item
    prompt=f'''أنت محرر أخبار محترف لمنصة نشهل. أعد تحرير المادة الرسمية التالية بالعربية والإنجليزية.
قواعد صارمة: استخدم المعلومات الموجودة فقط، لا تضف حقائق أو أرقام أو أسماء أو سياقًا، لا تنسخ الصياغة حرفيًا، اجعل العنوان مباشرًا وغير مثير، وإذا كان النص موقفًا رسميًا انسبه للجهة، ولا تخترع اقتباسات.
العنوان العربي: {title}
النص الرسمي: {raw}
أعد JSON فقط: {{"title_ar":"...","summary_ar":"...","title_en":"...","summary_en":"..."}}'''
    try:
        r=requests.post('https://api.x.ai/v1/responses',headers={'Authorization':f'Bearer {token}','Content-Type':'application/json'},json={'model':'grok-4.5','input':[{'role':'user','content':prompt}],'include':['no_inline_citations']},timeout=AI_TIMEOUT); r.raise_for_status(); data=r.json(); text='\n'.join(c.get('text','') for o in data.get('output',[]) if o.get('type')=='message' for c in o.get('content',[]) if c.get('type')=='output_text'); m=re.search(r'\{[\s\S]*\}',text)
        if not m:return item
        x=json.loads(m.group(0));
        for k in ('title_ar','summary_ar','title_en','summary_en'):
            item[k]=clean(x.get(k,''))
        if item.get('title_ar'): item['title']=item['title_ar'][:300]
        if item.get('summary_ar'): item['summary']=item['summary_ar'][:900]; item['description']=item['summary'][:300]; item['content']=item['summary']
        item['rewrite_status']='editorial_rewrite_bilingual'
    except Exception as ex: print('[WARN] AI',ex)
    item.pop('_raw',None); item.pop('title_ar',None); item.pop('summary_ar',None); return item
def main():
    os.makedirs('data',exist_ok=True); old=[]
    try:
        loaded=json.load(open(OUT,encoding='utf-8')); loaded=loaded.get('news',[]) if isinstance(loaded,dict) else loaded
        old=[x for x in loaded if isinstance(x,dict) and x.get('status')=='published' and x.get('auto_published') is True and str(x.get('source_type','')).startswith('official') and not blocked(x.get('source'),x.get('source_url'))]
    except Exception: pass
    fresh=[ai(x) for x in rss()+pages()]
    by={x.get('id'):x for x in old if x.get('id')}
    by.update({x.get('id'):x for x in fresh if x.get('id')})
    final=sorted(by.values(),key=lambda x:x.get('published_at',''),reverse=True)[:MAX_ITEMS]
    with open(OUT,'w',encoding='utf-8') as f: json.dump(final,f,ensure_ascii=False,indent=2)
    print(f'[DONE] {len(final)} official stories; {len(fresh)} new')
if __name__=='__main__': main()
