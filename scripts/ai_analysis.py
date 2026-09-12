#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تحليل تحريري عربي للأخبار المنشورة مع فصل الوقائع عن القراءة السياقية."""
import json
import os
import re
from urllib.parse import urlparse
import requests

OUT = "data/news.json"
MODEL = "grok-4.5"
MAX_ANALYZE = 20
TIMEOUT = 90


def clean(value):
    value = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", value).strip()


def response_text(data):
    parts = []
    for output in data.get("output", []):
        if output.get("type") != "message":
            continue
        for content in output.get("content", []):
            if content.get("type") == "output_text":
                parts.append(content.get("text", ""))
    return "\n".join(parts).strip()


def domain(url):
    return urlparse(str(url)).netloc.lower().removeprefix("www.")


def analyze(item, token):
    title = clean(item.get("title") or item.get("original_title"))
    summary = clean(item.get("summary") or item.get("description") or item.get("content"))
    source = clean(item.get("source_name") or item.get("source"))
    prompt = f"""أنت محرر أول ومحلل أخبار في غرفة تحرير عربية محترفة لمنصة نشهل.
حلّل الخبر التالي اعتمادًا على النص المتاح فقط.

المطلوب JSON فقط:
{{
  "analysis_ar":"قراءة سياقية من 2 إلى 4 جمل",
  "news_angle":"سياسي أو ميداني أو أمني أو دبلوماسي أو اقتصادي أو إنساني أو متابعة",
  "importance":"مرتفع أو متوسط أو عادي",
  "entities_ar":["حتى 6 كيانات مذكورة صراحة"],
  "keywords_ar":["حتى 8 كلمات مفتاحية مستمدة من النص"]
}}

قواعد التحرير:
- اشرح ما تعنيه المعلومة في سياقها، لا تعِد صياغة الخبر فقط.
- ميّز بوضوح بين الوقائع المثبتة والقراءة التحليلية.
- لا تضف أي اسم أو رقم أو تاريخ أو موقع أو سبب غير وارد في المادة.
- لا تقدّم استنتاجًا جازمًا عن المستقبل. استخدم عند الحاجة: تشير المعطيات، في السياق الراهن، قد تعكس، من شأنه أن، لا تكفي المعطيات للجزم.
- استخدم لغة عربية فصيحة قوية ورصينة، وتوظيفًا طبيعيًا لمصطلحات: المشهد، السياق، المعطيات، الدلالة، التداعيات، المسار، المؤشرات، الفاعلون، الاستحقاقات، موازين التأثير، مكامن الغموض، الحراك السياسي، التطورات الميدانية، المسار الدبلوماسي.
- لا تستخدم لغة دعائية أو تحريضية أو مبالغة.
- لا تحوّل التحليل إلى رأي شخصي.

المصدر: {source}
العنوان: {title}
المادة: {summary}
"""
    r = requests.post(
        "https://api.x.ai/v1/responses",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"model": MODEL, "input": [{"role": "user", "content": prompt}], "include": ["no_inline_citations"]},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    text = response_text(r.json())
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    return json.loads(match.group(0))


def main():
    token = os.getenv("XAI_API_KEY")
    if not token:
        print("[INFO] XAI_API_KEY غير مضبوط؛ تخطي التحليل")
        return
    try:
        with open(OUT, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"[WARN] تعذر قراءة الأخبار: {exc}")
        return
    if isinstance(data, dict):
        data = data.get("news", data.get("items", []))
    if not isinstance(data, list):
        return

    targets = [x for x in data if isinstance(x, dict) and x.get("title") and not clean(x.get("analysis_ar")) and clean(x.get("status", "published")) == "published"][:MAX_ANALYZE]
    changed = 0
    for item in targets:
        try:
            result = analyze(item, token)
            if not isinstance(result, dict):
                continue
            item["analysis_ar"] = clean(result.get("analysis_ar"))[:1400]
            angle = clean(result.get("news_angle"))
            item["news_angle"] = angle if angle in ("سياسي", "ميداني", "أمني", "دبلوماسي", "اقتصادي", "إنساني", "متابعة") else "متابعة"
            importance = clean(result.get("importance"))
            item["importance"] = importance if importance in ("مرتفع", "متوسط", "عادي") else "عادي"
            item["entities_ar"] = [clean(v) for v in result.get("entities_ar", []) if clean(v)][:6]
            item["keywords_ar"] = [clean(v) for v in result.get("keywords_ar", []) if clean(v)][:8]
            item["analysis_engine"] = MODEL
            changed += 1
            print(f"[OK] تحليل: {item.get('title','')[:80]}")
        except Exception as exc:
            print(f"[WARN] تعذر تحليل خبر: {exc}")

    if changed:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[DONE] تم تحليل {changed} خبرًا")


if __name__ == "__main__":
    main()
