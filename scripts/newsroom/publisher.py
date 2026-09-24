#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent 5: deterministic publication gate and dataset publisher."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from .common import NEWS_PATH, PIPELINE_VERSION, clean, make_id


PRESERVE = (
    "analysis_ar", "background_ar", "what_happened_ar", "why_it_matters_ar",
    "implications_ar", "open_questions_ar", "analysis_level", "analysis_engine",
    "analysis_version", "entities_ar",
)


def load_news() -> list[dict]:
    if not NEWS_PATH.exists():
        return []
    data = json.loads(NEWS_PATH.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("news", data.get("items", []))
    return data if isinstance(data, list) else []


def publish(items: list[dict]) -> dict:
    existing = load_news()
    index: dict[str, dict] = {}

    for item in existing:
        if not isinstance(item, dict):
            continue
        key = clean(item.get("event_key") or item.get("id"))
        if key:
            index[key] = dict(item)

    published = 0
    review = 0
    rejected = 0
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    for item in items:
        if not isinstance(item, dict):
            continue
        key = clean(item.get("event_key")) or clean(item.get("id"))
        if not key:
            continue

        verification = clean(item.get("verification")).lower()
        current = dict(item)
        current["id"] = make_id(key)
        current["event_key"] = key
        current["original_title"] = clean(item.get("source_title"))[:320]
        current["title"] = clean(item.get("title") or item.get("headline"))
        current["summary"] = clean(item.get("summary"))
        current["description"] = clean(item.get("summary"))[:500]
        current["content"] = clean(item.get("content_ar"))
        current["published"] = clean(item.get("published"))
        current["published_at"] = current["published"]
        current["collected_at"] = clean(item.get("collected_at")) or now
        current["updated_at"] = now
        current["source_name"] = clean((item.get("primary_source") or {}).get("name") if isinstance(item.get("primary_source"), dict) else "")
        current["source_url"] = clean((item.get("primary_source") or {}).get("url") if isinstance(item.get("primary_source"), dict) else "")
        current["source"] = current["source_name"]
        current["platform"] = "news"
        current["source_type"] = "event-first"
        current["rewrite_status"] = "original_editorial"
        current["editorial_model"] = current.get("editorial_model") or "xai"
        current["editorial_version"] = PIPELINE_VERSION
        current["pipeline_version"] = PIPELINE_VERSION
        current["pipeline_stages"] = ["collect", "write", "verify", "edit", "publish"]
        current["verification_evidence_count"] = len(current.get("verification_evidence") or [])

        if verification == "confirmed" and current.get("editorial_status") == "ready":
            current["status"] = "published"
            current["auto_published"] = True
            current["confidence"] = "high"
            published += 1
        elif verification == "developing":
            current["status"] = "review"
            current["auto_published"] = False
            current["confidence"] = "medium"
            review += 1
        else:
            current["status"] = "review"
            current["auto_published"] = False
            current["confidence"] = "low"
            rejected += 1

        old = index.get(key, {})
        for field in PRESERVE:
            if not clean(current.get(field)) and old.get(field):
                current[field] = old[field]

        # Preserve any legacy metadata that the new pipeline does not own.
        for field, value in old.items():
            if field not in current and value not in (None, "", [], {}):
                current[field] = value

        index[key] = current

    merged = sorted(
        index.values(),
        key=lambda x: x.get("published_at") or x.get("published") or "",
        reverse=True,
    )
    NEWS_PATH.write_text(
        json.dumps(merged[:180], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    stats = {"published": published, "review": review, "rejected": rejected, "total": len(merged)}
    print(f"[PUBLISHER] {stats}")
    return stats
