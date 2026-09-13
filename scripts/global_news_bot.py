#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""محرك نشهل لاكتشاف الأخبار العربية والعالمية بالذكاء الاصطناعي.
لا يعتمد على قائمة قنوات ثابتة. يستخدم بحث الويب وX لاكتشاف الأحداث، ثم يتحقق من
وجود روابط فعلية ويعيد صياغة الخبر بالعربية مع تصنيف جغرافي وموضوعي.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import requests

OUT = "data/news.json"
MODEL = os.getenv("XAI_MODEL", "grok-4.5")
MAX_ITEMS = 180
TIMEOUT = 120

CATEGORIES = ["اليمن", "الخليج", "العالم العربي", "العالم", "اقتصاد", "تقنية", "علوم", "رياضة", "ثقافة"]


def clean(value: str | None) -> str:
    value = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", value).strip()


def response_text(data: dict) -> str:
    parts: list[str] = []
    for output in data.get("output", []):
        if output.get("type") != "message":
            continue
        for content in output.get("content", []):
            if content.get("type") == "output_text":
                parts.append(content.get("text", ""))
    return "\n".join(parts).strip()


def normalize_url(url: str) -> str:
    return clean(url).rstrip("/")


def make_id(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode()).hexdigest()[:20]


def load_existing() -> list[dict]:
    try:
        with open(OUT, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = data.get("news", data.get("items", []))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def discover() -> list[dict]:
    token = os.getenv("XAI_API_KEY")
    if not token:
        raise RuntimeError("XAI_API_KEY غير مضبوط")

    now = datetime.now(timezone.utc)
    from_date = (now - timedelta(hours=24)).date().isoformat()
    to_date = now.date().isoformat()

    prompt = """أنت محرك اكتشاف أخبار وغرفة رصد رقمية لمنصة عربية ذات تغطية عالمية اسمها نشهل.
ابحث عن أبرز الأخبار والتطورات الحقيقية خلال آخر 24 ساعة، بالعربية أو من المصادر العالمية مهما كانت لغتها، ثم أعد عرضها بالعربية.

نطاق التغطية:
- اليمن والجنوب اليمني والخليج والشرق الأوسط والعالم العربي.
- الأخبار الدولية ذات الأهمية العالمية.
- السياسة والدبلوماسية والأمن والاقتصاد والأسواق والتقنية والعلوم والصحة والبيئة والثقافة والرياضة.
- لا تجعل اليمن محور كل النتائج؛ نريد منصة عربية وعالمية متوازنة.

منهج الاكتشاف:
- استخدم البحث على الويب كمحرك أساسي، وX كمجال رصد واكتشاف مبكر.
- لا تعتبر منشور X أو حسابًا منفردًا دليلًا كافيًا لخبر مؤكد.
- أعط الأولوية للتطورات التي يمكن التحقق منها من مادة صحفية أو بيان رسمي أو جهة موثوقة.
- ابحث عن أكثر من تغطية عندما يكون الخبر كبيرًا أو حساسًا.
- لا تكرر الحدث نفسه بصيغ مختلفة.
- استبعد المحتوى الدعائي والإعلانات والشائعات والآراء الفردية.

أعد JSON فقط بالشكل:
[
  {
    "title":"عنوان عربي مهني",
    "summary":"ملخص دقيق من 3 إلى 5 جمل يذكر الوقائع الأساسية دون تهويل",
    "source_name":"اسم أفضل مصدر متاح",
    "source_url":"رابط مباشر للمادة",
    "published":"ISO-8601 إن توفر وإلا فارغ",
    "category":"اليمن أو الخليج أو العالم العربي أو العالم أو اقتصاد أو تقنية أو علوم أو رياضة أو ثقافة",
    "region":"اليمن أو الخليج أو الشرق الأوسط أو العالم العربي أو أوروبا أو أميركا أو آسيا أو أفريقيا أو دولي",
    "verification":"confirmed أو developing أو unconfirmed"
  }
]

قواعد مهمة:
- بحد أقصى 25 خبرًا.
- كل خبر يجب أن يملك source_url صالحًا ظهر في نتائج البحث أو الاستشهادات.
- لا تخترع رابطًا أو اسم مصدر.
- في الخبر الحساس استخدم confirmed فقط عند وجود أساس موثوق؛ developing للحدث الجاري الذي تتغير تفاصيله؛ unconfirmed لا يُنشر في الواجهة الرئيسية.
- اكتب العربية الفصحى الصحفية، لا ترجمة حرفية ركيكة.
- لا تنسب موقفًا أو نيةً أو سببًا لم يثبت في المادة.
"""

    r = requests.post(
        "https://api.x.ai/v1/responses",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "input": [{"role": "user", "content": prompt}],
            "tools": [
                {"type": "web_search"},
                {"type": "x_search", "from_date": from_date, "to_date": to_date},
            ],
            "include": ["no_inline_citations"],
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    text = response_text(data)
    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        return []
    raw = json.loads(match.group(0))
    if not isinstance(raw, list):
        return []

    citations = {normalize_url(x) for x in data.get("citations", []) if isinstance(x, str) and x.startswith(("http://", "https://"))}
    results: list[dict] = []
    seen_urls: set[str] = set()

    for item in raw:
        if not isinstance(item, dict):
            continue
        title = clean(item.get("title"))
        summary = clean(item.get("summary"))
        source_name = clean(item.get("source_name"))
        source_url = clean(item.get("source_url"))
        verification = clean(item.get("verification")) or "developing"
        category = clean(item.get("category"))
        region = clean(item.get("region"))
        if not title or not summary or not source_name or not source_url.startswith(("http://", "https://")):
            continue
        normalized = normalize_url(source_url)
        if citations and normalized not in citations:
            continue
        if normalized in seen_urls:
            continue
        seen_urls.add(normalized)
        if category not in CATEGORIES:
            category = "العالم"
        if verification not in {"confirmed", "developing", "unconfirmed"}:
            verification = "developing"
        results.append({
            "id": make_id(source_url),
            "title": title[:300],
            "original_title": title[:300],
            "summary": summary[:1400],
            "description": summary[:500],
            "content": summary[:1400],
            "source": source_name,
            "source_name": source_name,
            "source_url": source_url,
            "link": source_url,
            "published": clean(item.get("published")) or datetime.now(timezone.utc).isoformat(),
            "published_at": clean(item.get("published")) or datetime.now(timezone.utc).isoformat(),
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "region": region or "دولي",
            "status": "review" if verification == "unconfirmed" else "published",
            "confidence": "high" if verification == "confirmed" else "medium",
            "verification": verification,
            "platform": "news",
            "source_type": "ai_discovery",
            "auto_published": verification != "unconfirmed",
            "rewrite_status": "ai_discovery",
        })
    return results


def main() -> None:
    existing = load_existing()
    try:
        fresh = discover()
        print(f"[OK] AI discovery: {len(fresh)} stories")
    except Exception as exc:
        print(f"[WARN] AI discovery failed: {exc}")
        if existing:
            return
        return

    if not fresh and existing:
        return

    merged: dict[str, dict] = {}
    for item in existing + fresh:
        if isinstance(item, dict) and item.get("id"):
            merged[str(item["id"])] = item

    ordered = sorted(merged.values(), key=lambda x: x.get("published_at") or x.get("published") or "", reverse=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(ordered[:MAX_ITEMS], f, ensure_ascii=False, indent=2)
    print(f"[DONE] {min(len(ordered), MAX_ITEMS)} total stories")


if __name__ == "__main__":
    main()
