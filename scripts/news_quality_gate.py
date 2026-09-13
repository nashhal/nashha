#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quality gate: prevent stale, weakly verified or malformed stories from the live feed."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "news.json"
MAX_LIVE_AGE_HOURS = 72


def dt(value):
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        x = datetime.fromisoformat(text)
        return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
    except ValueError:
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
        score = int(item.get("verification_score") or 0)
        evidence = item.get("verification_evidence") if isinstance(item.get("verification_evidence"), list) else []
        primary = sum(1 for e in evidence if isinstance(e, dict) and e.get("type") == "primary")
        independent = sum(1 for e in evidence if isinstance(e, dict) and e.get("type") == "independent")
        published = dt(item.get("published") or item.get("published_at"))
        fresh = bool(published and now - published <= timedelta(hours=MAX_LIVE_AGE_HOURS) and published <= now + timedelta(minutes=10))

        if verification == "confirmed" and not (primary >= 1 and independent >= 1 and score >= 80):
            verification = "developing"
            score = min(score if score else 70, 79)
        if verification == "unconfirmed" or not fresh:
            item["status"] = "archive" if fresh is False and published else "review"
            item["auto_published"] = False
            demoted += 1
            continue

        item["verification"] = verification
        item["verification_status"] = verification
        item["verification_score"] = max(55 if verification == "developing" else 80, min(score or 70, 100))
        item["verification_evidence_count"] = len(evidence)
        item["status"] = "published"
        item["auto_published"] = True
        live += 1

    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[DONE] quality gate: {live} live, {demoted} demoted")


if __name__ == "__main__":
    main()
