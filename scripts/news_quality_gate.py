#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quality gate: validate freshness, evidence strength and publication readiness."""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "news.json"
MAX_LIVE_AGE_HOURS = 72
FETCH_TIMEOUT = 12
YEAR_RE = re.compile(r"\b(20\d{2})\b")
DATE_META_RE = re.compile(r'<meta[^>]+(?:property|name)=["\'](?:article:published_time|datePublished|publish-date|date)["\'][^>]+content=["\']([^"\']+)["\']', re.I)
JSON_DATE_RE = re.compile(r'"(?:datePublished|dateModified|uploadDate)"\s*:\s*"([^"]+)"', re.I)


def dt(value):
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        x = datetime.fromisoformat(text)
        return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def source_date(url: str):
    if not str(url).startswith(("http://", "https://")):
        return None
    try:
        r = requests.get(url, timeout=FETCH_TIMEOUT, headers={"User-Agent": "NashhalNewsBot/1.0 (+https://nashhal.github.io/nashha)"})
        if not r.ok:
            return None
        text = r.text[:500000]
        match = DATE_META_RE.search(text) or JSON_DATE_RE.search(text)
        return dt(match.group(1)) if match else None
    except requests.RequestException:
        return None


def main():
    data = json.loads(OUT.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("news", data.get("items", []))
    if not isinstance(data, list):
        raise SystemExit("بنية news.json غير صالحة")

    now = datetime.now(timezone.utc)
    seen = set()
    live = 0
    demoted = 0

    for item in data:
        if not isinstance(item, dict):
            continue
        key = str(item.get("event_key") or item.get("id") or "").strip()
        if key and key in seen:
            item["status"] = "archive"
            item["auto_published"] = False
            demoted += 1
            continue
        if key:
            seen.add(key)

        verification = str(item.get("verification") or "developing").strip().lower()
        try:
            score = int(item.get("verification_score") or 0)
        except (TypeError, ValueError):
            score = 0
        evidence = item.get("verification_evidence") if isinstance(item.get("verification_evidence"), list) else []
        primary = sum(1 for e in evidence if isinstance(e, dict) and e.get("type") == "primary")
        independent = sum(1 for e in evidence if isinstance(e, dict) and e.get("type") == "independent")
        published = dt(item.get("published") or item.get("published_at"))
        source_url = item.get("source_url") or (evidence[0].get("url") if evidence and isinstance(evidence[0], dict) else "")
        source_published = source_date(source_url)
        effective_date = source_published or published
        fresh = bool(effective_date and now - effective_date <= timedelta(hours=MAX_LIVE_AGE_HOURS) and effective_date <= now + timedelta(minutes=10))
        title = str(item.get("title") or "")
        years = [int(y) for y in YEAR_RE.findall(title)]
        historical_title = bool(years and max(years) < now.year)

        if source_published:
            item["source_published_at"] = source_published.isoformat()
        if verification == "confirmed" and not (primary >= 1 and independent >= 1 and score >= 80):
            verification = "developing"
            score = min(score if score else 70, 79)
        if verification == "unconfirmed" or not fresh or historical_title:
            item["status"] = "archive" if effective_date else "review"
            item["auto_published"] = False
            item["verification"] = verification
            item["verification_status"] = verification
            demoted += 1
            continue

        item["verification"] = verification
        item["verification_status"] = verification
        item["verification_score"] = max(55 if verification == "developing" else 80, min(score or 70, 100))
        item["verification_evidence_count"] = len(evidence)
        item["status"] = "published"
        item["auto_published"] = True
        item["freshness_hours"] = round((now - effective_date).total_seconds() / 3600, 2)
        live += 1

    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[DONE] quality gate: {live} live, {demoted} demoted")


if __name__ == "__main__":
    main()
