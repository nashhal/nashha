#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""نشهل - جمع الأخبار من مصادرها الأصلية وإعادة صياغتها بصياغة صحفية مهنية."""
import hashlib
import html
import json
import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests

OUT = "data/news.json"
MAX_ITEMS = 120
REQUEST_TIMEOUT = 25
REWRITE_TIMEOUT = 90

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
HEADERS = {"User-Agent": "NahshalNews/3.0 (+https://nashhal.github.io/nashha/)"}


def clean(value):
    value = html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    return re.sub(r"\s+", " ", value).strip()


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
        "confidence": "high",
        "auto_published": True,
        "summary": summary[:900],
        "original_summary": summary[:1800],
        "description": summary[:300],
        "content": summary[:900],
        "platform": "news",
        "source_type": source_type,
        "rewrite_status": "source_text",
    }


def collect_rss():
    found = []
    for source, url, source_type in TRUSTED_FEEDS:
        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            source_count = 0
            for entry in feed.entries[:50]:
                item = make_item(
                    source,
                    source_type,
                    entry.get("title"),
                    entry.get("link"),
                    entry.get("summary") or entry.get("description"),
                    entry.get("published") or entry.get("updated"),
                )
                if item:
                    item["raw_source_text"] = clean(
                        entry.get("summary") or entry.get("description") or entry.get("title")
                    )[:2200]
                    found.append(item)
                    source_count += 1
            print(f"[OK] {source}: {source_count} خبرًا صالحًا")
        except Exception as exc:
            print(f"[WARN] RSS {source}: {exc}")
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
أنت محرر أخبار محترف لمنصة نشهل اليمنية.
أعد تحرير الخبر التالي بصياغة صحفية عربية مهنية ومحايدة.
استخدم المعلومات الواردة في المصدر فقط. ممنوع إضافة أي معلومة أو رقم أو اسم أو سياق غير موجود في النص.
لا تغيّر حقيقة الخبر ولا تبالغ في العنوان. لا تستخدم لغة دعائية أو حزبية أو عاطفية. لا تستنتج اتهامات أو دوافع غير مذكورة. لا تخترع اقتباسات.
حافظ على أسماء الأشخاص والجهات والأماكن كما وردت. اجعل العنوان واضحًا ودقيقًا وغير مثير للنقر.
اكتب ملخصًا من جملتين إلى ثلاث جمل يشرح أهم ما ورد في المصدر.

عنوان المصدر:
{original_title}

نص المصدر:
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
        item["editorial_note"] = "أعيدت الصياغة اعتمادًا على نص المصدر الأصلي دون إضافة معلومات جديدة."
    except Exception as exc:
        print(f"[WARN] تعذر إعادة صياغة خبر من {item.get('source')}: {exc}")
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

    existing = {
        x.get("id"): x
        for x in old
        if isinstance(x, dict)
        and x.get("id")
        and x.get("status") == "published"
        and x.get("auto_published", True) is True
        and x.get("source_type") != "social_public"
    }

    # النشر الآلي يعتمد على خلاصات الأخبار من المصادر الأصلية فقط.
    fresh = editorial_process(collect_rss())
    for item in fresh:
        existing[item["id"]] = item

    final = dedupe(list(existing.values()))[:MAX_ITEMS]
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print(f"[DONE] {len(final)} خبر منشور؛ {len(fresh)} خبر جديد من المصادر الأصلية")


if __name__ == "__main__":
    main()
