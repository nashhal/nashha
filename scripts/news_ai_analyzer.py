#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""نشهل: طبقة تحرير وتحليل الأخبار باستخدام Claude Sonnet 5.

تعمل على data/news.json بعد مرحلة اكتشاف الأخبار. لا تجلب مصادر محددة
ولا تضيف قنوات جديدة؛ مهمتها تحليل الخبر الموجود، تقوية الصياغة العربية،
التصنيف، واكتشاف مؤشرات التغطية المتقاطعة داخل البيانات الحالية.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

try:
    import anthropic
except ImportError:
    print("يلزم تثبيت المكتبة: pip install anthropic", file=sys.stderr)
    raise

OUT = "data/news.json"
MODEL = "claude-sonnet-5"
MAX_ANALYZE = 24
MAX_RETRIES = 3
RETRY_BACKOFF = 4
REQUEST_PAUSE = 0.8
CORROBORATION_WINDOW_HOURS = 30
CORROBORATION_SIMILARITY = 0.62

CATEGORIES = {"الجنوب", "اليمن"}
ANGLES = {"سياسي", "ميداني", "أمني", "دبلوماسي", "اقتصادي", "إنساني", "متابعة"}
IMPORTANCE = {"مرتفع", "متوسط", "عادي"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("nashhal-news-ai")

SYSTEM_PROMPT = """أنت رئيس تحرير في غرفة أخبار عربية محترفة تابعة لمنصة نشهل اليمنية.
تتعامل مع مادة إخبارية خام، ومهمتك إنتاج صياغة تحريرية دقيقة ورصينة دون اختلاق أي معلومة.

أخرج JSON فقط بهذه الحقول:
{
  \"title\": \"عنوان صحفي قوي ومباشر لا يتجاوز 20 كلمة\",
  \"summary\": \"ملخص من 2 إلى 3 جمل يشرح جوهر الخبر بوضوح\",
  \"analysis_ar\": \"قراءة سياقية من 2 إلى 4 جمل تشرح الدلالة المحتملة دون الجزم بالمستقبل\",
  \"news_angle\": \"سياسي أو ميداني أو أمني أو دبلوماسي أو اقتصادي أو إنساني أو متابعة\",
  \"importance\": \"مرتفع أو متوسط أو عادي\",
  \"category\": \"الجنوب أو اليمن\",
  \"confidence\": \"high أو medium أو low\",
  \"entities_ar\": [\"حتى 6 كيانات مذكورة صراحة\"],
  \"keywords_ar\": [\"حتى 8 كلمات مفتاحية\"],
  \"is_relevant\": true
}

قواعد نشهل التحريرية:
- لا تضف رقمًا أو اسمًا أو تاريخًا أو موقعًا أو سببًا أو اقتباسًا غير موجود في المادة.
- لا تنسب موقفًا أو نية إلى أي طرف دون نص صريح أو قرينة واضحة في المادة نفسها.
- ميّز بين الوقائع وبين القراءة السياقية. لا تجعل التحليل يبدو كأنه حقيقة مثبتة.
- استخدم فصيحًا صحفيًا قويًا، طبيعيًا وغير متكلف.
- استخدم عند الحاجة مصطلحات مثل: المشهد، السياق، المعطيات، الدلالة، التداعيات، المسار، المؤشرات، الفاعلون، الاستحقاقات، موازين التأثير، مكامن الغموض، الحراك السياسي، التطورات الميدانية، المسار الدبلوماسي.
- تجنب اللغة الدعائية والتحريضية والتضخيم والعبارات القطعية من نوع: سيؤدي حتمًا، يثبت بما لا يدع مجالًا للشك.
- لا تقل إن الخبر مؤكد لمجرد أن المصدر يحمل اسمًا معروفًا؛ قيّم وضوح المادة وقوة التفاصيل.
- إذا كانت المادة غامضة أو ناقصة، خفّض الثقة إلى medium أو low بدل ملء الفراغ بالتخمين.
- إذا لم يكن الخبر متعلقًا جوهريًا باليمن أو الجنوب، اجعل is_relevant=false.
"""


def clean(value: Any) -> str:
    value = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", value).strip()


def response_text(data: dict[str, Any]) -> str:
    parts: list[str] = []
    for output in data.get("output", []):
        if output.get("type") != "message":
            continue
        for content in output.get("content", []):
            if content.get("type") == "output_text":
                parts.append(content.get("text", ""))
    return "\n".join(parts).strip()


def parse_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        value = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def parse_dt(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, clean(a).lower(), clean(b).lower()).ratio()


def corroborated_by(item: dict[str, Any], existing: list[dict[str, Any]]) -> list[str]:
    title = clean(item.get("title"))
    category = clean(item.get("category"))
    published = parse_dt(item.get("published"))
    if not title or not published:
        return []

    matches: list[str] = []
    for other in existing:
        if other is item or clean(other.get("status", "published")) != "published":
            continue
        if clean(other.get("category")) != category:
            continue
        other_time = parse_dt(other.get("published"))
        if not other_time:
            continue
        if abs((published - other_time).total_seconds()) > CORROBORATION_WINDOW_HOURS * 3600:
            continue
        if similarity(title, clean(other.get("title"))) >= CORROBORATION_SIMILARITY:
            source = clean(other.get("source_name") or other.get("source"))
            if source and source != clean(item.get("source_name") or item.get("source")) and source not in matches:
                matches.append(source)
    return matches


def analyze_item(client: anthropic.Anthropic, item: dict[str, Any]) -> dict[str, Any] | None:
    source = clean(item.get("source_name") or item.get("source"))
    title = clean(item.get("title") or item.get("original_title"))
    raw = clean(item.get("content") or item.get("summary") or item.get("description"))
    if not raw or not title:
        return None

    user_prompt = f"""المصدر: {source}\n\nالعنوان الحالي:\n{title}\n\nالمادة الخام:\n{raw[:7000]}"""

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=1100,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            result = parse_json_object("".join(
                block.text for block in response.content if getattr(block, "type", "") == "text"
            ))
            if result is not None:
                return result
            raise ValueError("Claude returned invalid JSON")
        except (anthropic.APIStatusError, anthropic.APIConnectionError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF * attempt
                log.warning("إعادة تحليل الخبر (%d/%d) بعد %ds: %s", attempt, MAX_RETRIES, wait, exc)
                time.sleep(wait)
    log.error("تعذر تحليل الخبر بعد %d محاولات: %s", MAX_RETRIES, last_error)
    return None


def main() -> None:
    token = os.getenv("ANTHROPIC_API_KEY")
    if not token:
        log.info("ANTHROPIC_API_KEY غير مضبوط؛ تخطي طبقة Claude")
        return

    try:
        with open(OUT, encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        log.warning("تعذر قراءة %s: %s", OUT, exc)
        return

    if isinstance(data, dict):
        data = data.get("news", data.get("items", []))
    if not isinstance(data, list):
        return

    targets = [
        item for item in data
        if isinstance(item, dict)
        and clean(item.get("title"))
        and clean(item.get("status", "published")) == "published"
        and not clean(item.get("editorial_ai_status"))
    ][:MAX_ANALYZE]

    if not targets:
        log.info("لا توجد أخبار جديدة للتحليل")
        return

    client = anthropic.Anthropic(api_key=token)
    changed = 0

    for index, item in enumerate(targets, start=1):
        log.info("تحليل %d/%d: %s", index, len(targets), clean(item.get("title"))[:80])
        result = analyze_item(client, item)
        time.sleep(REQUEST_PAUSE)
        if not result or result.get("is_relevant") is False:
            item["editorial_ai_status"] = "rejected_irrelevant"
            continue

        title = clean(result.get("title"))
        summary = clean(result.get("summary"))
        analysis = clean(result.get("analysis_ar"))
        category = clean(result.get("category")) if clean(result.get("category")) in CATEGORIES else "اليمن"
        angle = clean(result.get("news_angle")) if clean(result.get("news_angle")) in ANGLES else "متابعة"
        importance = clean(result.get("importance")) if clean(result.get("importance")) in IMPORTANCE else "عادي"
        confidence = clean(result.get("confidence")) if clean(result.get("confidence")) in {"high", "medium", "low"} else "medium"

        item["original_title"] = item.get("original_title") or item.get("title")
        if title:
            item["title"] = title[:300]
        if summary:
            item["summary"] = summary[:1000]
            item["description"] = summary[:400]
            item["content"] = summary[:1000]
        item["category"] = category
        item["analysis_ar"] = analysis[:1600]
        item["news_angle"] = angle
        item["importance"] = importance
        item["confidence"] = confidence
        item["entities_ar"] = [clean(x) for x in result.get("entities_ar", []) if clean(x)][:6]
        item["keywords_ar"] = [clean(x) for x in result.get("keywords_ar", []) if clean(x)][:8]
        item["analysis_engine"] = MODEL
        item["editorial_ai_status"] = "analyzed"
        changed += 1

    # بعد تحديث العناوين، نبحث عن تغطيات متقاطعة ضمن النسخة الكاملة.
    for item in data:
        if isinstance(item, dict) and item.get("editorial_ai_status") == "analyzed":
            item["corroborated_by"] = corroborated_by(item, data)
            if len(item["corroborated_by"]) >= 2 and item.get("confidence") != "high":
                item["confidence"] = "high"

    if changed:
        with open(OUT, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
    log.info("[DONE] تم تحرير %d خبرًا بواسطة %s", changed, MODEL)


if __name__ == "__main__":
    main()
