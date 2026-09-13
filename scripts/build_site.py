#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build indexable article pages, sitemaps and crawl rules for Nashhal."""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "news.json"
ARTICLES = ROOT / "articles"
BASE = "https://nashhal.github.io/nashha"


def clean(v: object) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def esc(v: object) -> str:
    return html.escape(clean(v), quote=True)


def parse_dt(v: object):
    text = clean(v).replace("Z", "+00:00")
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def page_url(item: dict) -> str:
    return f"{BASE}/articles/{quote(str(item.get('id', '')).strip())}.html"


def paragraphize(text: str) -> str:
    parts = [clean(p) for p in text.split("\n") if clean(p)]
    return "".join(f"<p>{esc(p)}</p>" for p in parts)


def list_html(items: object) -> str:
    if not isinstance(items, list):
        return ""
    vals = [clean(x) for x in items if clean(x)]
    return "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in vals) + "</ul>" if vals else ""


def render_article(n: dict) -> str:
    title = clean(n.get("title")) or "خبر من نشهل"
    summary = clean(n.get("summary") or n.get("description"))
    published = parse_dt(n.get("published") or n.get("published_at"))
    modified = parse_dt(n.get("updated_at") or n.get("collected_at")) or published
    score = n.get("verification_score")
    try:
        score_text = f"{int(score)}%"
    except (TypeError, ValueError):
        score_text = "غير متاحة"
    verification = clean(n.get("verification"))
    label = {"confirmed": "مؤكد", "developing": "قيد التطور", "unconfirmed": "غير مؤكد"}.get(verification, "قيد التحقق")
    badge = "confirmed" if verification == "confirmed" else "developing" if verification == "developing" else ""
    facts = n.get("facts_ar") if isinstance(n.get("facts_ar"), list) else []
    claims = n.get("claims_ar") if isinstance(n.get("claims_ar"), list) else []
    evidence = n.get("verification_evidence") if isinstance(n.get("verification_evidence"), list) else []
    independent = sum(1 for x in evidence if isinstance(x, dict) and x.get("type") == "independent")
    primary = sum(1 for x in evidence if isinstance(x, dict) and x.get("type") == "primary")
    body = facts if facts else [clean(n.get("content") or summary)]

    graph = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": title,
        "description": summary[:300],
        "url": page_url(n),
        "datePublished": published.isoformat() if published else None,
        "dateModified": modified.isoformat() if modified else None,
        "articleSection": clean(n.get("category") or "الأخبار"),
        "inLanguage": "ar",
        "author": {"@type": "Organization", "name": "غرفة تحرير نشهل"},
        "publisher": {"@type": "Organization", "name": "نشهل", "url": BASE},
        "mainEntityOfPage": {"@type": "WebPage", "@id": page_url(n)},
    }
    graph = {k: v for k, v in graph.items() if v is not None}

    facts_block = f'<section class="box facts"><h2>الوقائع</h2>{list_html(facts)}</section>' if facts else ""
    claims_block = f'<section class="box claims"><h2>ادعاءات تحتاج إلى نسبة</h2>{list_html(claims)}</section>' if claims else ""
    analysis = clean(n.get("analysis_ar"))
    background = clean(n.get("background_ar"))
    what = clean(n.get("what_happened_ar"))
    why = clean(n.get("why_it_matters_ar"))
    implications = list_html(n.get("implications_ar"))
    questions = list_html(n.get("open_questions_ar"))
    analysis_block = ""
    if any((what, background, analysis, why, implications, questions)):
        analysis_block = f'''<section class="box analysis"><div class="analysis-title"><strong>قراءة نشهل</strong><span>{esc(n.get("importance") or "عادي")}</span></div>'''
        if what: analysis_block += f'<div><h3>ماذا حدث؟</h3>{paragraphize(what)}</div>'
        if background: analysis_block += f'<div><h3>خلفية</h3>{paragraphize(background)}</div>'
        if analysis: analysis_block += f'<div><h3>القراءة والسياق</h3>{paragraphize(analysis)}</div>'
        if why: analysis_block += f'<div><h3>لماذا يهم؟</h3>{paragraphize(why)}</div>'
        if implications: analysis_block += f'<div><h3>المسارات المحتملة</h3>{implications}</div>'
        if questions: analysis_block += f'<div><h3>الأسئلة المفتوحة</h3>{questions}</div>'
        analysis_block += "</section>"

    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | نشهل</title>
<meta name="description" content="{esc(summary[:300])}">
<link rel="canonical" href="{page_url(n)}">
<meta property="og:type" content="article"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(summary[:300])}"><meta property="og:url" content="{page_url(n)}"><meta property="og:site_name" content="نشهل">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(summary[:300])}">
<script type="application/ld+json">{json.dumps(graph, ensure_ascii=False)}</script>
<style>
:root{{--bg:#f2f4f6;--paper:#fff;--ink:#14202b;--muted:#687482;--line:#d7dde3;--brand:#0B2A4A;--brand2:#1F5A8A;--ok:#18794e;--warn:#a16207;--soft:#eef3f7;--max:920px}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:2}}
.top{{background:var(--brand);color:#fff;padding:9px 0;font-size:12px}}.wrap{{width:min(var(--max),calc(100% - 30px));margin:auto}}.top a,.back{{color:#fff;text-decoration:none}}
.head{{background:var(--paper);border-bottom:1px solid var(--line);padding:18px 0}}.headrow{{display:flex;justify-content:space-between;gap:15px;align-items:center}}.brand{{font-size:28px;font-weight:900;color:var(--ink);text-decoration:none}}.back{{color:var(--brand2);font-weight:700;text-decoration:none}}
.article{{margin:28px 0 55px;background:var(--paper);border:1px solid var(--line);padding:32px;box-shadow:0 8px 28px rgba(11,42,74,.06)}}.kicker{{color:var(--brand2);font-size:12px;font-weight:900}}h1{{font-size:34px;line-height:1.5;margin:8px 0 10px}}.meta{{color:var(--muted);font-size:12px;border-bottom:1px solid var(--line);padding-bottom:15px}}
.lead{{font-size:20px;font-weight:800;margin:22px 0}}.article-body{{font-size:17px}}.article-body p{{margin:0 0 14px}}
.box{{margin:24px 0;padding:18px 20px;border:1px solid var(--line);background:var(--soft)}}.box h2,.box h3{{margin:0 0 8px;color:var(--brand);font-weight:900;font-size:16px}}.box ul{{margin:0;padding-right:20px}}.box li{{margin:5px 0;font-size:15px}}
.claims{{border-right:4px solid var(--warn);background:#fbfaf4}}.claims h2{{color:#7a5700}}.verification{{border-right:4px solid var(--brand2)}}.ver-head{{display:flex;justify-content:space-between;align-items:center;gap:10px}}.ver-head strong{{font-size:17px}}.badge{{padding:3px 9px;border-radius:3px;background:var(--brand2);color:#fff;font-size:11px;font-weight:900}}.badge.confirmed{{background:var(--ok)}}.badge.developing{{background:var(--warn)}}.ver-text{{color:#344555;font-size:14px;margin-top:8px}}.ver-meta{{color:var(--muted);font-size:10px;margin-top:10px}}
.analysis{{background:#f7f9fb;border-right:4px solid var(--brand2)}}.analysis-title{{display:flex;justify-content:space-between;margin-bottom:8px;color:var(--brand)}}.analysis>div:not(.analysis-title){{border-top:1px solid var(--line);padding-top:14px;margin-top:14px}}.notice{{margin-top:28px;padding-top:15px;border-top:1px solid var(--line);font-size:11px;color:var(--muted)}}footer{{background:#07111c;color:#aab8c3;padding:25px 0;font-size:10px}}
@media(max-width:600px){{.article{{padding:20px}}h1{{font-size:24px}}.lead{{font-size:17px}}.article-body{{font-size:16px}}.headrow,.ver-head{{align-items:flex-start;flex-direction:column}}}}
</style>
</head>
<body>
<div class="top"><div class="wrap"><a href="../index.html">نشهل</a> · منصة أخبار مستقلة</div></div>
<header class="head"><div class="wrap headrow"><a class="brand" href="../index.html">نشهل</a><a class="back" href="../index.html">العودة للأخبار</a></div></header>
<main class="wrap"><article class="article">
<div class="kicker">{esc(n.get("category") or "أخبار")}</div><h1>{esc(title)}</h1>
<div class="meta">{esc(n.get("region") or "")} · {esc(published.isoformat() if published else "")}</div>
<p class="lead">{esc(summary)}</p>
{facts_block}{claims_block}
<div class="article-body">{''.join(f'<p>{esc(clean(x))}</p>' for x in body if clean(x))}</div>
<section class="box verification"><div class="ver-head"><strong>حالة التحقق في نشهل</strong><span class="badge {badge}">{label}</span></div><div class="ver-text">{esc(n.get("verification_basis") or "تُراجع المعطيات المتاحة ويُفصل بين ما ثبت وما نُسب وما يزال قيد التحقق.")}</div><div class="ver-meta">درجة التحقق: {score_text} · مواد التحقق: {len(evidence)} · أولية: {primary} · مستقلة: {independent}</div></section>
{analysis_block}
<div class="notice">هذا خبر محرر باسم نشهل يركز على الحدث نفسه. تحفظ غرفة التحرير مواد التحقق والروابط المرجعية في سجل الحدث لمراجعة الأدلة والتحديثات والتصحيحات. استخدام الذكاء الاصطناعي لا يعني اعتماد المعلومات دون مراجعة قواعد التحقق التحريري.</div>
</article></main><footer><div class="wrap">© نشهل · الحدث أولًا · التحقق أولًا</div></footer>
</body></html>'''


def load_items() -> list[dict]:
    try:
        data = json.loads(DATA.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("news", data.get("items", []))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def main() -> None:
    items = [x for x in load_items() if isinstance(x, dict) and x.get("id") and x.get("title")]
    ARTICLES.mkdir(parents=True, exist_ok=True)
    live = [x for x in items if clean(x.get("status", "published")) == "published"]
    generated = set()
    for item in live:
        path = ARTICLES / f"{item['id']}.html"
        path.write_text(render_article(item), encoding="utf-8")
        generated.add(path.name)

    now = datetime.now(timezone.utc)
    recent = []
    for item in live:
        dt = parse_dt(item.get("published") or item.get("published_at"))
        if dt and now - dt <= timedelta(days=30):
            recent.append(item)
    recent.sort(key=lambda x: parse_dt(x.get("published") or x.get("published_at")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    urls = [f"{BASE}/", f"{BASE}/about.html", f"{BASE}/editorial-policy.html", f"{BASE}/ai-policy.html", f"{BASE}/corrections.html"]
    urls += [page_url(x) for x in live]
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sitemap.append(f"<url><loc>{html.escape(u)}</loc></url>")
    sitemap.append('</urlset>')
    (ROOT / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")

    newsmap = ['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">']
    for item in recent[:1000]:
        dt = parse_dt(item.get("published") or item.get("published_at"))
        if not dt:
            continue
        title = html.escape(clean(item.get("title")))
        pub = dt.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
        newsmap.append(f'<url><loc>{html.escape(page_url(item))}</loc><news:news><news:publication><news:name>نشهل</news:name><news:language>ar</news:language></news:publication><news:publication_date>{pub}</news:publication_date><news:title>{title}</news:title></news:news></url>')
    newsmap.append('</urlset>')
    (ROOT / "news-sitemap.xml").write_text("\n".join(newsmap) + "\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\nSitemap: {BASE}/news-sitemap.xml\n", encoding="utf-8")
    print(f"[DONE] Generated {len(generated)} indexable article pages and sitemaps")


if __name__ == '__main__':
    main()
