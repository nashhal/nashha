#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final invariant checks for newsroom output before GitHub Pages publication."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
NEWS = ROOT / "data" / "news.json"


def valid_url(value: object) -> bool:
    try:
        p = urlparse(str(value or ""))
        return p.scheme in {"http", "https"} and bool(p.netloc)
    except Exception:
        return False


def main() -> None:
    data = json.loads(NEWS.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("news", data.get("items", []))
    if not isinstance(data, list):
        raise SystemExit("news.json must be a list")

    errors: list[str] = []
    seen: set[str] = set()

    for item in data:
        if not isinstance(item, dict):
            errors.append("وجد عنصر غير صالح داخل news.json")
            continue

        key = str(item.get("event_key") or item.get("id") or "").strip()
        if key in seen:
            errors.append(f"تكرار event_key: {key}")
        if key:
            seen.add(key)

        status = str(item.get("status") or "").strip().lower()
        verification = str(item.get("verification") or "").strip().lower()
        auto = bool(item.get("auto_published"))
        evidence = item.get("verification_evidence") if isinstance(item.get("verification_evidence"), list) else []

        if auto:
            if status != "published":
                errors.append(f"auto_published لكن الحالة ليست published: {key}")
            if verification != "confirmed":
                errors.append(f"خبر منشور آليًا دون confirmed: {key}")
            try:
                score = int(item.get("verification_score") or 0)
            except (TypeError, ValueError):
                score = 0
            if score < 80:
                errors.append(f"درجة تحقق أقل من 80 لخبر منشور: {key}")
            primary = sum(1 for e in evidence if isinstance(e, dict) and e.get("type") == "primary")
            independent = sum(1 for e in evidence if isinstance(e, dict) and e.get("type") == "independent")
            if primary < 1 or independent < 1:
                errors.append(f"الأدلة غير كافية لخبر منشور: {key}")

        if status == "published":
            for field in ("title", "summary", "content", "source_url"):
                if not str(item.get(field) or "").strip():
                    errors.append(f"حقل إلزامي مفقود {field}: {key}")
            if not valid_url(item.get("source_url")):
                errors.append(f"source_url غير صالح: {key}")

        if verification == "unconfirmed" and auto:
            errors.append(f"unconfirmed لا يجوز نشره آليًا: {key}")

    if errors:
        print("[SELF-CHECK] FAILED")
        for error in errors[:40]:
            print(f" - {error}")
        raise SystemExit(1)

    published = sum(1 for x in data if isinstance(x, dict) and x.get("status") == "published")
    print(f"[SELF-CHECK] OK · records={len(data)} · published={published}")


if __name__ == "__main__":
    main()
