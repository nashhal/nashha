#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent 3: independently verify claims and source strength."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from .common import MAX_CANDIDATES, MAX_EVIDENCE, canonical_url, clean, citations_from, extract_json, xai_responses


def verify(drafts: list[dict]) -> list[dict]:
    if not drafts:
        return []

    now = datetime.now(timezone.utc)
    from_date = (now - timedelta(hours=72)).date().isoformat()
    to_date = now.date().isoformat()

    payload = json.dumps(drafts[:MAX_CANDIDATES], ensure_ascii=False, indent=2)
    prompt = f"""أنت روبوت التأكيد والتحقق في غرفة أخبار نشهل.

لكل مرشح، قم بالتحقق المستقل عبر الويب وX.
ابحث عن:
1) المصدر الأولي أو الأقرب للحدث.
2) مصدر مستقل مناسب، خصوصًا للادعاءات السياسية أو الأمنية أو العسكرية.
3) التوافق بين التوقيت والمكان والأطراف والتفاصيل الأساسية.
4) أي تناقض أو نقص جوهري.

أعد JSON فقط:
[
  {{
    "event_key":"نفس event_key",
    "verification":"confirmed أو developing أو unconfirmed",
    "verification_score":0,
    "verification_basis":"سبب القرار باختصار",
    "verified_facts_ar":["الوقائع التي دعمها البحث"],
    "unsupported_claims_ar":["الادعاءات التي لم يمكن دعمها"],
    "primary_evidence":{{"name":"اسم المصدر","url":"الرابط المباشر"}},
    "evidence":[
      {{"name":"المصدر","url":"الرابط المباشر","type":"primary أو independent أو contextual","role":"ما الذي يثبته"}}
    ]
  }}
]

معايير إلزامية:
- confirmed فقط عند وجود مصدر أولي واضح + مصدر مستقل مناسب، ودرجة 80-100.
- developing عند وجود حدث حقيقي لكن بعض التفاصيل لم تحسم، و55-79.
- unconfirmed عند عدم كفاية الأدلة، و0-54.
- لا تمنح confirmed لمجرد تكرار عدة وسائل إعلام لنفس المصدر.
- منشور واحد على منصة اجتماعية لا يكفي لتأكيد خبر حساس.
- لا تخترع روابط أو أدلة.
- إذا كانت الأدلة متضاربة، صرّح بالتضارب وخفّض الحالة.

المرشحون:
{payload}
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

    draft_map = {str(x.get("event_key")): x for x in drafts}
    results = []
    for item in raw[:MAX_CANDIDATES]:
        if not isinstance(item, dict):
            continue
        key = clean(item.get("event_key"))
        if key not in draft_map:
            continue

        evidence: list[dict] = []
        seen = set()
        for ev in item.get("evidence", []) if isinstance(item.get("evidence"), list) else []:
            if not isinstance(ev, dict):
                continue
            url = canonical_url(ev.get("url"))
            name = clean(ev.get("name"))
            typ = clean(ev.get("type")).lower()
            role = clean(ev.get("role"))
            if not url or not name or url in seen:
                continue
            if citations and url not in citations:
                continue
            if typ not in {"primary", "independent", "contextual"}:
                typ = "contextual"
            evidence.append({"name": name[:180], "url": url, "type": typ, "role": role[:500]})
            seen.add(url)

        primary = item.get("primary_evidence") if isinstance(item.get("primary_evidence"), dict) else {}
        p_url = canonical_url(primary.get("url"))
        p_name = clean(primary.get("name"))
        if p_url and p_url not in seen and (not citations or p_url in citations):
            evidence.insert(0, {"name": p_name or "المصدر الأولي", "url": p_url, "type": "primary", "role": "المصدر الأولي المرتبط بالحدث"})
            seen.add(p_url)

        try:
            score = max(0, min(100, int(item.get("verification_score", 0))))
        except (TypeError, ValueError):
            score = 0

        primary_count = sum(1 for x in evidence if x["type"] == "primary")
        independent_count = sum(1 for x in evidence if x["type"] == "independent")
        status = clean(item.get("verification")).lower()
        if status == "confirmed" and not (primary_count >= 1 and independent_count >= 1 and score >= 80):
            status, score = "developing", min(score or 70, 79)
        if status not in {"confirmed", "developing", "unconfirmed"}:
            status, score = "unconfirmed", min(score, 54)

        verified_primary = next((x for x in evidence if x["type"] == "primary"), None)
        results.append({
            **draft_map[key],
            "primary_source": verified_primary or draft_map[key].get("primary_source") or {},
            "verification": status,
            "verification_status": status,
            "verification_score": score,
            "verification_basis": clean(item.get("verification_basis"))[:1200],
            "verified_facts": [clean(x)[:600] for x in item.get("verified_facts_ar", []) if clean(x)][:8],
            "unsupported_claims": [clean(x)[:600] for x in item.get("unsupported_claims_ar", []) if clean(x)][:5],
            "verification_evidence": evidence[:MAX_EVIDENCE],
            "verification_evidence_count": len(evidence[:MAX_EVIDENCE]),
            "pipeline_stage": "verified",
        })

    print("[VERIFIER] " + " ".join(f"{x['verification']}={sum(1 for y in results if y['verification']==x['verification'])}" for x in [
        {"verification":"confirmed"},{"verification":"developing"},{"verification":"unconfirmed"}
    ]))
    return results
