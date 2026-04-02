from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .config import (
    DATA_DIR,
    DEFAULT_BRAND,
    DEFAULT_CATEGORY,
    SITE_URL,
    SUPPORTED_CSV_ENCODINGS,
)
from .utils import clean_text, slugify, strip_html


def _read_csv_fallback(csv_path: Path) -> pd.DataFrame:
    last_error: Exception | None = None

    for encoding in SUPPORTED_CSV_ENCODINGS:
        try:
            return pd.read_csv(csv_path, encoding=encoding)
        except Exception as exc:
            last_error = exc

    try:
        return pd.read_csv(csv_path, encoding_errors="ignore")
    except Exception as exc:
        last_error = exc

    raise RuntimeError(f"Could not read CSV file: {csv_path}") from last_error


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    return df


def _make_unique_slug(base_slug: str, seen: set[str]) -> str:
    slug = base_slug
    index = 2
    while slug in seen:
        slug = f"{base_slug}-{index}"
        index += 1
    seen.add(slug)
    return slug


def _build_product(row: dict[str, Any], product_id: int, seen_slugs: set[str]) -> dict[str, Any] | None:
    name = clean_text(row.get("title"))
    sku = clean_text(row.get("part_number"))
    brand = clean_text(row.get("brand")) or DEFAULT_BRAND
    category = clean_text(row.get("category")) or DEFAULT_CATEGORY
    description = strip_html(row.get("body_html"))
    seo_title = clean_text(row.get("seo_title")) or name
    seo_description = clean_text(row.get("seo_description")) or description
    image = clean_text(row.get("image"))
    keywords = clean_text(row.get("keywords"))
    tags = [t.strip() for t in keywords.split(",") if t.strip()]
    canonical_url = clean_text(row.get("canonical_url"))
    product_url = clean_text(row.get("product_url"))
    handle = clean_text(row.get("handle")) or sku or name
    seo_score = clean_text(row.get("seo_score"))

    if not name and not sku and not handle:
        return None

    if not name:
        name = sku or handle or f"Produkt {product_id}"

    if not sku:
        sku = handle or slugify(name)

    mpn = sku
    alt = name
    condition = "Neu / Gebraucht"

    if not description:
        description = f"{name} von {brand}. Angebot und Verfügbarkeit auf Anfrage innerhalb von 24h."

    if not seo_title:
        seo_title = name

    if not seo_description:
        seo_description = description

    base_slug = slugify(f"{brand}-{sku or handle or name}")
    slug = _make_unique_slug(base_slug, seen_slugs)

    url = f"/produkt/{slug}.html"
    if product_url.startswith("/"):
        url = product_url
    elif product_url.startswith("http://") or product_url.startswith("https://"):
        url = f"/produkt/{slug}.html"

    return {
        "id": product_id,
        "name": name,
        "sku": sku,
        "brand": brand,
        "category": category,
        "top_category": category,
        "description": description,
        "seo_title": seo_title,
        "seo_description": seo_description,
        "image": image,
        "tags": tags,
        "condition": condition,
        "mpn": mpn,
        "slug": slug,
        "url": url,
        "canonical_url": canonical_url or f"{SITE_URL}{url}",
        "status": "active",
        "inventory_qty": "",
        "alt": alt,
        "handle": handle,
        "seo_score": seo_score,
    }


def load_products() -> list[dict[str, Any]]:
    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError("No CSV files found in /data")

    products: list[dict[str, Any]] = []
    seen_slugs: set[str] = set()

    for csv_file in csv_files:
        df = _normalize_columns(_read_csv_fallback(csv_file))

        for _, row in df.iterrows():
            product = _build_product(
                row.to_dict(),
                product_id=len(products) + 1,
                seen_slugs=seen_slugs,
            )
            if product is not None:
                products.append(product)

    return products


def group_by(products: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for product in products:
        out.setdefault(product[key], []).append(product)
    return out