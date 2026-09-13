#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""محرك نشهل لاكتشاف الأحداث وبناء أخبار أصلية مدعومة بالأدلة.

المبدأ التحريري:
حدث -> أدلة أولية -> مقارنة مستقلة -> تقييم تحقق -> خبر نشهل
المصادر تحفظ داخل البيانات كسجل تحقق ولا تظهر في واجهة الخبر كهوية للنشر.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse

import requests

OUT = "data/news.json"
MODEL = os.getenv("XAI_MODEL", "grok-4.5")
MAX_ITEMS = 180
MAX_FRESH = 25
TIMEOUT = 120

CATEGORIES = ["اليمن", "الخليج", "العالم العربي", "العالم", "اقتصاد", "تقنية", "علوم", "رياضة", "ثقافة"]
REGIONS = ["اليمن", "الخليج", "الشرق الأوسط", "العالم العربي", "أوروبا", "أميركا", "آسيا", "أفريقيا", "دولي"]
VERIFICATIONS = {"confirmed", "developing", "unconfirmed"}


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


def canonical_url(url: str) -> str:
    try:
        p = urlparse(clean(url))
        if p.scheme not in {"http", "https"} or not p.netloc:
            return ""
        return urlunparse((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), "", "", ""))
    except Exception:
        return ""


def make_id(seed: str) -> str:
    return hashlib.sha256(clean(seed).encode("utf-8")).hexdigest()[:20]


def make_event_key(title: str, summary: str) -> str:
    text = re.sub(r"[^\w\u0600-\u06FF ]+", " ", f"{title} {summary}".lower())
    tokens = [x for x in text.split() if len(x) > 2][:36]
    return hashlib.sha256(" ".join(tokens).encode("utf-8")).hexdigest()[:16]


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

    prompt = f"""أنت غرفة رصد رقمية مستقلة لمنصة نشهل.
مهمتك ليست جمع روابط أو تلخيص ما نشرته القنوات، بل اكتشاف الأحداث نفسها وبناء ملف تحقق لكل حدث خلال آخر 24 ساعة.

نطاق التغطية:
- اليمن والجنوب اليمني والخليج والشرق الأوسط والعالم العربي.
- الأخبار الدولية المهمة.
- السياسة والدبلوماسية والأمن والاقتصاد والأسواق والتقنية والعلوم والصحة والبيئة والثقافة والرياضة.

منهج العمل الإلزامي لكل حدث:
1) اكتشف الحدث نفسه، لا اسم القناة التي غطته.
2) ابحث أولًا عن المصدر الأولي أو الأقرب للحدث: بيان رسمي، وثيقة، جهة حكومية، تصريح مباشر، ملف رسمي، بيانات شركة أو منظمة، أو شاهد/حساب موثق عند الحاجة.
3) اجمع مادة مستقلة ثانية أو أكثر عندما يكون الحدث حساسًا أو مهمًا.
4) قارن الروايات واكشف أي تناقض أو نقص.
5) افصل بين "ما ثبت" و"ما ادعاه طرف" و"ما يزال قيد التحقق".
6) لا تجعل منشورًا واحدًا على X أو Facebook دليلًا كافيًا لخبر مؤكد.
7) لا تكرر الحدث نفسه لمجرد أن أكثر من مؤسسة غطته.
8) لا تنشر الإشاعة على أنها خبر.

أعد JSON فقط بالشكل التالي:
[
  {{
    "event_key":"معرف ثابت للحدث",
    "title":"عنوان عربي مهني أصلي لا يبدأ باسم مصدر",
    "summary":"ملخص دقيق من 3 إلى 5 جمل يصف الحدث نفسه",
    "facts_ar":["3 إلى 8 وقائع يمكن إسنادها إلى الأدلة"],
    "claims_ar":["حتى 5 ادعاءات منسوبة بوضوح إلى أصحابها إن وجدت"],
    "verification_basis":"شرح قصير لماذا اعتبر الحدث مؤكدًا أو جاريًا أو غير مؤكد",
    "verification_score":0,
    "verification":"confirmed أو developing أو unconfirmed",
    "primary_evidence":{{"name":"اسم الجهة أو المادة الأولية","url":"رابط مباشر"}},
    "evidence":[
      {{"name":"اسم الجهة أو المادة","url":"رابط مباشر","type":"primary أو independent أو contextual","role":"ماذا تثبت هذه المادة"}}
    ],
    "published":"ISO-8601 إن توفر وإلا فارغ",
    "category":"اليمن أو الخليج أو العالم العربي أو العالم أو اقتصاد أو تقنية أو علوم أو رياضة أو ثقافة",
    "region":"اليمن أو الخليج أو الشرق الأوسط أو العالم العربي أو أوروبا أو أميركا أو آسيا أو أفريقيا أو دولي"
  }}
]

قواعد حاسمة:
- بحد أقصى {MAX_FRESH} حدثًا.
- كل رابط يجب أن يكون رابطًا مباشرًا حقيقيًا ظهر في البحث أو الاستشهادات.
- لا تخترع أسماء أو روابط أو أرقامًا أو تواريخ.
- confirmed: يلزم أساس أولي واضح ومعه دعم مستقل مناسب للحدث، وتكون درجة التحقق 80-100.
- developing: حدث حقيقي جاري أو معلوماته الأساسية مثبتة لكن بعض التفاصيل لم تُحسم، ودرجة 55-79.
- unconfirmed: لا تكفي الأدلة، ودرجة 0-54. هذه العناصر لا تُنشر في الصفحة الرئيسية.
- في الأخبار الحساسة: لا تستخدم لغة قطعية عندما تكون الأدلة طرفية أو متضاربة.
- صياغة العنوان والملخص يجب أن تكون تحريرًا أصليًا من نشهل، لا إعادة إنتاج للعنوان الأصلي للمصدر.
- لا تجعل "source_name" أو أسماء المؤسسات جزءًا من عنوان الخبر أو مقدمته إلا عندما تكون جزءًا من الواقعة نفسها.
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

    citations = {canonical_url(x) for x in data.get("citations", []) if isinstance(x, str)}
    results: list[dict] = []
    seen_events: set[str] = set()

    for item in raw[:MAX_FRESH]:
        if not isinstance(item, dict):
            continue
        title = clean(item.get("title"))
        summary = clean(item.get("summary"))
        verification = clean(item.get("verification")).lower() or "developing"
        category = clean(item.get("category"))
        region = clean(item.get("region"))
        event_key = clean(item.get("event_key")) or make_event_key(title, summary)
        primary = item.get("primary_evidence") if isinstance(item.get("primary_evidence"), dict) else {}
        primary_name = clean(primary.get("name"))
        primary_url = canonical_url(primary.get("url", ""))
        raw_evidence = item.get("evidence") if isinstance(item.get("evidence"), list) else []

        evidence: list[dict] = []
        seen_urls: set[str] = set()
        for ev in raw_evidence:
            if not isinstance(ev, dict):
                continue
            ev_name = clean(ev.get("name"))
            ev_url = canonical_url(ev.get("url", ""))
            ev_type = clean(ev.get("type")) or "contextual"
            ev_role = clean(ev.get("role"))
            if not ev_name or not ev_url or ev_url in seen_urls:
                continue
            if citations and ev_url not in citations:
                continue
            if ev_type not in {"primary", "independent", "contextual"}:
                ev_type = "contextual"
            evidence.append({"name": ev_name[:180], "url": ev_url, "type": ev_type, "role": ev_role[:500]})
            seen_urls.add(ev_url)

        if primary_url and primary_url not in seen_urls and (not citations or primary_url in citations):
            evidence.insert(0, {"name": primary_name or "المادة الأولية", "url": primary_url, "type": "primary", "role": "المادة الأولية المرتبطة بالحدث"})
            seen_urls.add(primary_url)

        if not title or not summary or not evidence:
            continue
        if event_key in seen_events:
            continue
        seen_events.add(event_key)

        try:
            score = max(0, min(100, int(item.get("verification_score", 0))))
        except (TypeError, ValueError):
            score = 0

        independent_count = sum(1 for e in evidence if e.get("type") == "independent")
        has_primary = any(e.get("type") == "primary" for e in evidence)
        if verification == "confirmed" and not (has_primary and independent_count >= 1):
            verification = "developing"
            score = min(score or 70, 79)
        if verification not in VERIFICATIONS:
            verification = "developing"

        published = clean(item.get("published")) or datetime.now(timezone.utc).isoformat()
        results.append({
            "id": make_id(event_key),
            "event_key": event_key,
            "title": title[:300],
            "original_title": title[:300],
            "summary": summary[:1400],
            "description": summary[:500],
            "content": "\n\n".join(clean(x) for x in item.get("facts_ar", []) if clean(x))[:2600],
            "facts_ar": [clean(x)[:600] for x in item.get("facts_ar", []) if clean(x)][:8],
            "claims_ar": [clean(x)[:600] for x in item.get("claims_ar", []) if clean(x)][:5],
            "verification_basis": clean(item.get("verification_basis"))[:1200],
            "verification_score": score,
            "verification": verification,
            "verification_status": verification,
            "verification_evidence_count": len(evidence),
            "verification_evidence": evidence,
            "primary_evidence": evidence[0] if evidence else {},
            "source": primary_name or (evidence[0].get("name") if evidence else ""),
            "source_name": primary_name or (evidence[0].get("name") if evidence else ""),
            "source_url": primary_url or (evidence[0].get("url") if evidence else ""),
            "published": published,
            "published_at": published,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "category": category if category in CATEGORIES else "العالم",
            "region": region if region in REGIONS else "دولي",
            "status": "review" if verification == "unconfirmed" else "published",
            "confidence": "high" if verification == "confirmed" else ("medium" if verification == "developing" else "low"),
            "auto_published": verification != "unconfirmed",
            "source_type": "event_discovery",
            "rewrite_status": "original_editorial",
            "editorial_model": MODEL,
            "editorial_version": "3.0-event-first",
        })
    return results


def merge_events(existing: list[dict], fresh: list[dict]) -> list[dict]:
    """ادمج الأحداث مع اعتبار الاكتشاف الأحدث هو السجل التحريري الأساسي.

    نحتفظ بالتحليل السابق والحقول الإضافية الموجودة فقط عندما لا توفر النسخة
    الجديدة قيمة لها، بينما يتم تحديث العنوان والملخص والوقائع والتحقق والأدلة
    من الاكتشاف الجديد. هذا يمنع بقاء تحرير قديم يطغى على الخبر المعاد اكتشافه.
    """
    merged: dict[str, dict] = {}

    preserved_analysis = (
        "analysis_ar", "background_ar", "what_happened_ar", "why_it_matters_ar",
        "implications_ar", "open_questions_ar", "analysis_level", "news_angle",
        "importance", "entities_ar", "keywords_ar", "analysis_engine", "analysis_version",
    )

    for item in existing:
        if not isinstance(item, dict):
            continue
        key = str(item.get("event_key") or item.get("id") or "").strip()
        if key:
            merged[key] = dict(item)

    for fresh_item in fresh:
        if not isinstance(fresh_item, dict):
            continue
        key = str(fresh_item.get("event_key") or fresh_item.get("id") or "").strip()
        if not key:
            continue

        old = merged.get(key, {})
        combined = dict(fresh_item)

        # الاحتفاظ بالتحليل القديم فقط عند عدم وجود تحليل أحدث في البيانات الجديدة.
        for field in preserved_analysis:
            if not clean(combined.get(field)) and old.get(field):
                combined[field] = old[field]

        # الاحتفاظ بأي حقول داخلية مضافة سابقًا ما لم يقدم الاكتشاف الجديد بديلًا.
        for field, value in old.items():
            if field not in combined and value not in (None, "", [], {}):
                combined[field] = value

        old_evidence = old.get("verification_evidence") if isinstance(old.get("verification_evidence"), list) else []
        new_evidence = combined.get("verification_evidence") if isinstance(combined.get("verification_evidence"), list) else []
        evidence = []
        seen_urls = set()
        for ev in new_evidence + old_evidence:
            if not isinstance(ev, dict):
                continue
            ev_url = canonical_url(ev.get("url", ""))
            if not ev_url or ev_url in seen_urls:
                continue
            evidence.append(ev)
            seen_urls.add(ev_url)
        combined["verification_evidence"] = evidence[:12]
        combined["verification_evidence_count"] = len(combined["verification_evidence"])

        # لا نسمح بمرور حالة أقل جودة بسبب سجل قديم أقوى أو أضعف؛ نعتمد نتيجة الاكتشاف الحالي.
        verification = clean(combined.get("verification")).lower() or "developing"
        if verification not in VERIFICATIONS:
            verification = "developing"
        combined["verification"] = verification
        combined["verification_status"] = verification
        try:
            score = max(0, min(100, int(combined.get("verification_score", 0))))
        except (TypeError, ValueError):
            score = 0
        combined["verification_score"] = score
        if verification == "confirmed":
            combined["confidence"] = "high"
            combined["status"] = "published"
            combined["auto_published"] = True
        elif verification == "developing":
            combined["confidence"] = "medium"
            combined["status"] = "published"
            combined["auto_published"] = True
        else:
            combined["confidence"] = "low"
            combined["status"] = "review"
            combined["auto_published"] = False

        merged[key] = combined

    return list(merged.values())


def main() -> None:
    existing = load_existing()
    try:
        fresh = discover()
        print(f"[OK] Event discovery: {len(fresh)} events")
    except Exception as exc:
        print(f"[WARN] Event discovery failed: {exc}")
        return

    if not fresh and existing:
        print("[OK] No fresh events; keeping existing dataset.")
        return

    ordered = sorted(
        merge_events(existing, fresh),
        key=lambda x: x.get("published_at") or x.get("published") or "",
        reverse=True,
    )
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(ordered[:MAX_ITEMS], f, ensure_ascii=False, indent=2)
    print(f"[DONE] {min(len(ordered), MAX_ITEMS)} total event stories")


if __name__ == "__main__":
    main()
