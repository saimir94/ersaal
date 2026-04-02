from __future__ import annotations

import json
from typing import Any

from .config import DEFAULT_FORM_ENDPOINT, SITE_NAME, SITE_TAGLINE, SITE_URL
from .utils import html_escape, href_for, meta_desc, rel_path, slugify


def page_title(title: str) -> str:
    return f"{title} | {SITE_NAME} {SITE_TAGLINE}"


def render_head(
    title: str,
    description: str,
    canonical: str,
    depth: int,
    extra_meta: str = "",
    json_ld: str = "",
) -> str:
    root = rel_path(depth)
    canonical_full = canonical if canonical.startswith(("http://", "https://")) else f"{SITE_URL}{canonical}"

    return f"""<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html_escape(title)}</title>
  <meta name="description" content="{html_escape(description)}">
  <link rel="canonical" href="{html_escape(canonical_full)}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{html_escape(SITE_NAME)}">
  <meta property="og:title" content="{html_escape(title)}">
  <meta property="og:description" content="{html_escape(description)}">
  <meta property="og:url" content="{html_escape(canonical_full)}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="stylesheet" href="{root}assets/css/styles.css">
  <script defer src="{root}assets/js/site.js"></script>
  <script defer src="{root}assets/js/search.js"></script>
  {extra_meta}
  {json_ld}
</head>"""


def nav(depth: int) -> str:
    root = rel_path(depth)
    return f"""<header class="site-header">
  <div class="container nav-shell">
    <a class="brand" href="{root}index.html" aria-label="{html_escape(SITE_NAME)} Startseite">
      <span class="brand-mark">⚙</span>
      <span class="brand-text">
        <strong>{html_escape(SITE_NAME)}</strong>
        <small>{html_escape(SITE_TAGLINE.upper())}</small>
      </span>
    </a>
    <button class="nav-toggle" aria-label="Menü öffnen" data-nav-toggle>☰</button>
    <nav class="main-nav" data-nav>
      <a href="{root}index.html">Home</a>
      <a href="{root}produkte/index.html">Alle Produkte</a>
      <a href="{root}marken/index.html">Marken</a>
      <a href="{root}kategorien/index.html">Kategorien</a>
      <a href="{root}kontakt/index.html">Kontakt</a>
      <a href="{root}ueber-uns/index.html">Über Uns</a>
    </nav>
  </div>
</header>"""


def footer(depth: int) -> str:
    root = rel_path(depth)
    return f"""<footer class="site-footer">
  <div class="container footer-grid">
    <div>
      <div class="footer-brand">{html_escape(SITE_NAME)}</div>
      <p>Industrielle Komponenten, Ersatzteile und technische Beschaffung für internationale B2B-Kunden.</p>
    </div>
    <div>
      <h3>Navigation</h3>
      <a href="{root}produkte/index.html">Produkte</a>
      <a href="{root}marken/index.html">Marken</a>
      <a href="{root}kategorien/index.html">Kategorien</a>
    </div>
    <div>
      <h3>Kontakt</h3>
      <a href="mailto:verkauf@ersaal.de">verkauf@ersaal.de</a>
      <a href="{root}kontakt/index.html">Angebot anfragen</a>
    </div>
  </div>
  <div class="container footer-bottom">
    <span>© {html_escape(SITE_NAME)}. Alle Rechte vorbehalten.</span>
    <a href="{root}sitemap.xml">Sitemap</a>
  </div>
</footer>"""


def page_shell(
    title: str,
    description: str,
    canonical: str,
    body: str,
    depth: int = 0,
    extra_meta: str = "",
    json_ld: str = "",
) -> str:
    return f"""<!doctype html>
<html lang="de">
{render_head(title, description, canonical, depth, extra_meta, json_ld)}
<body>
{nav(depth)}
{body}
{footer(depth)}
</body>
</html>"""


def search_bar(depth: int) -> str:
    root = rel_path(depth)
    return f"""<section class="search-strip">
  <div class="container">
    <form class="search-form" action="{root}suche/index.html" method="get">
      <input type="search" name="q" placeholder="Artikelnummer, Marke oder Produkt suchen" aria-label="Produkte suchen" autocomplete="off" data-search-input>
      <button type="submit" class="btn btn-primary">Suchen</button>
      <div class="search-suggestions" data-search-suggestions></div>
    </form>
  </div>
</section>"""


def image_src(product: dict[str, Any], depth: int) -> str:
    if product["image"]:
        return html_escape(product["image"])
    return f"{rel_path(depth)}assets/img/product-placeholder.svg"


def product_card(product: dict[str, Any], depth: int = 0) -> str:
    href = href_for(depth, product["url"])
    image = image_src(product, depth)
    return f"""<article class="product-card">
  <a class="product-card__image" href="{href}">
    <img src="{image}" alt="{html_escape(product['alt'])}" loading="lazy">
  </a>
  <div class="product-card__body">
    <div class="eyebrow">{html_escape(product['brand'])}</div>
    <h3><a href="{href}">{html_escape(product['name'])}</a></h3>
    <p class="sku">SKU: {html_escape(product['sku'])}</p>
    <div class="product-card__actions">
      <a class="btn btn-primary" href="{href}#quote-form">Angebot anfordern</a>
      <a class="text-link" href="{href}">Weiterlesen »</a>
    </div>
  </div>
</article>"""


def make_product_jsonld(product: dict[str, Any]) -> str:
    page_url = f"{SITE_URL}{product['url']}"
    data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product["name"],
        "sku": product["sku"],
        "mpn": product["mpn"],
        "brand": {"@type": "Brand", "name": product["brand"]},
        "category": product["category"],
        "description": meta_desc(product["seo_description"], 300),
        "url": page_url,
        "image": [product["image"]] if product["image"] else [],
        "offers": {
            "@type": "Offer",
            "url": page_url,
            "priceCurrency": "EUR",
            "availability": "https://schema.org/LimitedAvailability",
            "priceSpecification": {
                "@type": "PriceSpecification",
                "priceCurrency": "EUR",
            },
            "seller": {
                "@type": "Organization",
                "name": SITE_NAME,
            },
        },
    }
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "Produkte", "item": SITE_URL + "/produkte/index.html"},
            {"@type": "ListItem", "position": 3, "name": product["brand"], "item": SITE_URL + f"/marke/{slugify(product['brand'])}/index.html"},
            {"@type": "ListItem", "position": 4, "name": product["name"], "item": page_url},
        ],
    }
    return f'<script type="application/ld+json">{json.dumps([data, breadcrumb], ensure_ascii=False)}</script>'


def make_pagination(current: int, total: int) -> str:
    if total <= 1:
        return ""

    links: list[str] = []
    for page in range(1, total + 1):
        href = "index.html" if page == 1 else f"page/{page}/index.html"
        cls = ' class="active"' if page == current else ""
        links.append(f"<a{cls} href=\"{href}\">{page}</a>")

    return '<nav class="pagination">' + "".join(links) + "</nav>"


def home_page(products: list[dict[str, Any]], brands: dict[str, list[dict[str, Any]]], categories: dict[str, list[dict[str, Any]]]) -> str:
    featured = products[:6]

    categories_html = "".join(
        f"""<article class="category-card">
  <div class="category-card__media">
    <img src="{html_escape(items[0]['image'] or 'assets/img/product-placeholder.svg')}" alt="{html_escape(name)}" loading="lazy">
  </div>
  <div class="category-card__body">
    <h3>{html_escape(name)}</h3>
    <p>Leistungsstarke und zuverlässige Lösungen für präzise industrielle Anwendungen und Beschaffung.</p>
    <a class="btn btn-primary" href="kategorie/{slugify(name)}/index.html">Komponenten entdecken</a>
  </div>
</article>"""
        for name, items in list(categories.items())[:6]
    )

    featured_html = "".join(product_card(p, depth=0) for p in featured)
    brand_html = "".join(
        f'<a class="pill" href="marke/{slugify(name)}/index.html">{html_escape(name)} <span>{len(items)}</span></a>'
        for name, items in list(brands.items())[:18]
    )

    body = f"""
<main>
  <section class="hero hero--home">
    <div class="hero-media"></div>
    <div class="container hero-content">
      <p class="eyebrow eyebrow-light">Entdecken Sie hochwertige Industriekomponenten und technische Lösungen.</p>
      <h1>Technische Lösungen für höchste Ansprüche</h1>
      <p class="lead lead-light">Skalierbarer B2B-Katalog für industrielle Ersatzteile, Automatisierungskomponenten und technische Beschaffung – optimiert für Performance, SEO und internationale Anfragen.</p>
      <div class="cta-row">
        <a class="btn btn-primary" href="produkte/index.html">Mehr erfahren</a>
        <a class="btn btn-ghost" href="kontakt/index.html">Kontakt aufnehmen</a>
      </div>
    </div>
  </section>

  {search_bar(0)}

  <section class="section">
    <div class="container narrow-center">
      <div class="eyebrow">Industriekomponenten</div>
      <h2>Leistungsstarke Steuerung für industrielle Anwendungen</h2>
      <p class="lead">Moderne Steuerungs- und Automatisierungskomponenten für zuverlässige industrielle Systeme. Entwickelt für stabile Leistung, hohe Präzision und den professionellen Einsatz in Produktion und Anlagensteuerung.</p>
      <ul class="bullet-list centered">
        <li>Präzise Steuerung industrieller Prozesse</li>
        <li>Geeignet für Produktion und Anlagensteuerung</li>
        <li>Zuverlässige Leistung im Dauerbetrieb</li>
        <li>Kompatibel mit modernen Automatisierungssystemen</li>
      </ul>
      <a class="btn btn-primary" href="produkte/index.html">Komponenten entdecken</a>
    </div>
  </section>

  <section class="section section-alt">
    <div class="container">
      <div class="section-head">
        <div>
          <div class="eyebrow">Sortiment</div>
          <h2>Kategorien für industrielle Beschaffung</h2>
        </div>
      </div>
      <div class="category-grid">{categories_html}</div>
    </div>
  </section>

  <section class="section">
    <div class="container">
      <div class="section-head">
        <div>
          <div class="eyebrow">Produkte</div>
          <h2>Ausgewählte Produkte</h2>
        </div>
        <a class="text-link" href="produkte/index.html">Alle Produkte anzeigen</a>
      </div>
      <div class="product-grid">{featured_html}</div>
    </div>
  </section>

  <section class="section section-alt">
    <div class="container">
      <div class="section-head">
        <div>
          <div class="eyebrow">Marken</div>
          <h2>Hersteller im Katalog</h2>
        </div>
      </div>
      <div class="pill-row">{brand_html}</div>
    </div>
  </section>
</main>
"""
    json_ld = '<script type="application/ld+json">' + json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": SITE_NAME,
            "url": SITE_URL,
            "potentialAction": {
                "@type": "SearchAction",
                "target": f"{SITE_URL}/suche/index.html?q={{search_term_string}}",
                "query-input": "required name=search_term_string",
            },
        },
        ensure_ascii=False,
    ) + "</script>"

    return page_shell(
        page_title("Industriekomponenten & technische Beschaffung"),
        meta_desc("Skalierbarer B2B-Katalog für industrielle Komponenten, Ersatzteile und Angebotsanfragen."),
        "/index.html",
        body,
        depth=0,
        json_ld=json_ld,
    )


def simple_page(filename: str, title: str, text: str, depth: int = 1) -> str:
    body = f"""<main>
  <section class="page-hero">
    <div class="container">
      <div class="eyebrow">{html_escape(SITE_NAME)}</div>
      <h1>{html_escape(title)}</h1>
      <p class="lead">{html_escape(text)}</p>
    </div>
  </section>
</main>"""
    return page_shell(
        page_title(title),
        meta_desc(text),
        f"/{filename}/index.html",
        body,
        depth=depth,
    )


def brand_index_page(brands: dict[str, list[dict[str, Any]]]) -> str:
    cards = "".join(
        f"""<article class="simple-card">
  <h2><a href="../marke/{slugify(name)}/index.html">{html_escape(name)}</a></h2>
  <p>{len(items)} Produkte</p>
  <a class="text-link" href="../marke/{slugify(name)}/index.html">Zur Marke »</a>
</article>"""
        for name, items in brands.items()
    )
    body = f"""<main>
  <section class="page-hero">
    <div class="container">
      <div class="eyebrow">Marken</div>
      <h1>Marken im Katalog</h1>
      <p class="lead">Herstellerseiten mit indexierten Produktlisten und SEO-freundlichen Landingpages.</p>
    </div>
  </section>
  <section class="section section-alt">
    <div class="container simple-grid">{cards}</div>
  </section>
</main>"""
    return page_shell(
        page_title("Marken"),
        meta_desc("Herstellerseiten für den gesamten Produktkatalog."),
        "/marken/index.html",
        body,
        depth=1,
    )


def category_index_page(categories: dict[str, list[dict[str, Any]]]) -> str:
    cards = "".join(
        f"""<article class="simple-card">
  <h2><a href="../kategorie/{slugify(name)}/index.html">{html_escape(name)}</a></h2>
  <p>{len(items)} Produkte</p>
  <a class="text-link" href="../kategorie/{slugify(name)}/index.html">Zur Kategorie »</a>
</article>"""
        for name, items in categories.items()
    )
    body = f"""<main>
  <section class="page-hero">
    <div class="container">
      <div class="eyebrow">Kategorien</div>
      <h1>Kategorien im Katalog</h1>
      <p class="lead">Kategorieseiten mit sauberer interner Verlinkung und schneller Navigation.</p>
    </div>
  </section>
  <section class="section section-alt">
    <div class="container simple-grid">{cards}</div>
  </section>
</main>"""
    return page_shell(
        page_title("Kategorien"),
        meta_desc("Kategorieseiten für Industriekomponenten."),
        "/kategorien/index.html",
        body,
        depth=1,
    )


def search_page() -> str:
    body = """<main>
  <section class="page-hero">
    <div class="container">
      <div class="eyebrow">Suche</div>
      <h1>Produkte durchsuchen</h1>
      <p class="lead">Schnelle Suche nach Artikelnummern, Marken und Produktnamen.</p>
    </div>
  </section>
  <section class="section">
    <div class="container">
      <form class="search-form search-form--wide" action="" method="get">
        <input type="search" name="q" placeholder="z. B. ZXH9999-0052" data-search-page-input>
        <button class="btn btn-primary" type="submit">Suchen</button>
      </form>
      <div id="search-results" class="search-results"></div>
    </div>
  </section>
</main>"""
    return page_shell(
        page_title("Suche"),
        meta_desc("Produktsuche im Industriekatalog."),
        "/suche/index.html",
        body,
        depth=1,
    )


def listing_page(
    title: str,
    intro: str,
    items: list[dict[str, Any]],
    canonical: str,
    depth: int,
    current_page: int,
    total_pages: int,
    hero_title: str | None = None,
) -> str:
    cards = "".join(product_card(item, depth=depth) for item in items)
    pagination = make_pagination(current_page, total_pages)
    body = f"""
<main>
  <section class="page-hero">
    <div class="container">
      <div class="eyebrow">Industriekomponenten</div>
      <h1>{html_escape(hero_title or title)}</h1>
      <p class="lead">{html_escape(intro)}</p>
    </div>
  </section>
  {search_bar(depth)}
  <section class="section section-alt">
    <div class="container">
      <div class="product-grid">{cards}</div>
      {pagination}
    </div>
  </section>
</main>
"""
    page_suffix = f" – Seite {current_page}" if current_page > 1 else ""
    return page_shell(
        page_title(title + page_suffix),
        meta_desc(intro),
        canonical,
        body,
        depth=depth,
    )


def product_page(product: dict[str, Any], related: list[dict[str, Any]]) -> str:
    desc = meta_desc(product["seo_description"] or product["description"])
    related_html = "".join(product_card(item, depth=1) for item in related[:3])
    image = html_escape(product["image"]) if product["image"] else "../assets/img/product-placeholder.svg"
    brand_link = f"../marke/{slugify(product['brand'])}/index.html"

    body = f"""
<main>
  <section class="hero hero--product">
    <div class="container hero-grid product-grid-top">
      <div class="product-image-panel">
        <img src="{image}" alt="{html_escape(product['alt'])}" loading="eager">
      </div>
      <div class="product-summary">
        <div class="eyebrow">{html_escape(product['brand'])} · {html_escape(product['category'])}</div>
        <h1>{html_escape(product['name'])}</h1>
        <p class="lead">{html_escape(desc)}</p>
        <ul class="bullet-list compact">
          <li>Schnelle Lieferung weltweit</li>
          <li>Geprüfte Industriequalität</li>
          <li>Persönlicher technischer Support</li>
          <li>Versand erfolgt aus Deutschland</li>
        </ul>
        <div class="cta-row">
          <a class="btn btn-dark" href="#quote-form">Jetzt Angebot anfragen</a>
          <span class="fine-print">Hinweis: {html_escape(SITE_NAME)} ist kein autorisierter Distributor für {html_escape(product['brand'])}.</span>
        </div>
      </div>
    </div>
  </section>

  <section class="section section-tight">
    <div class="container breadcrumbs">
      <a href="../index.html">Home</a> /
      <a href="../produkte/index.html">Produkte</a> /
      <a href="{brand_link}">{html_escape(product['brand'])}</a> /
      <span>{html_escape(product['sku'])}</span>
    </div>
  </section>

  <section class="section">
    <div class="container two-col-layout">
      <div>
        <h2>Produktinformationen zu {html_escape(product['name'])}</h2>
        <div class="accordion" data-accordion>
          <div class="accordion-item is-open">
            <button class="accordion-trigger" type="button">Warum bei {html_escape(SITE_NAME)} anfragen?</button>
            <div class="accordion-panel">
              <p>{html_escape(product['description'])}</p>
            </div>
          </div>
          <div class="accordion-item">
            <button class="accordion-trigger" type="button">Verfügbarkeit & Lieferung</button>
            <div class="accordion-panel">
              <p>Preis und Verfügbarkeit erhalten Sie auf Anfrage. Für kritische Ersatzteile priorisieren wir Express-Beschaffung und transparente Rückmeldung.</p>
            </div>
          </div>
          <div class="accordion-item">
            <button class="accordion-trigger" type="button">Technische Eckdaten</button>
            <div class="accordion-panel">
              <table class="spec-table">
                <tr><th>Hersteller</th><td>{html_escape(product['brand'])}</td></tr>
                <tr><th>Artikel</th><td>{html_escape(product['name'])}</td></tr>
                <tr><th>SKU / MPN</th><td>{html_escape(product['sku'])}</td></tr>
                <tr><th>Kategorie</th><td>{html_escape(product['category'])}</td></tr>
                <tr><th>Zustand</th><td>{html_escape(product['condition'])}</td></tr>
              </table>
            </div>
          </div>
          <div class="accordion-item">
            <button class="accordion-trigger" type="button">FAQ zur Angebotsanfrage</button>
            <div class="accordion-panel">
              <p>Nutzen Sie das Formular, um Mengen, Lieferanforderungen, alternative Teilenummern oder technische Rückfragen zu übermitteln. Unser Vertrieb antwortet in der Regel innerhalb von 24 Stunden.</p>
            </div>
          </div>
        </div>
      </div>
      <aside>
        <form id="quote-form" class="quote-form" method="POST" action="{DEFAULT_FORM_ENDPOINT}">
          <h2>Angebot für {html_escape(product['sku'])} anfordern</h2>
          <p class="form-intro">Übermitteln Sie Ihre Anfrage. Unser Vertriebsteam meldet sich zeitnah mit Preis- und Verfügbarkeitsinformationen.</p>
          <div class="product-mini-specs">
            <div><span>Produkt</span><strong>{html_escape(product['name'])}</strong></div>
            <div><span>Hersteller</span><strong>{html_escape(product['brand'])}</strong></div>
            <div><span>Modell</span><strong>{html_escape(product['sku'])}</strong></div>
          </div>
          <input type="hidden" name="product_name" value="{html_escape(product['name'])}">
          <input type="hidden" name="product_sku" value="{html_escape(product['sku'])}">
          <input type="hidden" name="product_url" value="{SITE_URL}{product['url']}">
          <div class="form-grid">
            <label>Menge *<input name="quantity" required placeholder="z. B. 5"></label>
            <label>Zustand<select name="condition"><option>Bitte wählen</option><option>Neu</option><option>Gebraucht</option><option>Refurbished</option></select></label>
            <label>Alternative Part Number<input name="alternative_part_number"></label>
            <label>Firma *<input name="company" required></label>
            <label>Ansprechpartner *<input name="customer_name" required></label>
            <label>Geschäftliche E-Mail *<input type="email" name="email" required></label>
            <label>Telefon<input name="phone"></label>
            <label>Land<input name="country"></label>
            <label class="full">Nachricht<textarea name="message" rows="5" placeholder="Bitte nennen Sie z. B. Zielpreis, Lieferanforderungen oder technische Hinweise."></textarea></label>
            <label class="checkbox full"><input type="checkbox" required> <span>Ich stimme zu, dass meine Daten zur Bearbeitung meiner Angebotsanfrage verarbeitet werden.</span></label>
            <button class="btn btn-primary full" type="submit">Angebot anfordern</button>
          </div>
        </form>
      </aside>
    </div>
  </section>

  <section class="section section-alt">
    <div class="container">
      <div class="section-head">
        <div>
          <div class="eyebrow">Passende Produkte</div>
          <h2>Weitere Komponenten von {html_escape(product['brand'])}</h2>
        </div>
        <a class="text-link" href="{brand_link}">Alle {html_escape(product['brand'])}-Produkte</a>
      </div>
      <div class="product-grid">{related_html}</div>
    </div>
  </section>
</main>
"""
    return page_shell(
        page_title(product["seo_title"]),
        desc,
        product["url"],
        body,
        depth=1,
        json_ld=make_product_jsonld(product),
    )