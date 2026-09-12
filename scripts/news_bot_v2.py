#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""نشهل - جامع أخبار موثوقة مع تواريخ ومصادر وصفحات خبر داخلية."""
import hashlib, html, json, os, re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import requests
import feedparser

OUT = "data/news.json"
MAX_ITEMS = 120
REQUEST_TIMEOUT = 20

TRUSTED_FEEDS = [
    ("بي بي سي عربي", "https://feeds.bbci.co.uk/arabic/rss.xml", "دولي"),
    ("فرانس 24 عربي", "https://www.france24.com/ar/rss", "دولي"),
    ("الجزيرة", "https://www.aljazeera.net/xml/rss/all.xml", "عربي"),
    ("سبأ", "https://www.sabanew.net/rss.php?lang=ar", "يمني"),
    ("الأيام", "https://www.alayyam.info/rss", "يمني"),
    ("عدن الغد", "https://www.adenalghad.net/rss", "يمني"),
    ("المصدر أونلاين", "https://almasdaronline.com/rss", "يمني"),
]

KEYWORDS = [
    "اليمن", "اليمني", "اليمنية", "عدن", "حضرموت", "شبوة", "أبين", "لحج",
    "الضالع", "المهرة", "سقطرى", "الجنوب", "الجنوبي", "القضية الجنوبية",
    "المقاومة الجنوبية", "الحوثي", "الحوثيون", "الحوثيين", "أنصار الله", "مجلس القيادة الرئاسي",
]
SOUTH = ["عدن", "حضرموت", "شبوة", "أبين", "لحج", "الضالع", "المهرة", "سقطرى", "الجنوب", "الجنوبي", "القضية الجنوبية", "المقاومة الجنوبية"]
EXCLUDED_KEYWORDS = [
    "كرة القدم", "كأس العالم", "الدوري", "دوري أبطال", "المباراة", "مباراة", "منتخب",
    "لاعب", "لاعبة", "مدرب", "مدربًا", "رياضة", "رياضي", "رياضية", "فيفا", "الاتحاد الدولي لكرة القدم",
    "goal", "football", "soccer", "fifa", "match", "champions league", "premier league",
    "موسيقى", "أغنية", "فنان", "فنانة", "ممثل", "ممثلة", "مشاهير", "سينما", "مسلسل", "فيلم",
    "ترفيه", "حفلة", "حفل غنائي", "تيك توك", "إنستغرام", "مؤثر", "مؤثرة",
]

HEADERS = {"User-Agent": "NahshalNews/2.0 (+https://nashhal.github.io/nashha/)"}

def clean(v):
    v = html.unescape(re.sub(r"<[^>]+>", " ", str(v or "")))
    return re.sub(r"\s+", " ", v).strip()

def relevant(title, summary):
    text = f"{title} {summary}".lower()
    if any(k.lower() in text for k in EXCLUDED_KEYWORDS):
        return False
    return any(k.lower() in text for k in KEYWORDS)

def is_south(title, summary):
    text = f"{title} {summary}".lower()
    return any(k.lower() in text for k in SOUTH)

def parse_date(value):
    if not value:
        return None
    try:
        d = parsedate_to_datetime(value)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).isoformat()
    except Exception:
        try:
            d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d.astimezone(timezone.utc).isoformat()
        except Exception:
            return None

def item_id(source, link):
    return hashlib.sha256(f"{source}|{link}".encode()).hexdigest()[:20]

def make_item(source, source_type, title, link, summary, published, platform="news", embed_url=""):
    title, link, summary = clean(title), clean(link), clean(summary)
    if not title or not link or not link.startswith(("http://", "https://")):
        return None
    if not relevant(title, summary):
        return None
    published = parse_date(published) or datetime.now(timezone.utc).isoformat()
    south = is_south(title, summary)
    return {
        "id": item_id(source, link),
        "title": title,
        "source": source,
        "source_name": source,
        "source_url": link,
        "link": link,
        "published": published,
        "published_at": published,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "category": "الجنوب" if south else "اليمن",
        "status": "published",
        "confidence": "high" if source_type in ("يمني", "عربي", "دولي") else "medium",
        "auto_published": True,
        "summary": summary[:900],
        "description": summary[:300],
        "content": summary[:900],
        "platform": platform,
        "source_type": source_type,
        "embed_url": embed_url,
    }

def collect_rss():
    found = []
    for source, url, source_type in TRUSTED_FEEDS:
        try:
            feed = feedparser.parse(requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT).content)
            for entry in feed.entries[:50]:
                item = make_item(
                    source, source_type,
                    entry.get("title"), entry.get("link"),
                    entry.get("summary") or entry.get("description"),
                    entry.get("published") or entry.get("updated"),
                )
                if item:
                    found.append(item)
            print(f"[OK] {source}: {len(found)} cumulative")
        except Exception as exc:
            print(f"[WARN] RSS {source}: {exc}")
    return found

def collect_x():
    token = os.getenv("X_BEARER_TOKEN")
    if not token:
        print("[INFO] X token غير مضبوط؛ تخطي X")
        return []

    query = clean(os.getenv(
        "X_SEARCH_QUERY",
        "(اليمن OR عدن OR حضرموت OR شبوة OR أبين OR لحج OR الضالع OR المهرة OR سقطرى OR الجنوب OR الحوثي) -is:retweet lang:ar"
    ))
    try:
        r = requests.get(
            "https://api.x.com/2/tweets/search/recent",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "query": query,
                "max_results": 20,
                "tweet.fields": "created_at,author_id,text,lang",
            },
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        result = []
        for p in r.json().get("data", []):
            text = clean(p.get("text"))
            pid = p.get("id")
            if not text or not pid:
                continue
            link = f"https://x.com/i/web/status/{pid}"
            item = make_item("X", "social_public", text[:180], link, text, p.get("created_at"), "X", link)
            if item:
                # X is an early-warning signal, not an automatic publication source.
                item["status"] = "review"
                item["auto_published"] = False
                item["confidence"] = "low"
                item["review_label"] = "قيد التحقق"
                result.append(item)
        print(f"[OK] X: {len(result)} إشارة مبكرة للمراجعة")
        return result
    except Exception as exc:
        print(f"[WARN] X: {exc}")
        return []

def collect_facebook():
    page_id, token = os.getenv("FACEBOOK_PAGE_ID"), os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    if not page_id or not token:
        print("[INFO] Facebook credentials غير مضبوطة؛ تخطي Facebook")
        return []
    try:
        r = requests.get(f"https://graph.facebook.com/{page_id}/posts", params={"access_token": token, "fields": "id,message,created_time,permalink_url", "limit": 20}, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        result = []
        for p in r.json().get("data", []):
            text, link = clean(p.get("message")), clean(p.get("permalink_url"))
            item = make_item("Facebook", "social_public", text[:180], link, text, p.get("created_time"), "Facebook", link)
            if item:
                item["status"] = "review"
                item["auto_published"] = False
                item["confidence"] = "medium"
                result.append(item)
        print(f"[OK] Facebook: {len(result)} منشور للمراجعة")
        return result
    except Exception as exc:
        print(f"[WARN] Facebook: {exc}")
        return []

def response_text(data):
    parts = []
    for item in data.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                parts.append(content.get("text", ""))
    return "\n".join(parts).strip()

def normalize_url(url):
    return clean(url).rstrip("/")

def collect_grok():
    token = os.getenv("XAI_API_KEY")
    if not token:
        print("[INFO] XAI_API_KEY غير مضبوط؛ تخطي Grok")
        return []
    now = datetime.now(timezone.utc)
    from_date = (now - timedelta(days=1)).date().isoformat()
    to_date = now.date().isoformat()
    prompt = """أنت محرر أخبار لمنصة نشهل اليمنية. ابحث الآن عن أحدث التطورات الموثوقة المتعلقة باليمن، مع أولوية خاصة للجنوب اليمني والمقاومة الجنوبية، باستخدام Web Search وX Search. ركّز على آخر 24 ساعة. لا تذكر أي خبر بلا مصدر يمكن فتحه، وتجنب الشائعات والآراء غير الموثقة والمحتوى المكرر.

أعد النتيجة JSON فقط، بدون Markdown أو روابط استشهاد داخل النص، بهذا الشكل:
[{"title":"...","summary":"...","source_name":"...","source_url":"https://...","published":"ISO-8601 أو فارغ","category":"الجنوب أو اليمن"}]

قواعد صارمة:
- بحد أقصى 8 أخبار.
- كل عنصر يجب أن يحتوي عنوانًا وملخصًا قصيرًا ورابط مصدر مباشر صالحًا.
- لا تخترع روابط أو أسماء مصادر.
- يجب أن يكون source_url رابطًا لمصدر عثرت عليه أثناء البحث.
- إذا لم تجد أخبارًا موثوقة، أعد [] فقط.
- لا تنشئ خبرًا اعتمادًا على منشور X واحد غير مؤكد؛ استخدمه كإشارة، وحاول تأكيده من مصدر آخر عند الإمكان.
- اكتب بالعربية وبصياغة خبرية محايدة.
- لا تُرجع أي خبر رياضي أو عن كرة القدم أو البطولات أو اللاعبين أو الأندية أو المشاهير أو الترفيه، حتى لو ورد فيه اسم اليمن أو مدينة يمنية.
- لا تُرجع أي خبر عامًا لا يرتبط بالشأن اليمني السياسي أو الأمني أو العسكري أو الإنساني أو الاقتصادي أو المحلي.
- إذا كان الخبر عن اليمن فقط بسبب مباراة أو لاعب أو منتخب أو بطولة، استبعده تمامًا.
- يجب أن يكون جوهر الخبر متعلقًا باليمن، وليس مجرد ذكر عابر لمكان أو شخص يمني."""
    try:
        r = requests.post(
            "https://api.x.ai/v1/responses",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "model": "grok-4.5",
                "input": [{"role": "user", "content": prompt}],
                "tools": [
                    {"type": "web_search"},
                    {"type": "x_search", "from_date": from_date, "to_date": to_date},
                ],
                "include": ["no_inline_citations"],
            },
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        text = response_text(data)
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            print("[WARN] Grok لم يُرجع JSON صالحًا")
            return []
        raw = json.loads(match.group(0))
        if not isinstance(raw, list):
            return []
        citations = {normalize_url(u) for u in data.get("citations", []) if isinstance(u, str) and u.startswith(("http://", "https://"))}
        result = []
        for candidate in raw:
            if not isinstance(candidate, dict):
                continue
            title = clean(candidate.get("title"))
            summary = clean(candidate.get("summary"))
            source_name = clean(candidate.get("source_name"))
            source_url = clean(candidate.get("source_url"))
            published = candidate.get("published") or ""
            if not title or not summary or not source_name or not source_url.startswith(("http://", "https://")):
                continue
            if citations and normalize_url(source_url) not in citations:
                print(f"[WARN] تجاهل Grok خبرًا برابط غير موجود ضمن المصادر: {source_url}")
                continue
            item = make_item("Grok / " + source_name, "grok_verified", title, source_url, summary, published)
            if item:
                item["source_name"] = source_name
                item["source"] = source_name
                item["source_type"] = "grok_verified"
                item["confidence"] = "high"
                item["auto_published"] = True
                result.append(item)
        print(f"[OK] Grok: {len(result)} خبرًا موثقًا")
        return result
    except Exception as exc:
        print(f"[WARN] Grok: {exc}")
        return []

def dedupe(items):
    by_id = {}
    for item in items:
        if item and item.get("id"):
            by_id[item["id"]] = item
    return sorted(by_id.values(), key=lambda x: x.get("published_at", ""), reverse=True)

def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    try:
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
        if not isinstance(old, list):
            old = old.get("news", []) if isinstance(old, dict) else []
    except Exception:
        old = []
    existing = {x.get("id"): x for x in old if isinstance(x, dict) and x.get("id")}
    # X is collected first as the rapid signal layer, then RSS/social sources, then verification.
    fresh = collect_x() + collect_rss() + collect_facebook() + collect_grok()
    for item in fresh:
        existing[item["id"]] = item
    final = dedupe(list(existing.values()))[:MAX_ITEMS]
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print(f"[DONE] {len(final)} news records; {len(fresh)} fresh records")

if __name__ == "__main__":
    main()
