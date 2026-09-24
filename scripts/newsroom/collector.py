#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent 1: discover real-world events and collect source evidence."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from .common import (
    MAX_CANDIDATES,
    clean,
    canonical_url,
    citations_from,
    extract_json,
    make_event_key,
    xai_responses,
)

SYSTEM_SCOPE = """
أنت روبوت الجمع في غرفة أخبار نشهل.
لا تكتب الخبر النهائي ولا تستنتج موقفًا سياسيًا.
مهمتك اكتشاف الأحداث التي تستحق المتابعة وجمع أدلتها الأولية.
نطاق الأولوية: جنوب اليمن، عدن، حضرموت، شبوة، أبين، لحج، الضالع، المهرة، سقطرى،
ثم اليمن عمومًا والخليج والشرق الأوسط عندما يكون الحدث ذا صلة مباشرة باليمن أو الجنوب.
الأحداث الدولية لا تُلتقط إلا إذا كان لها أثر أو صلة واضحة بالمشهد الذي تتابعه نشهل.
"""



def discover() -> list[dict]:
    now = datetime.now(timezone.utc)
    from_date = (now - timedelta(hours=24)).date().isoformat()
    to_date = now.date().isoformat()

    prompt = f"""{SYSTEM_SCOPE}

خلال آخر 24 ساعة ابحث عبر الويب وX عن أحداث فعلية، وليس مجرد إعادة نشر عناوين.
ابدأ بالمصادر الأولية أو الأقرب للحدث: بيانات رسمية، وثائق، تصريحات مباشرة،
جهات حكومية، منظمات، شركات، أو حسابات موثقة عند الضرورة.
اجمع لكل حدث مادة أولية واضحة، ومعها مصدر مستقل واحد على الأقل عندما يكون الحدث
سياسيًا أو أمنيًا أو عسكريًا أو حساسًا.

أعد JSON فقط كقائمة لا تتجاوز {MAX_CANDIDATES} عناصر:
[
  {{
    "event_key": "معرف مؤقت للحدث",
    "source_title": "عنوان المادة المصدرية كما وجدته",
    "event_summary": "ماذا حدث بحسب المادة المتاحة، دون تحليل",
    "primary_source": {{"name":"اسم الجهة","url":"رابط مباشر"}},
    "additional_sources": [
      {{"name":"اسم المصدر","url":"رابط مباشر","type":"independent أو contextual"}}
    ],
    "published": "ISO-8601 إن توفر",
    "location": "المكان إن كان ثابتًا",
    "category": "اليمن أو الخليج أو الشرق الأوسط أو العالم",
    "region": "الجنوب أو عدن أو حضرموت أو شبوة أو أبين أو لحج أو الضالع أو المهرة أو سقطرى أو اليمن أو الخليج أو دولي"
  }}
]

قواعد صارمة:
- لا تخترع أي رابط أو اسم أو تاريخ.
- لا تعتبر منشورًا واحدًا على X أو Facebook دليلًا كافيًا لخبر مؤكد.
- لا تجمع الحدث نفسه عدة مرات.
- لا تضع رأيًا أو لغة دعائية.
- إذا كانت المادة مجرد ادعاء غير مدعوم، يمكن جمعها فقط مع وسمها كمرشح يحتاج تحققًا.
"""
    text, citations = xai_responses(
        prompt=prompt,
        tools=[{"type": "web_search"}, {"type": "x_search"}],
        from_date=from_date,
        to_date=to_date,
    )
    raw = extract_json(text, "array")
    if not isinstance(raw, list):
        return []

    out: list[dict] = []
    seen: set[str] = set()

    for item in raw[:MAX_CANDIDATES]:
        if not isinstance(item, dict):
            continue
        title = clean(item.get("source_title"))
        summary = clean(item.get("event_summary"))
        primary = item.get("primary_source") if isinstance(item.get("primary_source"), dict) else {}
        p_name = clean(primary.get("name"))
        p_url = canonical_url(primary.get("url"))
        if not title or not summary or not p_url:
            continue
        if citations and p_url not in citations:
            continue

        event_key = clean(item.get("event_key")) or make_event_key(title, summary)
        if event_key in seen:
            continue

        sources: list[dict] = [{"name": p_name or "مصدر أولي", "url": p_url, "type": "primary"}]
        for src in item.get("additional_sources", []) if isinstance(item.get("additional_sources"), list) else []:
            if not isinstance(src, dict):
                continue
            url = canonical_url(src.get("url"))
            name = clean(src.get("name"))
            typ = clean(src.get("type")).lower()
            if not url or not name or url in {x["url"] for x in sources}:
                continue
            if citations and url not in citations:
                continue
            if typ not in {"independent", "contextual"}:
                typ = "contextual"
            sources.append({"name": name[:180], "url": url, "type": typ})

        seen.add(event_key)
        out.append({
            "event_key": event_key,
            "id": event_key,
            "source_title": title[:300],
            "event_summary": summary[:1600],
            "primary_source": sources[0],
            "collected_sources": sources[:8],
            "published": clean(item.get("published")) or now.isoformat(),
            "location": clean(item.get("location"))[:240],
            "category": clean(item.get("category")) or "اليمن",
            "region": clean(item.get("region")) or "اليمن",
            "pipeline_stage": "collected",
        })

    print(f"[COLLECTOR] collected={len(out)}")
    return out
