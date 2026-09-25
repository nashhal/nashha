#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build indexable article pages, sitemaps and crawl rules for Southern Revolution Newspaper."""
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


def noisy_text(value: object) -> bool:
    text = clean(value)
    if not text:
        return True
    markers = (
        "English UN Logo",
        "ابحث عن بيانات الأمم المتحدة",
        "من نحن عن الأمم المتحدة",
        "Submit search",
        "مسار التنقل",
        "المركز الإعلامي",
    )
    hits = sum(1 for marker in markers if marker in text)
    return hits >= 2 or (len(text) > 700 and hits >= 1)


def display_summary(item: dict) -> str:
    candidates = [
        item.get("summary"),
        item.get("description"),
        item.get("ai_summary_ar"),
        (item.get("facts_ar") or [None])[0] if isinstance(item.get("facts_ar"), list) else None,
        item.get("what_happened_ar"),
    ]
    for candidate in candidates:
        text = clean(candidate)
        if text and not noisy_text(text):
            return text[:320]
    return ""


def display_body(item: dict, summary: str) -> list[str]:
    facts = item.get("facts_ar")
    if isinstance(facts, list) and any(clean(x) for x in facts):
        return [clean(x) for x in facts if clean(x)]
    candidates = [item.get("content"), item.get("body")]
    for candidate in candidates:
        text = clean(candidate)
        if text and not noisy_text(text):
            parts = [clean(p) for p in str(candidate).split("\n") if clean(p)]
            return parts[:20]
    return [summary] if summary else []


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
    title = clean(n.get("title_en")) or "Story | The Southern Revolution"
    summary = clean(n.get("summary_en")) or "This archived story is preserved in its original source record. See the verification record for the original source."
    published = parse_dt(n.get("published") or n.get("published_at"))
    modified = parse_dt(n.get("updated_at") or n.get("collected_at")) or published
    score = n.get("verification_score")
    try:
        score_text = f"{int(score)}%"
    except (TypeError, ValueError):
        score_text = "Not available"
    verification = clean(n.get("verification"))
    label = {"confirmed": "Confirmed", "developing": "Developing", "unconfirmed": "Unverified"}.get(verification, "Under review")
    badge = "confirmed" if verification == "confirmed" else "developing" if verification == "developing" else ""
    facts = n.get("facts_en") if isinstance(n.get("facts_en"), list) else []
    claims = n.get("claims_en") if isinstance(n.get("claims_en"), list) else []
    evidence = n.get("verification_evidence") if isinstance(n.get("verification_evidence"), list) else []
    independent = sum(1 for x in evidence if isinstance(x, dict) and x.get("type") == "independent")
    primary = sum(1 for x in evidence if isinstance(x, dict) and x.get("type") == "primary")
    body = [clean(x) for x in (n.get("content_en") or "").split("\n") if clean(x)]

    graph = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": title,
        "description": summary[:300],
        "url": page_url(n),
        "datePublished": published.isoformat() if published else None,
        "dateModified": modified.isoformat() if modified else None,
        "articleSection": clean(n.get("category_en")) or clean(n.get("category") or "News"),
        "inLanguage": "en",
        "author": {"@type": "Organization", "name": "The Southern Revolution Newsroom"},
        "publisher": {"@type": "Organization", "name": "The Southern Revolution", "url": BASE},
        "mainEntityOfPage": {"@type": "WebPage", "@id": page_url(n)},
        "isAccessibleForFree": True,
    }
    graph = {k: v for k, v in graph.items() if v is not None}

    facts_block = f'<section class="box facts"><h2>Verified Facts</h2>{list_html(facts)}</section>' if facts else ""
    claims_block = f'<section class="box claims"><h2>Attributed Claims</h2>{list_html(claims)}</section>' if claims else ""
    analysis = clean(n.get("analysis_en"))
    background = clean(n.get("background_en"))
    what = clean(n.get("what_happened_en"))
    why = clean(n.get("why_it_matters_en"))
    implications = list_html(n.get("implications_en"))
    questions = list_html(n.get("open_questions_en"))
    analysis_block = ""
    if any((what, background, analysis, why, implications, questions)):
        analysis_block = f'''<section class="box analysis"><div class="analysis-title"><strong>Editorial Context</strong><span>{esc(n.get("importance") or "Normal")}</span></div>'''
        if what: analysis_block += f'<div><h3>What Happened?</h3>{paragraphize(what)}</div>'
        if background: analysis_block += f'<div><h3>Background</h3>{paragraphize(background)}</div>'
        if analysis: analysis_block += f'<div><h3>Context and Analysis</h3>{paragraphize(analysis)}</div>'
        if why: analysis_block += f'<div><h3>Why It Matters</h3>{paragraphize(why)}</div>'
        if implications: analysis_block += f'<div><h3>Possible Paths</h3>{implications}</div>'
        if questions: analysis_block += f'<div><h3>Open Questions</h3>{questions}</div>'
        analysis_block += "</section>"

    return f'''<!doctype html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | The Southern Revolution</title>
<meta name="description" content="{esc(summary[:300])}"><meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Newsreader:opsz,wght@6..72,300;6..72,400;6..72,500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../paper-effects.css">
<link rel="canonical" href="{page_url(n)}">
<meta property="og:type" content="article"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(summary[:300])}"><meta property="og:url" content="{page_url(n)}"><meta property="og:site_name" content="The Southern Revolution">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(summary[:300])}">
<script type="application/ld+json">{json.dumps(graph, ensure_ascii=False)}</script>
<style>
:root{{--bg:#f2f4f6;--paper:#fff;--ink:#14202b;--muted:#687482;--line:#d7dde3;--brand:#0B2A4A;--brand2:#1F5A8A;--ok:#18794e;--warn:#a16207;--soft:#eef3f7;--max:920px}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:'Newsreader',serif;line-height:2}}
.top{{background:var(--brand);color:#fff;padding:9px 0;font-size:12px}}.wrap{{width:min(var(--max),calc(100% - 30px));margin:auto}}.top a,.back{{color:#fff;text-decoration:none}}
.head{{background:var(--paper);border-bottom:1px solid var(--line);padding:18px 0}}.headrow{{display:flex;justify-content:space-between;gap:15px;align-items:center}}.brand{{font-size:28px;font-weight:900;color:var(--ink);text-decoration:none}}.back{{color:var(--brand2);font-weight:700;text-decoration:none}}
.article{{margin:28px 0 55px;background:var(--paper);border:1px solid var(--line);padding:32px;box-shadow:0 8px 28px rgba(11,42,74,.06)}}.kicker{{color:var(--brand2);font-size:12px;font-weight:900}}h1{{font-family:'Newsreader',serif;font-size:42px;line-height:1.35;margin:8px 0 10px;font-weight:700}}.meta{{color:var(--muted);font-size:12px;border-bottom:1px solid var(--line);padding-bottom:15px}}
.lead{{font-family:'Source Serif 4',serif;font-size:21px;font-weight:600;line-height:1.9;margin:22px 0}}.article-body{{font-family:'Source Serif 4',serif;font-size:18px;line-height:2}}.article-body p{{margin:0 0 14px}}
.box{{margin:24px 0;padding:18px 20px;border:1px solid var(--line);background:var(--soft)}}.box h2,.box h3{{margin:0 0 8px;color:var(--brand);font-weight:900;font-size:16px}}.box ul{{margin:0;padding-right:20px}}.box li{{margin:5px 0;font-size:15px}}
.claims{{border-right:4px solid var(--warn);background:#fbfaf4}}.claims h2{{color:#7a5700}}.verification{{border-right:4px solid var(--brand2)}}.trust-box{{background:linear-gradient(135deg,#f4f9fc,#edf6f5);border-right:4px solid #39bfe2}}.trust-box .trust-row{{display:flex;justify-content:space-between;align-items:center;gap:12px}}.trust-box .trust-title{{font-size:16px;font-weight:900;color:var(--brand)}}.trust-box .trust-state{{font-size:10px;color:var(--muted);margin-top:4px}}.trust-btn{{display:inline-flex;padding:7px 11px;border-radius:7px;background:var(--brand);color:#fff;text-decoration:none;font-size:10px;font-weight:900;white-space:nowrap}}.trust-box .trust-meta{{display:flex;flex-wrap:wrap;gap:7px;margin-top:10px;color:var(--muted);font-size:9px}}.trust-box code{{font-family:ui-monospace,SFMono-Regular,monospace;direction:ltr}}.ver-head{{display:flex;justify-content:space-between;align-items:center;gap:10px}}.ver-head strong{{font-size:17px}}.badge{{padding:3px 9px;border-radius:3px;background:var(--brand2);color:#fff;font-size:11px;font-weight:900}}.badge.confirmed{{background:var(--ok)}}.badge.developing{{background:var(--warn)}}.ver-text{{color:#344555;font-size:14px;margin-top:8px}}.ver-meta{{color:var(--muted);font-size:10px;margin-top:10px}}
.analysis{{background:#f7f9fb;border-right:4px solid var(--brand2)}}.analysis-title{{display:flex;justify-content:space-between;margin-bottom:8px;color:var(--brand)}}.analysis>div:not(.analysis-title){{border-top:1px solid var(--line);padding-top:14px;margin-top:14px}}.notice{{margin-top:28px;padding-top:15px;border-top:1px solid var(--line);font-size:11px;color:var(--muted)}}footer{{background:#07111c;color:#aab8c3;padding:25px 0;font-size:10px}}
@media(max-width:600px){{.article{{padding:20px}}h1{{font-size:24px}}.lead{{font-size:17px}}.article-body{{font-size:16px}}.headrow,.ver-head{{align-items:flex-start;flex-direction:column}}}}
</style>
</head>
<body>
<div class="top"><div class="wrap"><a href="../index.html">The Southern Revolution</a> · Independent News Platform</div></div>
<header class="head"><div class="wrap headrow"><a class="brand" href="../index.html">The Southern Revolution</a><a class="back" href="../index.html">Back to News</a></div></header>
<main class="wrap"><article class="article">
<div class="kicker">{esc(n.get("category_en") or ("South" if n.get("category")=="الجنوب" else "Yemen" if n.get("category")=="اليمن" else "News"))}</div><h1>{esc(title)}</h1>
<div class="meta">{esc(n.get("region_en") or "Yemen")} · {esc(published.isoformat() if published else "")}</div>
<p class="lead">{esc(summary)}</p>
{facts_block}{claims_block}
<div class="article-body">{''.join(f'<p>{esc(clean(x))}</p>' for x in body if clean(x))}</div>
<section class="box verification"><div class="ver-head"><strong>Verification Status</strong><span class="badge {badge}">{label}</span></div><div class="ver-text">{esc(n.get("verification_basis_en") or "Available information is reviewed, separating established facts from attributed claims and unresolved details.")}</div><div class="ver-meta">Verification score: {score_text} · Evidence: {len(evidence)} · Primary: {primary} · Independent: {independent}</div></section><section class="box trust-box" data-news-id="{esc(n.get("id"))}"><div class="trust-row"><div><div class="trust-title">Southern Revolution Trust · Verifiable Record</div><div class="trust-state" id="trustState">Digital fingerprint stored in the newspaper record · Web3 status available on the verification page</div></div><a class="trust-btn" href="../trust.html?id={quote(str(n.get("id","")).strip())}">Open Verification Log ↗</a></div><div class="trust-meta"><span>SHA-256</span><span>·</span><span id="web3State">Web3: Under Review</span><span>·</span><span>Story text and images are not stored on-chain</span></div></section>
{analysis_block}
<div class="notice">This story is edited by The Southern Revolution and focuses on the event itself. The newsroom retains verification materials and reference links for evidence review, updates and corrections. AI assistance does not replace editorial verification.</div>
</article></main><footer><div class="wrap">© The Southern Revolution · News First · Verification First · Al-Thawra Trust</div></footer>
<script src="../paper-effects.js" defer></script>

</body></html>'''


def load_items() -> list[dict]:
    try:
        data = json.loads(DATA.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("news", data.get("items", []))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def library_item_url(record_id: object) -> str:
    return f"{BASE}/library/item/{quote(str(record_id).strip())}.html"


def library_item_path(record_id: object) -> Path:
    return ROOT / "library" / "item" / f"{str(record_id).strip()}.html"


def library_collections() -> list[dict]:
    return [
        {"id":"history","name":"History","description":"Historical records, timelines and contextual material."},
        {"id":"documents","name":"Documents","description":"Official documents, declarations, agreements and records."},
        {"id":"newspapers","name":"Newspapers","description":"Newspaper reports and archived editions."},
        {"id":"books","name":"Books & Research","description":"Books, studies, journals and research publications."},
        {"id":"reports","name":"Reports","description":"Institutional, humanitarian and analytical reports."},
        {"id":"maps","name":"Maps","description":"Historical and geographic maps."},
        {"id":"photographs","name":"Photographs & Media","description":"Photographs, posters and audiovisual references."},
        {"id":"people","name":"People","description":"Biographical and archival records on people."},
        {"id":"institutions","name":"Institutions","description":"Organizations, authorities and institutions."},
        {"id":"oral-history","name":"Oral History","description":"Recorded memories and testimony with source notes."},
        {"id":"current-news","name":"News Archive","description":"Published Southern Revolution news records."},
        {"id":"references","name":"Reference Index","description":"Cross-referenced bibliographic and source material."},
    ]


def build_library(items: list[dict]) -> list[dict]:
    curated_path = ROOT / "data" / "library-curated.json"
    curated = []
    if curated_path.exists():
        try:
            raw = json.loads(curated_path.read_text(encoding="utf-8"))
            curated = raw.get("items", []) if isinstance(raw, dict) else raw
        except Exception:
            curated = []

    records: list[dict] = []
    seen: set[str] = set()

    for raw in curated:
        if not isinstance(raw, dict):
            continue
        rid = clean(raw.get("id"))
        title = clean(raw.get("title"))
        if not rid or not title or rid in seen:
            continue
        rec = dict(raw)
        rec.setdefault("language", "English")
        rec.setdefault("collection", "references")
        rec["page_url"] = rec.get("page_url") or f"{BASE}/library/item/{quote(rid)}.html"
        records.append(rec)
        seen.add(rid)

    for n in items:
        if not isinstance(n, dict) or not clean(n.get("id")):
            continue
        rid = f"NEWS-{clean(n.get('id'))}"
        if rid in seen:
            continue
        dt = parse_dt(n.get("published") or n.get("published_at"))
        region = clean(n.get("region_en") or n.get("region")) or "Southern Yemen"
        source = clean(n.get("source_name_en") or n.get("source_name") or n.get("source")) or "Unknown source"
        title = clean(n.get("title_en") or n.get("title")) or "Untitled news record"
        description = clean(n.get("summary_en") or n.get("description"))[:420]
        subjects = [x for x in [clean(n.get("category_en") or n.get("category")), region] if x]
        rec = {
            "id": rid,
            "title": title,
            "description": description,
            "type": "newspaper",
            "collection": "current-news",
            "collection_name": "News Archive",
            "date": dt.isoformat() if dt else "",
            "region": region,
            "location": region,
            "language": "English",
            "subjects": subjects,
            "people": [],
            "institutions": [],
            "source": source,
            "source_url": clean(n.get("source_url") or n.get("link")),
            "verification": clean(n.get("verification_status") or n.get("verification") or "Under review"),
            "verification_score": n.get("verification_score"),
            "original_news_id": clean(n.get("id")),
            "article_url": page_url(n),
            "page_url": library_item_url(rid),
        }
        records.append(rec)
        seen.add(rid)

    return records


def render_library_item(record: dict) -> str:
    title = clean(record.get("title")) or "Archive Record"
    description = clean(record.get("description")) or "Archive record preserved for research and reference."
    date = parse_dt(record.get("date"))
    rid = clean(record.get("id"))
    source = clean(record.get("source")) or "Archive record"
    region = clean(record.get("region")) or "Southern Yemen"
    collection = clean(record.get("collection_name")) or clean(record.get("collection")) or "Archive"
    source_url = clean(record.get("source_url"))
    article_url = clean(record.get("article_url"))
    subjects = record.get("subjects") if isinstance(record.get("subjects"), list) else []
    verification = clean(record.get("verification")) or "Not assessed"

    graph = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "headline": title,
        "name": title,
        "description": description[:300],
        "url": library_item_url(rid),
        "datePublished": date.isoformat() if date else None,
        "inLanguage": clean(record.get("language")) or "en",
        "isAccessibleForFree": True,
        "publisher": {"@type": "Organization", "name": "The Southern Revolution", "url": BASE},
        "about": [{"@type":"Thing","name": clean(x)} for x in subjects if clean(x)],
    }
    graph = {k:v for k,v in graph.items() if v is not None}

    source_link = f'<a class="source" href="{esc(source_url)}" target="_blank" rel="noopener noreferrer">Open original source ↗</a>' if source_url else ""
    article_link = f'<a class="secondary" href="{esc(article_url)}">Open newsroom article ↗</a>' if article_url else ""

    return f'''<!doctype html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | Library | The Southern Revolution</title>
<meta name="description" content="{esc(description[:300])}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<link rel="canonical" href="{library_item_url(rid)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description[:300])}">
<meta property="og:url" content="{library_item_url(rid)}">
<meta property="og:site_name" content="The Southern Revolution">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Newsreader:opsz,wght@6..72,300;6..72,400;6..72,500&display=swap" rel="stylesheet">
<style>
:root{{--paper:#fffdf8;--bg:#d9d7d1;--ink:#141414;--muted:#716c64;--line:rgba(20,20,20,.18);--black:#0e0e0d}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,Arial,sans-serif}}a{{color:inherit;text-decoration:none}}
.top{{background:var(--black);color:#fff;padding:12px 0;font:500 9px Inter,sans-serif;letter-spacing:1.5px}}.wrap{{width:min(920px,calc(100% - 28px));margin:auto}}
.toprow{{display:flex;justify-content:space-between;gap:15px}}.top a{{color:#fff}}
.sheet{{background:var(--paper);margin:28px auto 60px;padding:30px 34px 42px;border-top:1px solid var(--ink);box-shadow:0 24px 70px rgba(0,0,0,.12)}}
.crumb{{display:flex;justify-content:space-between;gap:15px;padding-bottom:10px;border-bottom:.5px solid var(--line);font:300 8px Inter,sans-serif;color:var(--muted);text-transform:uppercase;letter-spacing:1px}}
.kicker{{margin-top:30px;font:500 9px Inter,sans-serif;letter-spacing:2px;color:#757067;text-transform:uppercase}}
h1{{margin:8px 0 10px;font:300 clamp(38px,6vw,66px)/1.02 Newsreader,Georgia,serif;letter-spacing:-1.5px}}
.lead{{max-width:760px;color:#57524c;font:300 14px/1.8 Inter,sans-serif}}
.meta{{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px;padding:12px 0;border-top:.5px solid var(--line);border-bottom:.5px solid var(--line);color:var(--muted);font:300 8px/1.5 Inter,sans-serif}}
.meta b{{font-weight:500;color:var(--ink)}}.section{{margin-top:24px;padding-top:17px;border-top:.5px solid var(--line)}}.section h2{{margin:0 0 9px;font:400 24px Newsreader,serif}}
.record-grid{{display:grid;grid-template-columns:1fr 1fr;gap:0;border:.5px solid var(--line)}}.cell{{padding:13px;border-right:.5px solid var(--line);border-bottom:.5px solid var(--line)}}.cell:nth-child(2n){{border-right:0}}.cell:nth-last-child(-n+2){{border-bottom:0}}.cell span{{display:block;color:var(--muted);font:500 7px Inter,sans-serif;letter-spacing:1px;text-transform:uppercase}}.cell strong{{display:block;margin-top:5px;font:400 15px Newsreader,serif;line-height:1.45}}
.links{{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}}.links a{{padding:9px 12px;border:.5px solid var(--ink);font:500 8px Inter,sans-serif;text-transform:uppercase;letter-spacing:.7px}}.links a.source{{background:var(--black);color:#fff}}
.note{{margin-top:25px;padding-top:14px;border-top:.5px solid var(--line);color:var(--muted);font:300 9px/1.8 Inter,sans-serif}}
footer{{background:var(--black);color:#a9a49c;padding:20px 0;font:300 8px Inter,sans-serif}}
@media(max-width:620px){{.sheet{{padding:23px 18px 32px}}.record-grid{{grid-template-columns:1fr}}.cell,.cell:nth-child(2n){{border-right:0}}.cell:nth-last-child(-n+2){{border-bottom:.5px solid var(--line)}}.cell:last-child{{border-bottom:0}}}}
</style>
<script type="application/ld+json">{json.dumps(graph, ensure_ascii=False)}</script>
</head>
<body>
<div class="top"><div class="wrap toprow"><a href="../../library.html">THE SOUTHERN REVOLUTION LIBRARY</a><a href="../../index.html">NEWSPAPER ↗</a></div></div>
<main class="wrap sheet">
<div class="crumb"><span>{esc(collection)}</span><span>Record {esc(rid)}</span></div>
<div class="kicker">Archive Record</div>
<h1>{esc(title)}</h1>
<p class="lead">{esc(description)}</p>
<div class="meta"><span><b>Date</b> · {esc(date.isoformat() if date else "Undated")}</span><span>·</span><span><b>Region</b> · {esc(region)}</span><span>·</span><span><b>Source</b> · {esc(source)}</span></div>
<section class="section"><h2>Record Details</h2><div class="record-grid">
<div class="cell"><span>Collection</span><strong>{esc(collection)}</strong></div>
<div class="cell"><span>Language</span><strong>{esc(record.get("language") or "English")}</strong></div>
<div class="cell"><span>Verification</span><strong>{esc(verification)}</strong></div>
<div class="cell"><span>Record ID</span><strong>{esc(rid)}</strong></div>
</div></section>
<section class="section"><h2>Subjects</h2><p class="lead">{esc(" · ".join(clean(x) for x in subjects if clean(x)) or "No subject tags have been assigned yet.")}</p></section>
<div class="links">{source_link}{article_link}<a class="secondary" href="../../library.html">Back to library ↗</a></div>
<div class="note">This archive record preserves source and descriptive metadata for research. A source link identifies the origin of the material; it does not by itself constitute independent verification or endorsement of every claim contained in the source.</div>
</main>
<footer><div class="wrap">The Southern Revolution Library · Archive · Search · Research</div></footer>
</body>
</html>'''


def write_library_outputs(records: list[dict]) -> None:
    out_path = ROOT / "data" / "library.json"
    collections = library_collections()
    counts = {c["id"]:0 for c in collections}
    sources: set[str] = set()
    regions: set[str] = set()
    for record in records:
        cid = clean(record.get("collection")) or "references"
        if cid in counts:
            counts[cid] += 1
        if clean(record.get("source")):
            sources.add(clean(record.get("source")))
        if clean(record.get("region")):
            regions.add(clean(record.get("region")))
    for c in collections:
        c["count"] = counts.get(c["id"], 0)
    payload = {
        "version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "collections": collections,
        "stats": {"total_records":len(records),"sources":len(sources),"regions":len(regions)},
        "items": records,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    item_dir = ROOT / "library" / "item"
    item_dir.mkdir(parents=True, exist_ok=True)
    for record in records:
        path = library_item_path(record.get("id"))
        path.write_text(render_library_item(record), encoding="utf-8")

def main() -> None:
    items = [x for x in load_items() if isinstance(x, dict) and x.get("id") and x.get("title")]
    ARTICLES.mkdir(parents=True, exist_ok=True)
    live = [x for x in items if clean(x.get("status", "published")) == "published"]
    library_records = build_library(live)
    write_library_outputs(library_records)
    generated = set()
    for item in live:
        path = ARTICLES / f"{item['id']}.html"
        path.write_text(render_article(item), encoding="utf-8")
        generated.add(path.name)

    now = datetime.now(timezone.utc)
    recent = []
    for item in live:
        dt = parse_dt(item.get("published") or item.get("published_at"))
        if dt and now - dt <= timedelta(days=2):
            recent.append(item)
    recent.sort(key=lambda x: parse_dt(x.get("published") or x.get("published_at")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    urls = [f"{BASE}/", f"{BASE}/about.html", f"{BASE}/editorial-policy.html", f"{BASE}/ai-policy.html", f"{BASE}/corrections.html", f"{BASE}/trust.html", f"{BASE}/web3.html", f"{BASE}/search.html", f"{BASE}/library.html"]
    urls += [page_url(x) for x in live]
    urls += [library_item_url(x.get("id")) for x in library_records]
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
        title = html.escape(clean(item.get("title_en") or item.get("title")))
        pub = dt.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
        newsmap.append(f'<url><loc>{html.escape(page_url(item))}</loc><news:news><news:publication><news:name>The Southern Revolution</news:name><news:language>en</news:language></news:publication><news:publication_date>{pub}</news:publication_date><news:title>{title}</news:title></news:news></url>')
    newsmap.append('</urlset>')
    (ROOT / "news-sitemap.xml").write_text("\n".join(newsmap) + "\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\nSitemap: {BASE}/news-sitemap.xml\n", encoding="utf-8")
    print(f"[DONE] Generated {len(generated)} article pages + {len(library_records)} library records and sitemaps")


if __name__ == '__main__':
    main()
