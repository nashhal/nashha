#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent 4: final editorial treatment after verification."""
from __future__ import annotations

import json

from .common import MAX_CANDIDATES, clean, clean_body, extract_json, xai_responses


def edit(verified: list[dict]) -> list[dict]:
    if not verified:
        return []

    eligible = [x for x in verified if x.get("verification") in {"confirmed", "developing"}]
    if not eligible:
        return []

    payload = json.dumps(eligible[:MAX_CANDIDATES], ensure_ascii=False, indent=2)
    prompt = f"""أنت روبوت التحرير النهائي في غرفة أخبار نشهل.

استخدم فقط المعلومات الموجودة في البيانات التالية.
أعد صياغة الخبر بصياغة صحفية احترافية بالعربية والإنجليزية، مع فصل الوقائع عن الادعاءات.
لا تضف أي معلومة جديدة.
لا تستخدم لغة دعائية أو تهويلية.
لا تكتب استنتاجات سياسية من عندك.

أعد JSON فقط:
[
  {{
    "event_key":"نفس event_key",
    "title":"Final accurate headline",
    "summary":"2 to 4 sentence summary",
    "content_ar":"Arabic newsroom body text from 4 to 8 short paragraphs",
    "title_en":"English headline",
    "summary_en":"English summary in 2 to 4 sentences",
    "content_en":"English newsroom body text from 4 to 8 short paragraphs",
    "facts_ar":["حتى 8 وقائع مدعومة"],
    "facts_en":["Up to 8 supported facts, translated accurately into English"],
    "claims_ar":["الادعاءات المنسوبة بوضوح إن وجدت"],
    "claims_en":["Attributed claims translated accurately into English when present"],
    "news_angle":"سياسي أو ميداني أو أمني أو دبلوماسي أو اقتصادي أو إنساني أو متابعة",
    "importance":"مرتفع أو متوسط أو عادي",
    "keywords_ar":["حتى 10 كلمات"],
    "verification_basis_en":"Short English explanation of the available verification basis",
    "editorial_note":"ملخص داخلي قصير عن سبب جاهزية المادة"
  }}
]

شروط الجودة:
- إذا كانت الحالة developing فلا تحولها في الصياغة إلى خبر مؤكد؛ يجب أن تعكس اللغة درجة اليقين.
- اكتب النسخة الإنجليزية بأمانة للمعنى دون إضافة معلومات جديدة، واجعل العنوان الإنجليزي طبيعيًا ومهنيًا.
- إذا وجدت ادعاءً غير مدعوم، انسبه بوضوح أو استبعده.
- لا تنقل عنوان المصدر حرفيًا.

المواد:
{payload}
"""
    text, _ = xai_responses(prompt=prompt)
    raw = extract_json(text, "array")
    if not isinstance(raw, list):
        return []

    by_key = {str(x.get("event_key")): x for x in eligible}
    out = []
    for item in raw[:MAX_CANDIDATES]:
        if not isinstance(item, dict):
            continue
        key = clean(item.get("event_key"))
        base = by_key.get(key)
        if not base:
            continue
        title = clean(item.get("title"))
        summary = clean(item.get("summary"))
        body = clean_body(item.get("content_ar"))
        title_en = clean(item.get("title_en"))
        summary_en = clean(item.get("summary_en"))
        body_en = clean_body(item.get("content_en"))
        if not title or not summary or not body:
            continue
        if not title_en or not summary_en or not body_en:
            continue

        angle = clean(item.get("news_angle"))
        if angle not in {"سياسي", "ميداني", "أمني", "دبلوماسي", "اقتصادي", "إنساني", "متابعة"}:
            angle = "متابعة"
        importance = clean(item.get("importance"))
        if importance not in {"مرتفع", "متوسط", "عادي"}:
            importance = "عادي"

        out.append({
            **base,
            "title": title[:320],
            "summary": summary[:1600],
            "title_en": title_en[:320],
            "summary_en": summary_en[:1600],
            "content_ar": body[:6500],
            "content_en": body_en[:6500],
            "facts_ar": [clean(x)[:600] for x in item.get("facts_ar", []) if clean(x)][:8],
            "facts_en": [clean(x)[:600] for x in facts_en if clean(x)][:8],
            "claims_ar": [clean(x)[:600] for x in item.get("claims_ar", []) if clean(x)][:5],
            "claims_en": [clean(x)[:600] for x in claims_en if clean(x)][:5],
            "news_angle": angle,
            "importance": importance,
            "keywords_ar": [clean(x)[:80] for x in item.get("keywords_ar", []) if clean(x)][:10],
            "verification_basis_en": clean(item.get("verification_basis_en"))[:1200],
            "editorial_note": clean(item.get("editorial_note"))[:700],
            "editorial_status": "ready" if base.get("verification") == "confirmed" else "review_required",
            "pipeline_stage": "edited",
        })

    print(f"[EDITOR] ready={sum(1 for x in out if x.get('editorial_status')=='ready')} review={sum(1 for x in out if x.get('editorial_status')!='ready')}")
    return out
