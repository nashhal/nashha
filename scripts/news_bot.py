#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility wrapper: the active news collector is news_bot_v2.py.
This legacy entry point no longer collects media channels or social posts.
"""
import runpy

runpy.run_path("scripts/news_bot_v2.py", run_name="__main__")
