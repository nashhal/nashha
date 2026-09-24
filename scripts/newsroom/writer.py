#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent 2: turn collected material into an original draft without adding facts."""
from __future__ import annotations

import json

from .common import MAX_CANDIDATES, clean, extract_json, xai_responses


def write(candidates: list[dict]) -> list[dict]:
    if not candidates:
        return []

    source = json.dumps(candidates[:MAX_CANDIDATES], ensure_ascii=False, indent=2)
    prompt = f"""أنت روبوت الكتابة الأولية في غرفة أخبار نشهل.

حوّل المواد المجمعة أدناه إلى مسودات أصلية باللغة العربية الفصحى.
لا تبحث عن معلومات جديدة ولا تضف أي حقيقة غير موجودة في المادة المجمعة.
لا تنسب رأيًا إلى جهة لم تذكره المادة.
اكتب عن الحدث نفسه لا عن القناة التي نشرته.

أعد JSON فقط:
[
  {{
    "event_key":"نفس event_key",
    "headline":"عنوان مهني واضح دون تهويل",
    "summary":"2 إلى 4 جمل تلخص الوقائع المتاحة",
    "facts_ar":["3 إلى 6 وقائع مثبتة من المادة"],
    "claims_ar":["الادعاءات المنسوبة لأصحابها إن وجدت"],
    "category":"التصنيف",
    "region":"المنطقة",
    "location":"المكان إن كان ثابتًا",
    "writing_notes":"ملاحظات للمدقق، لا تظهر للقارئ"
  }}
]

ممنوع:
- اختلاق أرقام أو أسماء أو تواريخ.
- استخدام لغة تحريضية أو دعائية.
- تحويل الاحتمالات إلى حقائق.
- نسخ عنوان المصدر حرفيًا.

المواد:
{source}
"""
    text, _ = xai_responses(prompt=prompt)
    raw = extract_json(text, "array")
    if not isinstance(raw, list):
        return []

    by_key = {str(x.get("event_key")): x for x in candidates}
    out = []
    for item in raw[:MAX_CANDIDATES]:
        if not isinstance(item, dict):
            continue
        key = clean(item.get("event_key"))
        if not key or key not in by_key:
            continue
        headline = clean(item.get("headline"))
        summary = clean(item.get("summary"))
        if not headline or not summary:
            continue
        out.append({
            **by_key[key],
            "headline": headline[:300],
            "draft_summary": summary[:1600],
            "draft_facts": [clean(x)[:600] for x in item.get("facts_ar", []) if clean(x)][:6],
            "draft_claims": [clean(x)[:600] for x in item.get("claims_ar", []) if clean(x)][:5],
            "writing_notes": clean(item.get("writing_notes"))[:900],
            "pipeline_stage": "written",
        })
    print(f"[WRITER] drafts={len(out)}")
    return out
