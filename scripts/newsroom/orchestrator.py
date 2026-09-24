#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nashhal Newsroom Engine: collect -> write -> verify -> edit -> publish."""
from __future__ import annotations

import sys

from .collector import discover
from .editor import edit
from .publisher import publish
from .verifier import verify
from .writer import write


def main() -> int:
    print("[NEWSROOM] بدء دورة غرفة أخبار نشهل")
    candidates = discover()
    if not candidates:
        print("[NEWSROOM] لا توجد مواد جديدة صالحة للجمع في هذه الدورة")
        return 0

    drafts = write(candidates)
    if not drafts:
        raise RuntimeError("فشل روبوت الكتابة في إنتاج أي مسودة صالحة")

    verified = verify(drafts)
    if not verified:
        raise RuntimeError("فشل روبوت التحقق في إنتاج نتائج تحقق")

    edited = edit(verified)
    if not edited:
        raise RuntimeError("لم ينتج روبوت التحرير أي مادة")

    stats = publish(edited)
    print(f"[NEWSROOM] اكتملت الدورة: {stats}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[NEWSROOM][FATAL] {exc}")
        sys.exit(1)
