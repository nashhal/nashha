#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared utilities for the Nashhal newsroom agents."""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import requests

ROOT = Path(__file__).resolve().parents[2]
NEWS_PATH = ROOT / "data" / "news.json"

MODEL = os.getenv("XAI_MODEL") or "grok-4.5"
REQUEST_TIMEOUT = int(os.getenv("NEWSROOM_TIMEOUT", "120"))
MAX_CANDIDATES = int(os.getenv("NEWSROOM_MAX_CANDIDATES", "8"))
MAX_EVIDENCE = 12
PIPELINE_VERSION = "1.0.0"


def clean(value: object) -> str:
    value = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", value).strip()


def clean_body(value: object) -> str:
    value = re.sub(r"<[^>]+>", "", str(value or ""))
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in value.splitlines()]
    paragraphs = []
    for line in lines:
        if line:
            paragraphs.append(line)
    return "\n\n".join(paragraphs).strip()


def canonical_url(url: object) -> str:
    try:
        p = urlparse(clean(url))
        if p.scheme not in {"http", "https"} or not p.netloc:
            return ""
        path = p.path.rstrip("/")
        return urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", "", ""))
    except Exception:
        return ""


def make_id(seed: object) -> str:
    return hashlib.sha256(clean(seed).encode("utf-8")).hexdigest()[:20]


def make_event_key(title: object, summary: object = "") -> str:
    text = re.sub(
        r"[^\w\u0600-\u06FF ]+",
        " ",
        f"{clean(title)} {clean(summary)}".lower(),
    )
    tokens = [x for x in text.split() if len(x) > 2][:40]
    return hashlib.sha256(" ".join(tokens).encode("utf-8")).hexdigest()[:20]


def response_text(data: dict) -> str:
    parts: list[str] = []
    for output in data.get("output", []):
        if output.get("type") != "message":
            continue
        for content in output.get("content", []):
            if content.get("type") == "output_text":
                parts.append(str(content.get("text", "")))
    return "\n".join(parts).strip()


def extract_json(text_value: str, expected: str = "object"):
    text_value = str(text_value or "").strip()
    try:
        return json.loads(text_value)
    except json.JSONDecodeError:
        pass

    if expected == "array":
        match = re.search(r"\[[\s\S]*\]", text_value)
    else:
        match = re.search(r"\{[\s\S]*\}", text_value)
    if not match:
        raise ValueError("لم يتم العثور على JSON صالح في استجابة النموذج")
    return json.loads(match.group(0))


def citations_from(data: dict) -> set[str]:
    return {canonical_url(x) for x in data.get("citations", []) if canonical_url(x)}


def xai_responses(*, prompt: str, tools: list[dict] | None = None, from_date: str | None = None, to_date: str | None = None) -> tuple[str, set[str]]:
    token = os.getenv("XAI_API_KEY")
    if not token:
        raise RuntimeError("XAI_API_KEY غير مضبوط")

    payload: dict = {
        "model": MODEL,
        "input": [{"role": "user", "content": prompt}],
        "include": ["no_inline_citations"],
    }
    if tools:
        payload["tools"] = tools

    if from_date or to_date:
        payload["tools"] = list(payload.get("tools", []))
        for tool in payload["tools"]:
            if tool.get("type") == "x_search":
                if from_date:
                    tool["from_date"] = from_date
                if to_date:
                    tool["to_date"] = to_date

    response = requests.post(
        "https://api.x.ai/v1/responses",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    if not response.ok:
        detail = ""
        try:
            detail = response.text[:1000]
        except Exception:
            pass
        raise RuntimeError(f"xAI API HTTP {response.status_code}: {detail}")

    data = response.json()
    return response_text(data), citations_from(data)


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
