from __future__ import annotations

import math
import shutil
from pathlib import Path

from .assets import write_assets
from .config import DIST, PRODUCTS_PER_PAGE, SEARCH_LOCAL_THRESHOLD
from .loader import group_by, load_products
from .renderer import (
    brand_index_page,
    category_index_page,
    home_page,
    listing_page,
    product_page,
    search_page,
    simple_page,
)
from .utils import slugify, unique_preserve_order


def _reset_dist() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True, exist_ok=True)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_product_pages(products: list[dict]) -> list[str]:
    urls: list[str] = []

    for product in products:
        related = [p for p in products if p["brand"] == product["brand"] and p["slug"] != product["slug"]]
        out = DIST / "produkt" / f"{product['slug']}.html"
        _write_text(out, product_page(product, related))
        urls.append(product["url"])

    return urls


def _write_listing_pages(
    title: str,
    intro: str,
    items: list[dict],
    out_dir: Path,
    canonical_base: str,
    depth: int,
    hero_title: str | None = None,
) -> list[str]:
    urls: list[str] = []
    if not items:
        return urls

    total_pages = math.ceil(len(items) / PRODUCTS_PER_PAGE)

    for page_num in range(1, total_pages + 1):
        start = (page_num - 1) * PRODUCTS_PER_PAGE
        subset = items[start:start + PRODUCTS_PER_PAGE]

        canonical = canonical_base if page_num == 1 else canonical_base.replace("/index.html", f"/page/{page_num}/index.html")
        target = out_dir / ("index.html" if page_num == 1 else f"page/{page_num}/index.html")

        html = listing_page(
            title=title,
            intro=intro,
            items=subset,
            canonical=canonical,
            depth=depth,
            current_page=page_num,
            total_pages=total_pages,
            hero_title=hero_title,
        )
        _write_text(target, html)
        urls.append(canonical)

    return urls


def _write_indexes_and_taxonomies(products: list[dict], brands: dict[str, list[dict]], categories: dict[str, list[dict]]) -> list[str]:
    urls: list[str] = []

    _write_text(DIST / "index.html", home_page(products, brands, categories))
    urls.append("/index.html")

    _write_text(DIST / "marken" / "index.html", brand_index_page(brands))
    urls.append("/marken/index.html")

    _write_text(DIST / "kategorien" / "index.html", category_index_page(categories))
    urls.append("/kategorien/index.html")

    _write_text(DIST / "suche" / "index.html", search_page())
    urls.append("/suche/index.html")

    _write_text(
        DIST / "kontakt" / "index.html",
        simple_page("kontakt", "Kontakt", "Senden Sie uns Ihre Anfrage für Industriekomponenten, Ersatzteile und technische Beschaffung."),
    )
    urls.append("/kontakt/index.html")

    _write_text(
        DIST / "ueber-uns" / "index.html",
        simple_page("ueber-uns", "Über Uns", "ERSAAL unterstützt internationale B2B-Kunden mit technischer Beschaffung und zuverlässiger Ersatzteilversorgung."),
    )
    urls.append("/ueber-uns/index.html")

    urls.extend(
        _write_listing_pages(
            title="Alle Produkte",
            intro="Gesamter Produktkatalog mit indexierten Produktdetailseiten, schnellen Filterwegen und sauberer interner Verlinkung.",
            items=products,
            out_dir=DIST / "produkte",
            canonical_base="/produkte/index.html",
            depth=1,
            hero_title="Alle Produkte",
        )
    )

    for brand, items in brands.items():
        urls.extend(
            _write_listing_pages(
                title=f"{brand} Produkte",
                intro=f"Produkte und Komponenten von {brand} im ERSAAL Katalog.",
                items=items,
                out_dir=DIST / "marke" / slugify(brand),
                canonical_base=f"/marke/{slugify(brand)}/index.html",
                depth=2,
                hero_title=f"{brand} Produkte",
            )
        )

    for category, items in categories.items():
        urls.extend(
            _write_listing_pages(
                title=f"{category}",
                intro=f"Industriekomponenten in der Kategorie {category}.",
                items=items,
                out_dir=DIST / "kategorie" / slugify(category),
                canonical_base=f"/kategorie/{slugify(category)}/index.html",
                depth=2,
                hero_title=category,
            )
        )

    return urls


def _write_sitemap(urls: list[str]) -> None:
    unique_urls = unique_preserve_order(urls)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for url in unique_urls:
        lines.append(f"  <url><loc>https://www.ersaal.de{url}</loc></url>")
    lines.append("</urlset>")

    _write_text(DIST / "sitemap.xml", "\n".join(lines))
    _write_text(DIST / "robots.txt", "User-agent: *\nAllow: /\nSitemap: https://www.ersaal.de/sitemap.xml\n")


def _write_readme(products_count: int, brands_count: int, categories_count: int, local_search: bool) -> None:
    content = f"""# ERSAAL Static Catalog

Production-ready static B2B quote-request catalog generated from CSV files.

## Build
python build.py

## Search mode
{"local JSON index" if local_search else "external search recommended"}

## Dataset summary
Products: {products_count}
Brands: {brands_count}
Categories: {categories_count}
"""
    _write_text(DIST / "BUILD-INFO.txt", content)


def build_site() -> None:
    print("Starting build...")
    _reset_dist()

    products = load_products()
    brands = group_by(products, "brand")
    categories = group_by(products, "category")

    local_search = len(products) < SEARCH_LOCAL_THRESHOLD

    write_assets(local_search=local_search, products=products)

    urls: list[str] = []
    urls.extend(_write_product_pages(products))
    urls.extend(_write_indexes_and_taxonomies(products, brands, categories))

    _write_sitemap(urls)
    _write_readme(len(products), len(brands), len(categories), local_search)

    print(f"Build completed: {len(products)} products")