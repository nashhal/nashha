#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""نشهل: بوت اكتشاف أخبار بالذكاء الاصطناعي.
لا يعتمد على قائمة قنوات ثابتة. يستخدم البحث اللحظي في الويب وX لاكتشاف الأحداث،
ثم يفرزها ويتحقق من الأدلة ويعيد تحريرها بالعربية بصياغة نشهل.
"""

import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import requests

OUT = "data/news.json"
MAX_ITEMS = 120
AI_TIMEOUT = 180
HEADERS = {"User-Agent": "NashhalAI-NewsBot/1.0 (+https://nashhal.github.io/nashha/)"}

EXCLUDED_TERMS = [
    "كرة القدم", "كأس العالم", "الدوري", "دوري أبطال", "المباراة", "مباراة",
    "منتخب", "لاعب", "لاعبة", "مدرب", "رياضة", "رياضي", "رياضية", "فيفا",
    "football", "soccer", "fifa", "match", "champions league", "premier league",
    "موسيقى", "أغنية", "فنان", "فنانة", "ممثل", "ممثلة", "مشاهير", "سينما",
    "مسلسل", "فيلم", "ترفيه", "حفلة", "حفل غنائي", "تيك توك", "إنستغرام", "مؤثر",
]

REGION_TERMS = [
    "اليمن", "اليمني", "اليمنية", "الجنوب", "الجنوبي", "القضية الجنوبية",
    "عدن", "حضرموت", "شبوة", "أبين", "لحج", "الضالع", "المهرة", "سقطرى",
    "تعز", "مأرب", "صنعاء", "الحديدة", "حجة", "صعدة", "الجوف", "ذمار",
    "إب", "ريمة", "البيضاء", "باب المندب", "البحر الأحمر", "خليج عدن",
]


def clean(value):
    value = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", value).strip()


def domain(url):
    try:
        return urlparse(str(url)).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def is_yemen_related(text):
    haystack = clean(text).lower()
    if any(term.lower() in haystack for term in EXCLUDED_TERMS):
        return False
    return any(term.lower() in haystack for term in REGION_TERMS)


def parse_json_array(text):
    text = clean(text)
    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        raise ValueError("لم يعثر البوت على مصفوفة JSON")
    data = json.loads(match.group(0))
    if not isinstance(data, list):
        raise ValueError("النتيجة ليست قائمة")
    return data


def response_text(data):
    parts = []
    for output in data.get("output", []):
        if output.get("type") != "message":
            continue
        for content in output.get("content", []):
            if content.get("type") == "output_text":
                parts.append(content.get("text", ""))
    return "\n".join(parts).strip()


def citations_from_response(data):
    urls = set()
    for value in data.get("citations", []) or []:
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            urls.add(value.rstrip("/"))
    for output in data.get("output", []):
        for content in output.get("content", []) if isinstance(output, dict) else []:
            if not isinstance(content, dict):
                continue
            for key in ("url", "source_url"):
                value = content.get(key)
                if isinstance(value, str) and value.startswith(("http://", "https://")):
                    urls.add(value.rstrip("/"))
    return urls


def load_existing():
    try:
        with open(OUT, encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            data = data.get("news", data.get("items", []))
        return [x for x in data if isinstance(x, dict) and x.get("id")] if isinstance(data, list) else []
    except Exception as exc:
        print(f"[WARN] تعذر قراءة البيانات الحالية: {exc}")
        return []


def item_id(url, title):
    return hashlib.sha256(f"{url}|{title}".encode("utf-8")).hexdigest()[:20]


def normalize_candidate(candidate, valid_citations):
    if not isinstance(candidate, dict):
        return None

    title = clean(candidate.get("title"))
    summary = clean(candidate.get("summary"))
    content = clean(candidate.get("content"))
    source_url = clean(candidate.get("source_url"))
    source_name = clean(candidate.get("source_name"))
    published = clean(candidate.get("published"))
    category = clean(candidate.get("category")) or "اليمن"
    significance = clean(candidate.get("significance")) or "متوسط"
    confidence = clean(candidate.get("confidence")) or "medium"
    evidence_count = int(candidate.get("evidence_count") or 0)
    x_only = bool(candidate.get("x_only", False))
    editorial_angle = clean(candidate.get("editorial_angle"))
    analysis = clean(candidate.get("analysis"))
    implications = clean(candidate.get("implications"))
    entities = candidate.get("entities") if isinstance(candidate.get("entities"), list) else []
    keywords = candidate.get("keywords") if isinstance(candidate.get("keywords"), list) else []

    if not title or not summary or not source_url.startswith(("http://", "https://")):
        return None
    if valid_citations and source_url.rstrip("/") not in valid_citations:
        return None
    if not is_yemen_related(f"{title} {summary}"):
        return None

    # سياسة النشر: منشور X المنفرد ليس خبرًا منشورًا.
    status = "review" if x_only or evidence_count < 1 or confidence == "low" else "published"
    if evidence_count >= 2 and confidence in {"high", "medium"}:
        status = "published"

    return {
        "id": item_id(source_url, title),
        "title": title[:300],
        "original_title": title[:300],
        "source": source_name or domain(source_url) or "مصدر إلكتروني",
        "source_name": source_name or domain(source_url) or "مصدر إلكتروني",
        "source_url": source_url,
        "link": source_url,
        "published": published or datetime.now(timezone.utc).isoformat(),
        "published_at": published or datetime.now(timezone.utc).isoformat(),
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "category": category if category in {"الجنوب", "اليمن"} else ("الجنوب" if category.startswith("جنوب") else "اليمن"),
        "status": status,
        "confidence": confidence if confidence in {"high", "medium", "low"} else "medium",
        "significance": significance if significance in {"مرتفع", "متوسط", "عادي"} else "متوسط",
        "evidence_count": evidence_count,
        "auto_published": status == "published",
        "summary": summary[:900],
        "description": summary[:300],
        "content": content[:1800] if content else summary[:900],
        "title_en": clean(candidate.get("title_en"))[:300],
        "summary_en": clean(candidate.get("summary_en"))[:900],
        "platform": "ai_discovery",
        "source_type": "ai_discovered",
        "rewrite_status": "ai_editorial_analysis",
        "editorial_angle": editorial_angle,
        "analysis": analysis,
        "implications": implications,
        "entities": [clean(x) for x in entities[:12] if clean(x)],
        "keywords": [clean(x) for x in keywords[:12] if clean(x)],
        "x_only": x_only,
    }


def discover_with_ai():
    token = os.getenv("XAI_API_KEY")
    if not token:
        print("[ERROR] XAI_API_KEY غير مضبوط")
        return []

    now = datetime.now(timezone.utc)
    from_date = (now - timedelta(days=1)).date().isoformat()
    to_date = now.date().isoformat()

    prompt = f"""أنت الآن غرفة أخبار مصغرة تعمل لصالح منصة نشهل اليمنية.
مهمتك اكتشاف أحدث الأخبار والتطورات المتعلقة باليمن، مع أولوية للجنوب اليمني، خلال الفترة من {from_date} إلى {to_date}.

لا تعتمد على قائمة قنوات أو وكالات محددة. ابحث بحرية في الويب وX، واسمح لمحرك البحث باكتشاف المصادر المناسبة بنفسه.
أعطِ الأولوية للمصادر الأولية: بيانات حكومية، جهات رسمية، منظمات دولية، تصريحات مباشرة، وثائق، ثم المصادر الصحفية ذات الصلة.
استخدم X للرصد واكتشاف التطورات، لكن لا تنشر ادعاءً من X وحده بوصفه خبرًا مؤكدًا.

لكل حدث:
1) اجمع الوقائع الأساسية.
2) تحقق من وجود دليل مباشر صالح.
3) حاول corroboration من مصدر ثانٍ مستقل عندما يكون الحدث مهمًا أو حساسًا.
4) ارفض الشائعات والادعاءات غير القابلة للتحقق.
5) لا تخلط بين الرأي والخبر.
6) لا تخترع اسمًا أو رقمًا أو موقعًا أو تاريخًا أو اقتباسًا أو رابطًا.
7) لا تنسخ عنوان المصدر؛ أعد بناء عنوان مهني خاص بنشهل.
8) استخدم لغة عربية صحفية قوية، دقيقة، رصينة، دون تهويل أو عبارات دعائية.
9) لا تستخدم مفردات جازمة مثل "بلا شك" أو "حتماً" عندما لا يثبتها الدليل.
10) عند وجود غموض، اذكره صراحة في حقل التحليل أو الحالة.

المعجم الصحفي المفضل عند ملاءمته للسياق: المشهد، المعطيات، السياق، الدلالة، المؤشرات، التداعيات المحتملة، المسار، موازين التأثير، الاستحقاقات، التطورات المتسارعة، المعطى الميداني، الحراك السياسي، المسار الدبلوماسي، اصطفافات القوى، خريطة التأثير، مكامن الغموض.
لا تستخدم هذه الكلمات لمجرد الزخرفة؛ يجب أن يكون لكل واحدة معنى حقيقي في السياق.

أعد JSON فقط، بلا Markdown، وبحد أقصى 12 حدثًا:
[
  {{
    "title":"عنوان نشهل",
    "summary":"ملخص خبري دقيق من 2-3 جمل",
    "content":"صياغة أوسع من 3-6 جمل عند توفر معطيات كافية",
    "source_name":"اسم المصدر الفعلي",
    "source_url":"الرابط المباشر الذي استندت إليه",
    "published":"تاريخ ووقت ISO-8601 إن توفر وإلا فارغ",
    "category":"الجنوب أو اليمن",
    "confidence":"high أو medium أو low",
    "evidence_count":2,
    "x_only":false,
    "significance":"مرتفع أو متوسط أو عادي",
    "editorial_angle":"زاوية الخبر في سطر واحد",
    "analysis":"قراءة نشهل: ماذا تعني المعطيات دون تجاوز الوقائع",
    "implications":"التداعيات المحتملة بصياغة احتمالية لا جازمة",
    "entities":["جهة","شخص","منطقة"],
    "keywords":["كلمة","كلمة"],
    "title_en":"English headline",
    "summary_en":"English summary"
  }}
]

قواعد إضافية للنشر:
- إذا كان الحدث مستندًا إلى منشور X واحد فقط: x_only=true وconfidence=low وevidence_count=0، ولا يُنشر تلقائيًا.
- إذا كان هناك مصدر واحد مباشر موثوق: يمكن نشره إذا كانت الأدلة واضحة، confidence=medium، evidence_count=1.
- إذا وُجد مصدران مستقلان أو مصدر أولي قوي مع تأكيد داعم: confidence=high، evidence_count>=2.
- source_url يجب أن يكون رابطًا حقيقيًا ظهر في نتائج البحث أو التصفح.
- لا تضع رابط الصفحة الرئيسية بدل رابط الخبر إن كان رابط الخبر متاحًا.
"""

    try:
        response = requests.post(
            "https://api.x.ai/v1/responses",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "model": "grok-4.6",
                "input": [{"role": "user", "content": prompt}],
                "tools": [
                    {"type": "web_search"},
                    {"type": "x_search", "from_date": from_date, "to_date": to_date},
                ],
                "include": ["web_search_call.action.sources"],
            },
            timeout=AI_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        text = response_text(data)
        candidates = parse_json_array(text)
        valid_citations = citations_from_response(data)
        print(f"[AI] discovered={len(candidates)} citations={len(valid_citations)}")

        result = []
        seen = set()
        for candidate in candidates:
            item = normalize_candidate(candidate, valid_citations)
            if not item:
                continue
            if item["id"] in seen:
                continue
            seen.add(item["id"])
            result.append(item)
        return result
    except Exception as exc:
        print(f"[WARN] AI discovery failed: {exc}")
        return []


def dedupe(items):
    by_id = {}
    for item in items:
        if not item or not item.get("id"):
            continue
        by_id[item["id"]] = item
    values = list(by_id.values())
    values.sort(key=lambda x: x.get("published_at") or x.get("published") or "", reverse=True)
    return values


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    existing = load_existing()
    fresh = discover_with_ai()

    if not fresh:
        if existing:
            print(f"[SAFE] لا توجد نتائج جديدة؛ الإبقاء على {len(existing)} خبرًا.")
            return
        print("[SAFE] لم تصل نتائج جديدة ولا توجد بيانات سابقة؛ لن يتم إفراغ الملف.")
        return

    merged = dedupe(existing + fresh)[:MAX_ITEMS]
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(merged, handle, ensure_ascii=False, indent=2)
    print(f"[DONE] {len(merged)} news records; {len(fresh)} discovered by AI")


if __name__ == "__main__":
    main()
