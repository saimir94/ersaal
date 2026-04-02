from __future__ import annotations

import html
import re
from typing import Any

import pandas as pd


def slugify(value: str) -> str:
    value = str(value or "").strip().lower()
    replacements = {
        "&": " und ",
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "item"


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def strip_html(value: str) -> str:
    value = clean_text(value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def html_escape(value: Any) -> str:
    return html.escape(clean_text(value), quote=True)


def meta_desc(text: str, max_len: int = 158) -> str:
    text = strip_html(text)
    if len(text) <= max_len:
        return text
    shortened = text[: max_len - 1]
    if " " in shortened:
        shortened = shortened.rsplit(" ", 1)[0]
    return shortened + "…"


def rel_path(depth: int) -> str:
    return "../" * depth


def href_for(depth: int, url: str) -> str:
    return f"{rel_path(depth)}{url.lstrip('/')}"


def chunked(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out