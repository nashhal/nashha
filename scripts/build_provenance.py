#!/usr/bin/env python3
"""Build a deterministic provenance manifest for the Nashhal newsroom dataset."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / "data" / "news.json"
OUT = ROOT / "data" / "provenance.json"


def clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def canonical(item: dict) -> dict[str, str]:
    return {
        "id": clean(item.get("id")),
        "title": clean(item.get("title")),
        "url": clean(item.get("source_url") or item.get("link")),
        "published": clean(item.get("published") or item.get("published_at")),
        "source": clean(item.get("source_name") or item.get("source")),
    }


def main() -> None:
    if not NEWS.exists():
        raise SystemExit(f"missing {NEWS}")
    data = json.loads(NEWS.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("news") or data.get("items") or []
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    rows = []
    for item in items:
        if not isinstance(item, dict) or not clean(item.get("id")):
            continue
        base = canonical(item)
        payload = json.dumps(base, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        rows.append({
            "id": base["id"],
            "title": base["title"],
            "url": base["url"],
            "published": base["published"],
            "source": base["source"] or "غير محدد",
            "captured_at": now,
            "content_hash": hashlib.sha256(payload).hexdigest(),
            "hash_algorithm": "SHA-256",
            "status": "anchored",
            "anchor": {"type": "github-history", "ref": "main"},
        })
    rows.sort(key=lambda x: x["id"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[DONE] provenance manifest: {len(rows)} records")


if __name__ == "__main__":
    main()
