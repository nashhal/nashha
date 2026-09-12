#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""نشهل - منصة أخبار تجمع من المصادر الرسمية/الأولية ثم تعيد التحرير صحفيًا."""
import hashlib
import html
import json
import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

import feedparser
import requests

OUT = "data/news.json"
MAX_ITEMS = 120
REQUEST_TIMEOUT = 25
REWRITE_TIMEOUT = 90

# لا توجد هنا BBC أو الجزيرة أو فرنسا 24 أو أي قناة إخبارية.
# سبأ تُستخدم كوكالة أنباء رسمية، بينما بقية المواد تأتي من مواقع الجهات نفسها.
OFFICIAL_RSS = [
    ("وكالة سبأ", "https://www.sabanew.net/rss.php?lang=ar", "official_agency"),
]

OFFICIAL_PAGES = [
    ("رئاسة مجلس القيادة الرئاسي", "https://www.presidentalalimi.net/cat1.html", "official_presidency"),
    ("وزارة الخارجية اليمنية", "https://www.mofa-ye.org/Pages/category/mofa-news/", "official_ministry"),
    ("وزارة الداخلية اليمنية", "https://www.moi-gov-ye.org/page/المركز-الإعلامي", "official_security"),
    ("الأمم المتحدة في اليمن", "https://yemen.un.org/ar", "international_official"),
]

# تمنع أي بقايا من النظام القديم من العودة إلى واجهة الأخبار.
BLOCKED_SOURCES = {
    "بي بي سي عربي", "فرانس 24 عربي", "الجزيرة", "الأيام", "عدن الغد", "المصدر أونلاين",
    "BBC Arabic", "France 24", "Al Jazeera", "BBC", "CNN", "Sky News",
}
BLOCKED_DOMAINS = {
    "bbc.co.uk", "bbc.com", "france24.com", "aljazeera.net", "alayyam.info",
    "adenalghad.net", "almasdaronline.com",
}

KEYWORDS = [
    "اليمن", "اليمني", "اليمنية", "عدن", "حضرموت", "شبوة", "أبين", "لحج",
    "الضالع", "المهرة", "سقطرى", "الجنوب", "الجنوبي", "القضية الجنوبية",
    "المقاومة الجنوبية", "الحوثي", "الحوثيون", "الحوثيين", "أنصار الله",
    "مجلس القيادة الرئاسي", "الحكومة اليمنية", "الأمم المتحدة في اليمن",
]
SOUTH = [
    "عدن", "حضرموت", "شبوة", "أبين", "لحج", "الضالع", "المهرة", "سقطرى",
    "الجنوب", "الجنوبي", "القضية الجنوبية", "المقاومة الجنوبية"
]
EXCLUDED_KEYWORDS = [
    "كرة القدم", "كأس العالم", "الدوري", "دوري أبطال", "المباراة", "مباراة", "منتخب",
    "لاعب", "لاعبة", "مدرب", "مدربًا", "رياضة", "رياضي", "رياضية", "فيفا",
    "الاتحاد الدولي لكرة القدم", "goal", "football", "soccer", "fifa", "match",
    "champions league", "premier league", "موسيقى", "أغنية", "فنان", "فنانة",
    "ممثل", "ممثلة", "مشاهير", "سينما", "مسلسل", "فيلم", "ترفيه", "حفلة",
    "حفل غنائي", "تيك توك", "إنستغرام", "مؤثر", "مؤثرة",
]
HEADERS = {"User-Agent": "NahshalNews/5.0 (+https://nashhal.github.io/nashha/)"}


def clean(value):
    value = html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    return re.sub(r"\s+", " ", value).strip()


def domain(url):
    m = re.search(r"https?://(?:www\.)?([^/]+)", str(url or "").lower())
    return m.group(1) if m else ""


def blocked(source, link):
    s = clean(source)
    d = domain(link)
    return s in BLOCKED_SOURCES or any(d == x or d.endswith("." + x) for x in BLOCKED_DOMAINS)


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
        d = parsedate_to_datetime(str(value))
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


def make_item(source, source_type, title, link, summary, published):
    title, link, summary = clean(title), clean(link), clean(summary)
    if not title or not link or not link.startswith(("http://", "https://")):
        return None
    if blocked(source, link) or not relevant(title, summary):
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
        "confidence": "high",
        "auto_published": True,
        "summary": summary[:900],
        "original_summary": summary[:1800],
        "description": summary[:300],
        "content": summary[:900],
        "platform": "official",
        "source_type": source_type,
        "rewrite_status": "source_text",
    }


def collect_official_rss():
    found = []
    for source, url, source_type in OFFICIAL_RSS:
        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            count = 0
            for entry in feed.entries[:60]:
                item = make_item(
                    source, source_type, entry.get("title"), entry.get("link"),
                    entry.get("summary") or entry.get("description"),
                    entry.get("published") or entry.get("updated"),
                )
                if item:
                    item["raw_source_text"] = clean(entry.get("summary") or entry.get("description") or entry.get("title"))[:2600]
                    found.append(item)
                    count += 1
            print(f"[OK] {source}: {count} خبرًا رسميًا")
        except Exception as exc:
            print(f"[WARN] RSS {source}: {exc}")
    return found


def extract_page_links(base_url, html_text):
    candidates = []
    patterns = [
        r'<h[1-4][^>]*>\s*<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>\s*([^<]{35,260})\s*</a>',
    ]
    for pattern in patterns:
        for match in re.findall(pattern, html_text, flags=re.I | re.S):
            href, title = match[0], clean(match[1])
            url = urljoin(base_url, html.unescape(href))
            if url.startswith(("http://", "https://")) and title and len(title) >= 25:
                candidates.append((title, url))
    unique = []
    seen = set()
    for title, url in candidates:
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)
        unique.append(key)
    return unique[:40]


def extract_article(url, fallback_title):
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        raw = response.text
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', raw, flags=re.I | re.S)
        title = clean(title_match.group(1)) if title_match else clean(fallback_title)
        paragraphs = [clean(x) for x in re.findall(r'<p[^>]*>(.*?)</p>', raw, flags=re.I | re.S)]
        paragraphs = [p for p in paragraphs if len(p) > 50]
        summary = " ".join(paragraphs[:5])[:2800]
        date_match = re.search(r'(20\d{2}[-/]\d{1,2}[-/]\d{1,2})', raw)
        published = date_match.group(1) if date_match else None
        return title, summary, published
    except Exception:
        return clean(fallback_title), "", None


def collect_official_pages():
    found = []
    for source, page_url, source_type in OFFICIAL_PAGES:
        try:
            response = requests.get(page_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            links = extract_page_links(page_url, response.text)
            count = 0
            for title, url in links:
                if blocked(source, url):
                    continue
                article_title, summary, published = extract_article(url, title)
                if not summary:
                    continue
                item = make_item(source, source_type, article_title, url, summary, published)
                if item:
                    item["raw_source_text"] = summary[:2800]
                    found.append(item)
                    count += 1
            print(f"[OK] {source}: {count} مادة رسمية")
        except Exception as exc:
            print(f"[WARN] الصفحة الرسمية {source}: {exc}")
    return found


def response_text(data):
    parts = []
    for output_item in data.get("output", []):
        if output_item.get("type") != "message":
            continue
        for content in output_item.get("content", []):
            if content.get("type") == "output_text":
                parts.append(content.get("text", ""))
    return "\n".join(parts).strip()


def rewrite_with_grok(item):
    token = os.getenv("XAI_API_KEY")
    if not token:
        return item
    source_text = clean(item.get("raw_source_text") or item.get("original_summary") or "")
    original_title = clean(item.get("original_title") or item.get("title") or "")
    if not source_text:
        return item
    prompt = f"""
أنت محرر أخبار محترف لمنصة نشهل.
أعد بناء المادة الرسمية التالية في صياغة خبر عربية مستقلة، دقيقة ومحايدة، بأسلوب مهني مشابه لوكالات الأنباء والمنصات الإخبارية الكبرى.

قواعد إلزامية:
- استخدم المعلومات الواردة فقط.
- ممنوع اختراع أي حقيقة أو رقم أو اسم أو مكان أو سبب أو اقتباس.
- لا تنسخ الجمل الأصلية حرفيًا؛ أعد صياغتها صحفيًا.
- ابدأ بأهم معلومة.
- العنوان مباشر ودقيق وغير مثير.
- إذا كانت المعلومة موقفًا أو إعلانًا رسميًا، انسبها للجهة بدل تقديمها كحقيقة مطلقة.
- لا تستخدم لغة دعائية أو حزبية أو عاطفية.

عنوان المادة:
{original_title}

نص المادة الرسمية:
{source_text}

أعد JSON فقط:
{{"title":"...","summary":"..."}}
""".strip()
    try:
        response = requests.post(
            "https://api.x.ai/v1/responses",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "model": "grok-4.5",
                "input": [{"role": "user", "content": prompt}],
                "include": ["no_inline_citations"],
            },
            timeout=REWRITE_TIMEOUT,
        )
        response.raise_for_status()
        text = response_text(response.json())
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return item
        rewritten = json.loads(match.group(0))
        new_title = clean(rewritten.get("title"))
        new_summary = clean(rewritten.get("summary"))
        if not new_title or not new_summary or not relevant(new_title, new_summary):
            return item
        item["title"] = new_title[:300]
        item["summary"] = new_summary[:900]
        item["description"] = new_summary[:300]
        item["content"] = new_summary[:900]
        item["rewrite_status"] = "editorial_rewrite"
        item["editorial_note"] = "أعيد تحرير المادة الرسمية بصياغة صحفية مستقلة دون إضافة معلومات جديدة."
    except Exception as exc:
        print(f"[WARN] تعذر التحرير: {exc}")
    return item


def editorial_process(items):
    processed = []
    for index, item in enumerate(items, start=1):
        item = rewrite_with_grok(item)
        item.pop("raw_source_text", None)
        processed.append(item)
        if index % 5 == 0:
            print(f"[OK] تمت معالجة الصياغة: {index}/{len(items)}")
    return processed


def dedupe(items):
    by_id = {}
    for item in items:
        if item and item.get("id") and not blocked(item.get("source"), item.get("source_url")):
            by_id[item["id"]] = item
    return sorted(by_id.values(), key=lambda x: x.get("published_at", ""), reverse=True)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    # لا نحتفظ بأي خبر سابق من القنوات أو المصادر الإعلامية القديمة.
    # يبدأ السجل الحالي من المصادر الرسمية فقط.
    old = []
    try:
        with open(OUT, encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            loaded = loaded.get("news", [])
        if isinstance(loaded, list):
            old = [
                x for x in loaded
                if isinstance(x, dict)
                and x.get("status") == "published"
                and x.get("auto_published", True) is True
                and x.get("source_type", "").startswith("official")
                and not blocked(x.get("source"), x.get("source_url"))
            ]
    except Exception:
        old = []

    fresh = editorial_process(collect_official_rss() + collect_official_pages())
    by_id = {x["id"]: x for x in old if x.get("id")}
    for item in fresh:
        by_id[item["id"]] = item

    final = dedupe(list(by_id.values()))[:MAX_ITEMS]
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print(f"[DONE] {len(final)} خبرًا رسميًا؛ {len(fresh)} مادة جديدة")


if __name__ == "__main__":
    main()
