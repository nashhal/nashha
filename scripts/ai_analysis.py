#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تحليل تحريري عربي مطوّل للأخبار المنشورة مع فصل الوقائع عن القراءة السياقية."""
import json
import os
import re
import sys
import time
from urllib.parse import urlparse
import requests

OUT = "data/news.json"
MODEL = "grok-4.5"
MAX_ANALYZE = 20
TIMEOUT = 90
MAX_RETRIES = 1  # لا نحتاج retry للـ 403، لأنها مشكلة صلاحيات دائمة

ALLOWED_ANGLES = ("سياسي", "ميداني", "أمني", "دبلوماسي", "اقتصادي", "إنساني", "متابعة")
ALLOWED_IMPORTANCE = ("مرتفع", "متوسط", "عادي")


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
مهمتك إعداد تقرير تحليلي تحريري دقيق حول الخبر، لا مجرد تلخيصه.
اعتمد على المادة المتاحة فقط، ولا تستحدث أي معلومة غير موجودة فيها.

أعد JSON فقط بهذا الشكل:
{{
  "analysis_ar": "تحليل مطول من 7 إلى 10 فقرات قصيرة، يشرح الخبر وسياقه ودلالته وتداعياته المحتملة، مع الفصل الصريح ب[...]
  "background_ar": "خلفية تفسيرية من 2 إلى 4 فقرات تشرح القضية أو التطور الذي يتناوله الخبر، من دون اختلاق تاريخ أو وق[...]
  "what_happened_ar": "فقرة دقيقة تجيب: ماذا حدث؟ من المعني؟ أين؟ ومتى؟ بحسب المعلومات المتاحة فقط.",
  "why_it_matters_ar": "2 إلى 3 فقرات تشرح أهمية التطور بالنسبة للمشهد اليمني أو الجنوبي، مع تجنب الجزم بما لم تثبته الم[...]
  "implications_ar": ["3 إلى 5 تداعيات أو مسارات محتملة، وكل واحدة بصياغة احتمالية منضبطة"],
  "open_questions_ar": ["حتى 5 أسئلة لا تزال الإجابة عنها غير محسومة من المادة"],
  "analysis_level": "مرتفع أو متوسط أو محدود",
  "news_angle": "سياسي أو ميداني أو أمني أو دبلوماسي أو اقتصادي أو إنساني أو متابعة",
  "importance": "مرتفع أو متوسط أو عادي",
  "entities_ar": ["حتى 8 كيانات مذكورة صراحة"],
  "keywords_ar": ["حتى 10 كلمات مفتاحية مستمدة من النص"]
}}

معايير الدقة:
- لا تضف أسماء أو أرقامًا أو تواريخ أو مواقع أو دوافع أو خلفيات غير ثابتة في المادة.
- إذا كانت المعلومات غ��ر كافية، صرّح بذلك بدل سد الفجوة بالتخمين.
- لا تعتبر كلام طرف واحد حقيقة مطلقة؛ انسب الادعاء إلى قائله عند الحاجة.
- فرّق بين الواقعة والادعاء والتفسير والاحتمال.
- لا تستخدم لغة دعائية أو تحريضية أو عاطفية أو تهويلية.
- لا تتنبأ بالمستقبل بصيغة جازمة.
- استخدم العربية الفصحى الصحفية الواضحة والقوية، مع مصطلحات مثل: المشهد، السياق، المعطيات، الدلالة، التداع[...]
- لا تكرر الجمل بين الحقول؛ لكل حقل وظيفة تحريرية مستقلة.
- اجعل التقرير مفيدًا لقارئ يريد فهم الخبر لا مجرد معرفته.

المصدر: {source}
العنوان: {title}
المادة المتاحة: {summary}
"""

    try:
        r = requests.post(
            "https://api.x.ai/v1/responses",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "input": [{"role": "user", "content": prompt}],
                "include": ["no_inline_citations"],
            },
            timeout=TIMEOUT,
        )
        
        # تسجيل تفصيلي لأي خطأ HTTP
        if not r.ok:
            error_detail = ""
            try:
                error_detail = r.json()
            except:
                error_detail = r.text[:500]
            
            print(f"[ERROR] HTTP {r.status_code} من xAI API")
            print(f"  URL: {r.url}")
            print(f"  Headers: {dict(r.headers)}")
            print(f"  Response: {error_detail}")
            
            if r.status_code == 403:
                print(f"[DIAGNOSTIC] 403 Forbidden - يشير إلى مشكلة صلاحيات:")
                print(f"  - تحقق من صحة XAI_API_KEY في GitHub Secrets")
                print(f"  - تحقق من صلاحيات المفتاح (scopes)")
                print(f"  - تأكد من تفعيل إمكانية الوصول إلى نموذج {MODEL}")
                print(f"  - تحقق من حالة فريق xAI (قد يكون محظورًا أو معلقًا)")
            
            r.raise_for_status()
        
        text = response_text(r.json())
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        return json.loads(match.group(0))
        
    except requests.exceptions.Timeout:
        print(f"[ERROR] انتهت المهلة الزمنية ({TIMEOUT}s) عند الاتصال بـ xAI")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] خطأ في الاتصال بـ xAI: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"[ERROR] فشل تحليل JSON من الاستجابة: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] خطأ غير متوقع: {e}")
        return None


def as_list(value, limit):
    if not isinstance(value, list):
        return []
    return [clean(v) for v in value if clean(v)][:limit]


def main():
    token = os.getenv("XAI_API_KEY")
    if not token:
        print("[ERROR] XAI_API_KEY غير مضبوط؛ لا يمكن إنشاء التقارير التحليلية")
        print("[DIAGNOSTIC] أضف XAI_API_KEY إلى GitHub Secrets في الإعدادات")
        sys.exit(1)

    # تحقق بسيط من صيغة المفتاح (يجب أن يبدأ بـ xai- عادةً)
    if not token.startswith(('xai-', 'sk-')):
        print(f"[WARN] تحذير: XAI_API_KEY قد لا تكون بالصيغة الصحيحة")

    try:
        with open(OUT, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"[ERROR] تعذر قراءة الأخبار: {exc}")
        sys.exit(1)

    if isinstance(data, dict):
        data = data.get("news", data.get("items", []))
    if not isinstance(data, list):
        print("[ERROR] بنية data/news.json غير صالحة")
        sys.exit(1)

    targets = [
        x for x in data
        if isinstance(x, dict)
        and x.get("title")
        and not clean(x.get("analysis_ar"))
        and clean(x.get("status", "published")) == "published"
    ][:MAX_ANALYZE]

    if not targets:
        print("[OK] لا توجد أخبار مستهدفة للتحليل؛ لا توجد مشكلة في هذه الدورة.")
        return

    print(f"[INFO] بدء تحليل {len(targets)} خبر...")
    changed = 0
    failed = 0
    for idx, item in enumerate(targets, 1):
        try:
            print(f"[{idx}/{len(targets)}] معالجة: {item.get('title','')[:60]}...")
            result = analyze(item, token)
            if not isinstance(result, dict):
                failed += 1
                print(f"  [WARN] رد التحليل غير صالح")
                continue

            analysis_ar = clean(result.get("analysis_ar"))
            background_ar = clean(result.get("background_ar"))
            what_happened_ar = clean(result.get("what_happened_ar"))
            why_it_matters_ar = clean(result.get("why_it_matters_ar"))
            if not analysis_ar and not background_ar and not what_happened_ar and not why_it_matters_ar:
                failed += 1
                print(f"  [WARN] الرد لا يحتوي على حقول تحليلية صالحة")
                continue

            item["analysis_ar"] = analysis_ar[:6500]
            item["background_ar"] = background_ar[:2600]
            item["what_happened_ar"] = what_happened_ar[:1800]
            item["why_it_matters_ar"] = why_it_matters_ar[:2600]
            item["implications_ar"] = as_list(result.get("implications_ar"), 5)
            item["open_questions_ar"] = as_list(result.get("open_questions_ar"), 5)

            angle = clean(result.get("news_angle"))
            item["news_angle"] = angle if angle in ALLOWED_ANGLES else "متابعة"

            importance = clean(result.get("importance"))
            item["importance"] = importance if importance in ALLOWED_IMPORTANCE else "عادي"

            level = clean(result.get("analysis_level"))
            item["analysis_level"] = level if level in ("مرتفع", "متوسط", "محدود") else "متوسط"

            item["entities_ar"] = as_list(result.get("entities_ar"), 8)
            item["keywords_ar"] = as_list(result.get("keywords_ar"), 10)
            item["analysis_engine"] = MODEL
            item["analysis_version"] = "2.1"
            changed += 1
            print(f"  [OK] تم التحليل بنجاح")
        except Exception as exc:
            failed += 1
            print(f"  [ERROR] {exc}")

    if changed:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[OK] تم حفظ البيانات في {OUT}")

    if failed and changed == 0:
        print(f"\n[ERROR] فشل تحليل جميع الأخبار: 0/{len(targets)} نجح، {failed} فشل")
        print("[INFO] تحقق من الأخطاء التشخيصية أعلاه")
        sys.exit(1)

    if failed:
        print(f"\n[WARN] نتائج جزئية: {changed}/{len(targets)} نجح، {failed} فشل")

    print(f"[DONE] تم إنشاء {changed} تقريرًا تحليليًا بنجاح")


if __name__ == "__main__":
    main()
