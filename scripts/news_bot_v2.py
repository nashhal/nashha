#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""نشهل: جامع أخبار موثوقة مع حماية البيانات من المسح عند فشل المصادر."""
import hashlib
import html
import json
import os
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse

import feedparser
import requests

OUT = "data/news.json"
MAX_ITEMS = 120
REQUEST_TIMEOUT = 25
AI_TIMEOUT = 90

# مصادر RSS موثوقة + رسمية. المصادر المحلية الحزبية لا تدخل تلقائيًا.
TRUSTED_FEEDS = [
    ("بي بي سي عربي", "https://feeds.bbci.co.uk/arabic/rss.xml", "دولي"),
    ("فرانس 24 عربي", "https://www.france24.com/ar/rss", "دولي"),
    ("الجزيرة", "https://www.aljazeera.net/xml/rss/all.xml", "عربي"),
    ("سبأ", "https://www.sabanew.net/rss.php?lang=ar", "يمني"),
]

OFFICIAL_PAGES = [
    ("رئاسة مجلس القيادة الرئاسي", "https://www.presidentalalimi.net/cat1.html", "رسمي"),
    ("وزارة الخارجية اليمنية", "https://www.mofa-ye.org/Pages/category/mofa-news/", "رسمي"),
    ("وزارة الداخلية اليمنية", "https://www.moi-gov-ye.org/page/المركز-الإعلامي", "رسمي"),
    ("الأمم المتحدة في اليمن", "https://yemen.un.org/ar", "دولي"),
]

KEYWORDS = [
    "اليمن", "اليمني", "اليمنية", "عدن", "حضرموت", "شبوة", "أبين", "لحج",
    "الضالع", "المهرة", "سقطرى", "الجنوب", "الجنوبي", "القضية الجنوبية",
    "المقاومة الجنوبية", "الحوثي", "الحوثيون", "الحوثيين", "أنصار الله",
    "مجلس القيادة الرئاسي", "الحكومة اليمنية", "باب المندب", "البحر الأحمر",
]
SOUTH = [
    "عدن", "حضرموت", "شبوة", "أبين", "لحج", "الضالع", "المهرة", "سقطرى",
    "الجنوب", "الجنوبي", "القضية الجنوبية", "المقاومة الجنوبية",
]
EXCLUDED = [
    "كرة القدم", "كأس العالم", "الدوري", "دوري أبطال", "المباراة", "مباراة",
    "منتخب", "لاعب", "لاعبة", "مدرب", "رياضة", "رياضي", "رياضية", "فيفا",
    "football", "soccer", "fifa", "match", "champions league", "premier league",
    "موسيقى", "أغنية", "فنان", "فنانة", "ممثل", "ممثلة", "مشاهير", "سينما",
    "مسلسل", "فيلم", "ترفيه", "حفلة", "حفل غنائي", "تيك توك", "إنستغرام", "مؤثر",
]

HEADERS = {"User-Agent": "NashhalNews/7.0 (+https://nashhal.github.io/nashha/)"}


def clean(value):
    value = html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    return re.sub(r"\s+", " ", value).strip()


def domain(url):
    return urlparse(str(url)).netloc.lower().removeprefix("www.")


def relevant(title, summary):
    text = f"{title} {summary}".lower()
    if any(word.lower() in text for word in EXCLUDED):
        return False
    return any(word.lower() in text for word in KEYWORDS)


def is_south(title, summary):
    text = f"{title} {summary}".lower()
    return any(word.lower() in text for word in SOUTH)


def parse_date(value):
    if not value:
        return None
    for parser in (
        lambda: parsedate_to_datetime(str(value)),
        lambda: datetime.fromisoformat(str(value).replace("Z", "+00:00")),
    ):
        try:
            dt = parser()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            pass
    return None


def item_id(source, link):
    return hashlib.sha256(f"{source}|{link}".encode()).hexdigest()[:20]


def make_item(source, source_type, title, link, summary, published, platform="news", embed_url=""):
    title, link, summary = clean(title), clean(link), clean(summary)
    if not title or not link.startswith(("http://", "https://")):
        return None
    if not relevant(title, summary):
        return None
    published = parse_date(published) or datetime.now(timezone.utc).isoformat()
    return {
        "id": item_id(source, link),
        "title": title,
        "original_title": title,
        "source": source,
        "source_name": source,
        "source_url": link,
        "link": link,
        "published": published,
        "published_at": published,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "category": "الجنوب" if is_south(title, summary) else "اليمن",
        "status": "published",
        "confidence": "high" if source_type in ("يمني", "عربي", "دولي", "رسمي") else "medium",
        "auto_published": True,
        "summary": summary[:900],
        "description": summary[:300],
        "content": summary[:900],
        "title_en": "",
        "summary_en": "",
        "platform": platform,
        "source_type": source_type,
        "rewrite_status": "source_text",
        "embed_url": embed_url,
    }


def collect_rss():
    found = []
    for source, url, source_type in TRUSTED_FEEDS:
        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            if not feed.entries:
                raise RuntimeError(f"RSS returned no entries (bozo={getattr(feed, 'bozo', False)})")
            before = len(found)
            for entry in feed.entries[:60]:
                item = make_item(
                    source,
                    source_type,
                    entry.get("title"),
                    entry.get("link", ""),
                    entry.get("summary") or entry.get("description"),
                    entry.get("published") or entry.get("updated"),
                )
                if item:
                    item["_raw"] = clean(
                        entry.get("summary") or entry.get("description") or entry.get("title")
                    )[:3000]
                    found.append(item)
            print(f"[OK] RSS {source}: {len(found) - before} relevant")
        except Exception as exc:
            print(f"[WARN] RSS {source}: {exc}")
    return found


def extract_links(base, raw):
    links = []
    pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
    for href, title in re.findall(pattern, raw, re.I | re.S):
        title = clean(title)
        url = urljoin(base, html.unescape(href))
        if len(title) >= 25 and url.startswith(("http://", "https://")):
            links.append((title, url))
    seen = set()
    result = []
    for value in links:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result[:60]


def fetch_article(url, fallback_title):
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        raw = response.text
        title_match = re.search(r"<h1[^>]*>(.*?)</h1>", raw, re.I | re.S)
        title = clean(title_match.group(1)) if title_match else clean(fallback_title)
        paragraphs = [clean(x) for x in re.findall(r"<p[^>]*>(.*?)</p>", raw, re.I | re.S)]
        paragraphs = [x for x in paragraphs if len(x) > 45]
        date_match = re.search(r"(20\d{2}[-/]\d{1,2}[-/]\d{1,2})", raw)
        return title, " ".join(paragraphs[:8])[:3200], date_match.group(1) if date_match else None
    except Exception:
        return clean(fallback_title), "", None


def collect_official_pages():
    found = []
    for source, base, source_type in OFFICIAL_PAGES:
        try:
            response = requests.get(base, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            links = extract_links(base, response.text)
            before = len(found)
            for title, url in links:
                article_title, summary, published = fetch_article(url, title)
                item = make_item(source, source_type, article_title, url, summary, published)
                if item:
                    item["_raw"] = summary[:3200]
                    found.append(item)
            print(f"[OK] PAGE {source}: {len(found) - before} relevant")
        except Exception as exc:
            print(f"[WARN] PAGE {source}: {exc}")
    return found


def response_text(data):
    parts = []
    for output in data.get("output", []):
        if output.get("type") != "message":
            continue
        for content in output.get("content", []):
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
    prompt = """أنت محرر أخبار لمنصة نشهل اليمنية. ابحث عن أحدث التطورات الموثوقة المتعلقة باليمن، مع أولوية للجنوب اليمني، خلال آخر 24 ساعة. استخدم البحث على الويب وX فقط كوسيلة رصد، ولا تعتمد على منشور منفرد غير مؤكد.

أعد JSON فقط بهذا الشكل:
[{"title":"...","summary":"...","source_name":"...","source_url":"https://...","published":"ISO-8601 أو فارغ","category":"الجنوب أو اليمن"}]

قواعد:
- بحد أقصى 8 أخبار.
- كل عنصر يجب أن يحتوي رابط مصدر مباشر صالحًا.
- لا تخترع روابط أو أسماء مصادر.
- استبعد الرياضة وكرة القدم والترفيه والمحتوى غير المرتبط جوهريًا باليمن.
- استبعد الشائعات والآراء غير الموثقة.
- اكتب بالعربية وبصياغة خبرية محايدة.
"""
    try:
        response = requests.post(
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
        response.raise_for_status()
        data = response.json()
        text = response_text(data)
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            print("[WARN] Grok لم يُرجع JSON صالحًا")
            return []
        raw = json.loads(match.group(0))
        if not isinstance(raw, list):
            return []
        citations = {
            normalize_url(value)
            for value in data.get("citations", [])
            if isinstance(value, str) and value.startswith(("http://", "https://"))
        }
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
                continue
            item = make_item("Grok / " + source_name, "grok_verified", title, source_url, summary, published)
            if item:
                item["source"] = source_name
                item["source_name"] = source_name
                item["source_type"] = "grok_verified"
                item["confidence"] = "high"
                item["auto_published"] = True
                item["_raw"] = summary[:3000]
                result.append(item)
        print(f"[OK] Grok: {len(result)} verified")
        return result
    except Exception as exc:
        print(f"[WARN] Grok: {exc}")
        return []


def rewrite_with_ai(item):
    token = os.getenv("XAI_API_KEY")
    raw = clean(item.get("_raw", ""))
    title = clean(item.get("original_title", item.get("title", "")))
    if not token or not raw:
        item.pop("_raw", None)
        return item

    prompt = f"""أنت محرر أخبار محترف لمنصة نشهل. أعد تحرير المادة الرسمية التالية بالعربية والإنجليزية.
استخدم المعلومات الموجودة فقط، ولا تضف حقائق أو أرقامًا أو أسماء أو اقتباسات. لا تنسخ الصياغة حرفيًا. اجعل العنوان مباشرًا ومحايدًا.

العنوان: {title}
النص: {raw}

أعد JSON فقط: {{\"title_ar\":\"...\",\"summary_ar\":\"...\",\"title_en\":\"...\",\"summary_en\":\"...\"}}"""
    try:
        response = requests.post(
            "https://api.x.ai/v1/responses",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "model": "grok-4.5",
                "input": [{"role": "user", "content": prompt}],
                "include": ["no_inline_citations"],
            },
            timeout=AI_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        text = response_text(data)
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            item.pop("_raw", None)
            return item
        result = json.loads(match.group(0))
        item["title_en"] = clean(result.get("title_en", ""))
        item["summary_en"] = clean(result.get("summary_en", ""))
        title_ar = clean(result.get("title_ar", ""))
        summary_ar = clean(result.get("summary_ar", ""))
        if title_ar:
            item["title"] = title_ar[:300]
        if summary_ar:
            item["summary"] = summary_ar[:900]
            item["description"] = item["summary"][:300]
            item["content"] = item["summary"]
        item["rewrite_status"] = "editorial_rewrite_bilingual"
    except Exception as exc:
        print(f"[WARN] AI rewrite: {exc}")
    item.pop("_raw", None)
    return item


def valid_old_items(raw):
    result = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        if not item.get("id"):
            continue
        if clean(item.get("status", "published")) == "published" and not item.get("source_url", item.get("link", "")):
            continue
        result.append(item)
    return result


def dedupe(items):
    by_id = {}
    for item in items:
        if item and item.get("id"):
            by_id[item["id"]] = item
    return sorted(by_id.values(), key=lambda x: x.get("published_at") or x.get("published") or "", reverse=True)


def load_existing():
    try:
        with open(OUT, encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            data = data.get("news", data.get("items", []))
        return valid_old_items(data)
    except Exception as exc:
        print(f"[WARN] تعذر قراءة البيانات الحالية: {exc}")
        return []


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    existing = load_existing()

    rss_items = collect_rss()
    page_items = collect_official_pages()
    grok_items = collect_grok()
    fresh = rss_items + page_items + grok_items
    fresh = [rewrite_with_ai(item) for item in fresh]

    # أهم حماية: لا تسمح لجولة فاشلة من المصادر بإفراغ قاعدة الأخبار.
    if not fresh:
        if existing:
            print(f"[SAFE] لم تصل أخبار جديدة؛ الإبقاء على {len(existing)} خبرًا موجودًا.")
            return
        print("[WARN] لم تصل أي أخبار ولا توجد بيانات سابقة؛ لن يتم تغيير الملف.")
        return

    merged = dedupe(existing + fresh)[:MAX_ITEMS]
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(merged, handle, ensure_ascii=False, indent=2)
    print(f"[DONE] {len(merged)} news records; {len(fresh)} fresh records")


if __name__ == "__main__":
    main()
