from __future__ import annotations
import csv, html, json, math, os, re, shutil, textwrap
from pathlib import Path
from urllib.parse import quote
import pandas as pd

BASE_DIR = Path(__file__).parent
DIST = BASE_DIR / 'dist'
ASSETS = DIST / 'assets'
CSS_DIR = ASSETS / 'css'
JS_DIR = ASSETS / 'js'
IMG_DIR = ASSETS / 'img'
DATA_DIR = BASE_DIR / 'data'

SITE_URL = 'https://www.ersaal.de'
SITE_NAME = 'ERSAAL'
DEFAULT_FORM_ENDPOINT = 'https://formspree.io/f/your-form-id'
PRODUCTS_PER_PAGE = 24
SEARCH_LOCAL_THRESHOLD = 20000


def slugify(value: str) -> str:
    value = str(value or '').strip().lower()
    value = value.replace('&', ' und ')
    value = value.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
    value = re.sub(r'[^a-z0-9]+', '-', value)
    return re.sub(r'-{2,}', '-', value).strip('-') or 'item'


def clean_text(value) -> str:
    if value is None:
        return ''
    try:
        if pd.isna(value):
            return ''
    except Exception:
        pass
    s = str(value)
    s = s.replace('\u00a0', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def strip_html(value: str) -> str:
    value = clean_text(value)
    value = re.sub(r'<[^>]+>', ' ', value)
    value = html.unescape(value)
    value = re.sub(r'\s+', ' ', value).strip()
    return value


def ensure_dirs():
    if BASE_DIR.exists():
        shutil.rmtree(BASE_DIR)
    for p in [DIST, CSS_DIR, JS_DIR, IMG_DIR, DATA_DIR]:
        p.mkdir(parents=True, exist_ok=True)


def page_title(title: str) -> str:
    return f"{title} | {SITE_NAME} Industrie- und Technikhandel"


def meta_desc(text: str, max_len: int = 158) -> str:
    text = strip_html(text)
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rsplit(' ', 1)[0] + '…'


def load_products() -> list[dict]:
    import io

    products = []
    seen = set()

    csv_files = sorted(DATA_DIR.glob('*.csv'))

    if not csv_files:
        raise FileNotFoundError('No CSV files found in /data')

    for csv_file in csv_files:
        raw = csv_file.read_bytes()

        raw = (
            raw.replace(bytes([129]), 'ü'.encode('utf-8'))
               .replace(bytes([211]), 'ö'.encode('utf-8'))
               .replace(bytes([227]), 'ä'.encode('utf-8'))
        )

        df = pd.read_csv(io.BytesIO(raw), encoding='utf-8')

        df.columns = [str(c).strip() for c in df.columns]

        for _, row in df.iterrows():
            name = clean_text(row.get('title'))
            sku = clean_text(row.get('part_number'))
            brand = clean_text(row.get('brand')) or 'ERSAAL'
            category = clean_text(row.get('category')) or 'Industriekomponenten'
            top_category = category

            description = strip_html(row.get('body_html'))
            if not description:
                description = f"{name} von {brand}. Angebot und Verfügbarkeit auf Anfrage innerhalb von 24h."

            seo_title = clean_text(row.get('seo_title')) or name
            seo_description = clean_text(row.get('seo_description')) or description
            image = clean_text(row.get('image'))
            tags = [t.strip() for t in clean_text(row.get('keywords')).split(',') if t.strip()]
            condition = 'Neu / Gebraucht'
            mpn = sku
            handle = clean_text(row.get('handle')) or sku or name

            base_slug = slugify(f"{brand}-{sku or handle or name}")
            unique = base_slug
            n = 2
            while unique in seen:
                unique = f"{base_slug}-{n}"
                n += 1

            slug = unique
            seen.add(slug)

            canonical_url = clean_text(row.get('canonical_url'))
            product_url = clean_text(row.get('product_url'))

            url = f'/produkt/{slug}.html'
            if product_url.startswith('/'):
                url = product_url
            elif product_url.startswith('http://') or product_url.startswith('https://'):
                # keep internal static structure for generated pages
                url = f'/produkt/{slug}.html'

            product = {
                'id': len(products) + 1,
                'name': name,
                'sku': sku,
                'brand': brand,
                'category': category,
                'top_category': top_category,
                'description': description,
                'seo_title': seo_title,
                'seo_description': seo_description,
                'image': image,
                'tags': tags,
                'condition': condition,
                'mpn': mpn,
                'slug': slug,
                'url': url,
                'canonical_url': canonical_url or f'{SITE_URL}{url}',
                'status': 'active',
                'inventory_qty': '',
                'alt': name,
                'handle': handle,
                'seo_score': clean_text(row.get('seo_score')),
            }

            if not product['name']:
                product['name'] = product['sku'] or product['handle'] or f'Produkt {product["id"]}'

            if not product['sku']:
                product['sku'] = product['handle'] or product['slug']

            if not product['mpn']:
                product['mpn'] = product['sku']

            if not product['seo_title']:
                product['seo_title'] = product['name']

            if not product['seo_description']:
                product['seo_description'] = product['description']

            if not product['alt']:
                product['alt'] = product['name']

            products.append(product)

    return products


def group_counts(products, key):
    out = {}
    for p in products:
        out.setdefault(p[key], []).append(p)
    return out


def rel_path(depth: int) -> str:
    return '../' * depth


def href_for(depth: int, url: str) -> str:
    root = rel_path(depth)
    return f'{root}{url.lstrip("/")}'


def render_head(title: str, description: str, canonical: str, depth: int, extra_meta: str = '', json_ld: str = '') -> str:
    root = rel_path(depth)
    canonical_full = canonical if canonical.startswith('http://') or canonical.startswith('https://') else f'{SITE_URL}{canonical}'
    return f'''<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description)}">
  <link rel="canonical" href="{html.escape(canonical_full)}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:title" content="{html.escape(title)}">
  <meta property="og:description" content="{html.escape(description)}">
  <meta property="og:url" content="{html.escape(canonical_full)}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="preconnect" href="https://cdn.shopify.com" crossorigin>
  <link rel="stylesheet" href="{root}assets/css/styles.css">
  <script defer src="{root}assets/js/site.js"></script>
  <script defer src="{root}assets/js/search.js"></script>
  {extra_meta}
  {json_ld}
</head>'''


def nav(depth: int) -> str:
    root = rel_path(depth)
    return f'''<header class="site-header">
  <div class="container nav-shell">
    <a class="brand" href="{root}index.html" aria-label="ERSAAL Startseite">
      <span class="brand-mark">⚙</span>
      <span class="brand-text"><strong>ERSAAL</strong><small>INDUSTRIE- UND TECHNIKHANDEL</small></span>
    </a>
    <button class="nav-toggle" aria-label="Menü öffnen" data-nav-toggle>☰</button>
    <nav class="main-nav" data-nav>
      <a href="{root}index.html">Home</a>
      <a href="{root}produkte/index.html">Alle Produkte</a>
      <a href="{root}marken/index.html">Marken</a>
      <a href="{root}kontakt/index.html">Kontakt</a>
      <a href="{root}ueber-uns/index.html">Über Uns</a>
    </nav>
  </div>
</header>'''


def footer(depth: int) -> str:
    root = rel_path(depth)
    return f'''<footer class="site-footer">
  <div class="container footer-grid">
    <div>
      <div class="footer-brand">ERSAAL</div>
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
    <span>© {SITE_NAME}. Alle Rechte vorbehalten.</span>
    <a href="{root}sitemap.xml">Sitemap</a>
  </div>
</footer>'''


def search_bar(depth: int) -> str:
    root = rel_path(depth)
    return f'''<section class="search-strip">
  <div class="container">
    <form class="search-form" action="{root}suche/index.html" method="get">
      <input type="search" name="q" placeholder="Artikelnummer, Marke oder Produkt suchen" aria-label="Produkte suchen" autocomplete="off" data-search-input>
      <button type="submit" class="btn btn-primary">Suchen</button>
      <div class="search-suggestions" data-search-suggestions></div>
    </form>
  </div>
</section>'''


def page_shell(title, description, canonical, body, depth=0, extra_meta='', json_ld=''):
    return f'''<!doctype html>
<html lang="de">
{render_head(title, description, canonical, depth, extra_meta, json_ld)}
<body>
{nav(depth)}
{body}
{footer(depth)}
</body>
</html>'''


def product_card(p, depth=0):
    image = html.escape(p['image']) if p['image'] else f"{rel_path(depth)}assets/img/product-placeholder.svg"
    href = href_for(depth, p['url'])
    img_tag = f'<img src="{image}" alt="{html.escape(p["alt"])}" loading="lazy">'
    return f'''<article class="product-card">
      <a class="product-card__image" href="{href}">{img_tag}</a>
      <div class="product-card__body">
        <div class="eyebrow">{html.escape(p['brand'])}</div>
        <h3><a href="{href}">{html.escape(p['name'])}</a></h3>
        <p class="sku">SKU: {html.escape(p['sku'])}</p>
        <div class="product-card__actions">
          <a class="btn btn-primary" href="{href}#quote-form">Angebot anfordern</a>
          <a class="text-link" href="{href}">Weiterlesen »</a>
        </div>
      </div>
    </article>'''


def make_product_jsonld(p):
    page_url = f'{SITE_URL}{p["url"]}'
    data = {
        '@context': 'https://schema.org',
        '@type': 'Product',
        'name': p['name'],
        'sku': p['sku'],
        'mpn': p['mpn'],
        'brand': {'@type': 'Brand', 'name': p['brand']},
        'category': p['category'],
        'description': meta_desc(p['seo_description'], 300),
        'url': page_url,
        'image': [p['image']] if p['image'] else [],
        'offers': {
            '@type': 'Offer',
            'url': page_url,
            'priceCurrency': 'EUR',
            'availability': 'https://schema.org/LimitedAvailability',
            'priceSpecification': {'@type': 'PriceSpecification', 'priceCurrency': 'EUR'},
            'seller': {'@type': 'Organization', 'name': SITE_NAME},
        },
    }
    breadcrumb = {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': SITE_URL + '/'},
            {'@type': 'ListItem', 'position': 2, 'name': 'Produkte', 'item': SITE_URL + '/produkte/index.html'},
            {'@type': 'ListItem', 'position': 3, 'name': p['brand'], 'item': SITE_URL + f"/marke/{slugify(p['brand'])}/index.html"},
            {'@type': 'ListItem', 'position': 4, 'name': p['name'], 'item': page_url},
        ]
    }
    return f'<script type="application/ld+json">{json.dumps([data, breadcrumb], ensure_ascii=False)}</script>'


def write_product_page(p, related):
    desc = meta_desc(p['seo_description'] or p['description'])
    related_html = ''.join(product_card(x, depth=1) for x in related[:3])
    image = html.escape(p['image']) if p['image'] else '../assets/img/product-placeholder.svg'
    img = f'<img src="{image}" alt="{html.escape(p["alt"])}" loading="eager">'
    brand_link = f'../marke/{slugify(p["brand"])}/index.html'

    body = f'''
<main>
  <section class="hero hero--product">
    <div class="container hero-grid product-grid-top">
      <div class="product-image-panel">{img}</div>
      <div class="product-summary">
        <div class="eyebrow">{html.escape(p['brand'])} · {html.escape(p['category'])}</div>
        <h1>{html.escape(p['name'])}</h1>
        <p class="lead">{html.escape(desc)}</p>
        <ul class="bullet-list compact">
          <li>Schnelle Lieferung weltweit</li>
          <li>Geprüfte Industriequalität</li>
          <li>Persönlicher technischer Support</li>
          <li>Versand erfolgt aus Deutschland</li>
        </ul>
        <div class="cta-row">
          <a class="btn btn-dark" href="#quote-form">Jetzt Angebot anfragen</a>
          <span class="fine-print">Hinweis: ERSAAL ist kein autorisierter Distributor für {html.escape(p['brand'])}.</span>
        </div>
      </div>
    </div>
  </section>

  <section class="section section-tight">
    <div class="container breadcrumbs"><a href="../index.html">Home</a> / <a href="../produkte/index.html">Produkte</a> / <a href="{brand_link}">{html.escape(p['brand'])}</a> / <span>{html.escape(p['sku'])}</span></div>
  </section>

  <section class="section">
    <div class="container two-col-layout">
      <div>
        <h2>Produktinformationen zu {html.escape(p['name'])}</h2>
        <div class="accordion" data-accordion>
          <div class="accordion-item is-open">
            <button class="accordion-trigger" type="button">Warum bei ERSAAL anfragen?</button>
            <div class="accordion-panel">
              <p>{html.escape(p['description'])}</p>
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
                <tr><th>Hersteller</th><td>{html.escape(p['brand'])}</td></tr>
                <tr><th>Artikel</th><td>{html.escape(p['name'])}</td></tr>
                <tr><th>SKU / MPN</th><td>{html.escape(p['sku'])}</td></tr>
                <tr><th>Kategorie</th><td>{html.escape(p['category'])}</td></tr>
                <tr><th>Zustand</th><td>{html.escape(p['condition'])}</td></tr>
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
          <h2>Angebot für {html.escape(p['sku'])} anfordern</h2>
          <p class="form-intro">Übermitteln Sie Ihre Anfrage. Unser Vertriebsteam meldet sich zeitnah mit Preis- und Verfügbarkeitsinformationen.</p>
          <div class="product-mini-specs">
            <div><span>Produkt</span><strong>{html.escape(p['name'])}</strong></div>
            <div><span>Hersteller</span><strong>{html.escape(p['brand'])}</strong></div>
            <div><span>Modell</span><strong>{html.escape(p['sku'])}</strong></div>
          </div>
          <input type="hidden" name="product_name" value="{html.escape(p['name'])}">
          <input type="hidden" name="product_sku" value="{html.escape(p['sku'])}">
          <input type="hidden" name="product_url" value="{SITE_URL}{p['url']}">
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
          <h2>Weitere Komponenten von {html.escape(p['brand'])}</h2>
        </div>
        <a class="text-link" href="{brand_link}">Alle {html.escape(p['brand'])}-Produkte</a>
      </div>
      <div class="product-grid">{related_html}</div>
    </div>
  </section>
</main>
'''
    out = DIST / 'produkt' / f"{p['slug']}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        page_shell(
            page_title(p['seo_title']),
            desc,
            p['url'],
            body,
            depth=1,
            json_ld=make_product_jsonld(p)
        ),
        encoding='utf-8'
    )


def make_pagination(base_url: str, current: int, total: int, depth: int) -> str:
    if total <= 1:
        return ''
    links = []
    for page in range(1, total + 1):
        href = 'index.html' if page == 1 else f'page/{page}/index.html'
        cls = 'active' if page == current else ''
        links.append(f'<a class="{cls}" href="{href}">{page}</a>')
    return '<nav class="pagination">' + ''.join(links) + '</nav>'


def write_listing_page(title, intro, items, out_dir: Path, canonical_base: str, depth: int, hero_title=None):
    if not items:
        return

    total_pages = math.ceil(len(items) / PRODUCTS_PER_PAGE)
    for page_num in range(1, total_pages + 1):
        start = (page_num - 1) * PRODUCTS_PER_PAGE
        subset = items[start:start + PRODUCTS_PER_PAGE]
        cards = ''.join(product_card(p, depth=depth) for p in subset)
        pagination = make_pagination(canonical_base, page_num, total_pages, depth)
        canonical = canonical_base if page_num == 1 else canonical_base.replace('/index.html', f'/page/{page_num}/index.html')
        body = f'''
<main>
  <section class="page-hero">
    <div class="container">
      <div class="eyebrow">Industriekomponenten</div>
      <h1>{html.escape(hero_title or title)}</h1>
      <p class="lead">{html.escape(intro)}</p>
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
'''
        target = out_dir / ('index.html' if page_num == 1 else f'page/{page_num}/index.html')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            page_shell(
                page_title(title + (f' – Seite {page_num}' if page_num > 1 else '')),
                meta_desc(intro),
                canonical,
                body,
                depth=depth
            ),
            encoding='utf-8'
        )


def write_home(products, brands, categories):
    featured = products[:6]

    categories_html = ''.join([
        f'''<article class="category-card"><div class="category-card__media"><img src="{html.escape((items[0]['image'] or 'assets/img/product-placeholder.svg'))}" alt="{html.escape(name)}" loading="lazy"></div><div class="category-card__body"><h3>{html.escape(name)}</h3><p>Leistungsstarke und zuverlässige Lösungen für präzise industrielle Anwendungen und Beschaffung.</p><a class="btn btn-primary" href="kategorie/{slugify(name)}/index.html">Komponenten entdecken</a></div></article>'''
        for name, items in list(categories.items())[:3]
    ])

    featured_html = ''.join(product_card(p, depth=0) for p in featured)
    brand_html = ''.join([
        f'<a class="pill" href="marke/{slugify(name)}/index.html">{html.escape(name)} <span>{len(items)}</span></a>'
        for name, items in list(brands.items())[:12]
    ])

    body = f'''
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
      <div class="section-head"><div><div class="eyebrow">Sortiment</div><h2>Kategorien für industrielle Beschaffung</h2></div></div>
      <div class="category-grid">{categories_html}</div>
    </div>
  </section>

  <section class="section">
    <div class="container">
      <div class="section-head"><div><div class="eyebrow">Products</div><h2>Ausgewählte Produkte</h2></div><a class="text-link" href="produkte/index.html">Alle Produkte anzeigen</a></div>
      <div class="product-grid">{featured_html}</div>
    </div>
  </section>

  <section class="section section-alt">
    <div class="container">
      <div class="section-head"><div><div class="eyebrow">Marken</div><h2>Hersteller im Katalog</h2></div></div>
      <div class="pill-row">{brand_html}</div>
    </div>
  </section>
</main>
'''
    json_ld = '<script type="application/ld+json">' + json.dumps({
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        'name': SITE_NAME,
        'url': SITE_URL,
        'potentialAction': {
            '@type': 'SearchAction',
            'target': f'{SITE_URL}/suche/index.html?q={{search_term_string}}',
            'query-input': 'required name=search_term_string'
        }
    }, ensure_ascii=False) + '</script>'

    (DIST / 'index.html').write_text(
        page_shell(
            page_title('Industriekomponenten & technische Beschaffung'),
            meta_desc('Skalierbarer B2B-Katalog für industrielle Komponenten, Ersatzteile und Angebotsanfragen.'),
            '/index.html',
            body,
            depth=0,
            json_ld=json_ld
        ),
        encoding='utf-8'
    )


def write_simple_page(filename, title, text, depth=1):
    body = f'''<main><section class="page-hero"><div class="container"><div class="eyebrow">ERSAAL</div><h1>{html.escape(title)}</h1><p class="lead">{html.escape(text)}</p></div></section></main>'''
    target = DIST / filename / 'index.html'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        page_shell(
            page_title(title),
            meta_desc(text),
            f'/{filename}/index.html',
            body,
            depth=depth
        ),
        encoding='utf-8'
    )


def write_brand_index(brands):
    cards = ''.join([
        f'<article class="simple-card"><h2><a href="../marke/{slugify(name)}/index.html">{html.escape(name)}</a></h2><p>{len(items)} Produkte</p><a class="text-link" href="../marke/{slugify(name)}/index.html">Zur Marke »</a></article>'
        for name, items in brands.items()
    ])
    body = f'''<main><section class="page-hero"><div class="container"><div class="eyebrow">Marken</div><h1>Marken im Katalog</h1><p class="lead">Herstellerseiten mit indexierten Produktlisten und SEO-freundlichen Landingpages.</p></div></section><section class="section section-alt"><div class="container simple-grid">{cards}</div></section></main>'''
    (DIST / 'marken').mkdir(parents=True, exist_ok=True)
    (DIST / 'marken' / 'index.html').write_text(
        page_shell(
            page_title('Marken'),
            meta_desc('Herstellerseiten für den gesamten Produktkatalog.'),
            '/marken/index.html',
            body,
            depth=1
        ),
        encoding='utf-8'
    )


def write_category_index(categories):
    cards = ''.join([
        f'<article class="simple-card"><h2><a href="../kategorie/{slugify(name)}/index.html">{html.escape(name)}</a></h2><p>{len(items)} Produkte</p><a class="text-link" href="../kategorie/{slugify(name)}/index.html">Zur Kategorie »</a></article>'
        for name, items in categories.items()
    ])
    body = f'''<main><section class="page-hero"><div class="container"><div class="eyebrow">Kategorien</div><h1>Kategorien im Katalog</h1><p class="lead">Kategorieseiten mit sauberer interner Verlinkung und schneller Navigation.</p></div></section><section class="section section-alt"><div class="container simple-grid">{cards}</div></section></main>'''
    (DIST / 'kategorien').mkdir(parents=True, exist_ok=True)
    (DIST / 'kategorien' / 'index.html').write_text(
        page_shell(
            page_title('Kategorien'),
            meta_desc('Kategorieseiten für Industriekomponenten.'),
            '/kategorien/index.html',
            body,
            depth=1
        ),
        encoding='utf-8'
    )


def write_search_page():
    body = '''<main><section class="page-hero"><div class="container"><div class="eyebrow">Suche</div><h1>Produkte durchsuchen</h1><p class="lead">Schnelle Suche nach Artikelnummern, Marken und Produktnamen.</p></div></section><section class="section"><div class="container"><form class="search-form search-form--wide" action="" method="get"><input type="search" name="q" placeholder="z. B. ZXH9999-0052" data-search-page-input><button class="btn btn-primary" type="submit">Suchen</button></form><div id="search-results" class="search-results"></div></div></section></main>'''
    target = DIST / 'suche' / 'index.html'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        page_shell(
            page_title('Suche'),
            meta_desc('Produktsuche im Industriekatalog.'),
            '/suche/index.html',
            body,
            depth=1
        ),
        encoding='utf-8'
    )


def write_assets(local_search: bool):
    css = r'''
:root{--bg:#f6f7fb;--surface:#fff;--surface-alt:#eef1f7;--text:#0d1830;--muted:#576278;--line:#dce2ee;--primary:#2557c6;--primary-dark:#0f2344;--shadow:0 16px 40px rgba(12,26,56,.08);--radius:22px;--container:min(1220px,calc(100% - 40px));font-synthesis-weight:none}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:var(--text);background:#fff;line-height:1.55}a{color:inherit;text-decoration:none}img{max-width:100%;display:block}button,input,select,textarea{font:inherit}.container{width:var(--container);margin-inline:auto}.site-header{position:sticky;top:0;z-index:30;background:rgba(9,17,34,.78);backdrop-filter:blur(16px);color:#fff}.nav-shell{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:18px 0}.brand{display:flex;align-items:center;gap:12px}.brand-mark{width:58px;height:58px;border:2px solid rgba(255,255,255,.45);border-radius:50%;display:grid;place-items:center;font-size:30px}.brand-text{display:flex;flex-direction:column;line-height:1}.brand-text strong{font-size:2rem;letter-spacing:.02em}.brand-text small{font-size:.75rem;opacity:.88;margin-top:6px}.main-nav{display:flex;gap:34px;align-items:center}.main-nav a{font-size:1.05rem;color:#fff;opacity:.96}.nav-toggle{display:none;background:none;border:none;color:#fff;font-size:1.6rem}.hero{position:relative;overflow:hidden}.hero--home{min-height:78vh;background:#101b34;color:#fff;display:flex;align-items:center}.hero-media{position:absolute;inset:0;background:linear-gradient(rgba(10,19,37,.68),rgba(10,19,37,.78)),url('https://images.unsplash.com/photo-1581091215367-59ab6dcef10f?auto=format&fit=crop&w=1600&q=80') center/cover no-repeat;transform:scale(1.02)}.hero-content{position:relative;padding:120px 0 110px;max-width:980px}.eyebrow{font-size:1rem;font-weight:700;letter-spacing:.02em;color:var(--primary-dark);margin-bottom:18px}.eyebrow-light{color:#fff}.hero h1,.page-hero h1,.section h2{font-size:clamp(2.4rem,5vw,4.1rem);line-height:1.04;margin:0 0 22px;font-weight:800;letter-spacing:-.03em}.lead{font-size:1.22rem;color:var(--muted);max-width:950px}.lead-light{color:rgba(255,255,255,.88)}.cta-row{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin-top:28px}.btn{display:inline-flex;align-items:center;justify-content:center;padding:16px 28px;border-radius:999px;font-weight:800;transition:.2s;border:1px solid transparent;cursor:pointer}.btn-primary{background:var(--primary);color:#fff;box-shadow:0 14px 30px rgba(37,87,198,.24)}.btn-dark{background:var(--primary-dark);color:#fff;box-shadow:var(--shadow)}.btn-ghost{border-color:rgba(255,255,255,.55);color:#fff}.btn:hover{transform:translateY(-1px)}.search-strip{background:#fff;padding:26px 0;border-bottom:1px solid var(--line)}.search-form{position:relative;display:grid;grid-template-columns:1fr auto;gap:14px}.search-form input{height:60px;border-radius:999px;border:1px solid var(--line);padding:0 24px;background:#fff}.search-form--wide{max-width:920px}.search-suggestions{position:absolute;left:0;right:150px;top:calc(100% + 10px);background:#fff;border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow);display:none;overflow:hidden}.search-suggestions.active{display:block}.search-suggestions a{display:block;padding:14px 18px;border-top:1px solid var(--line)}.search-suggestions a:first-child{border-top:none}.section{padding:90px 0}.section-tight{padding:18px 0}.section-alt{background:var(--bg)}.narrow-center{text-align:center;max-width:1150px}.centered{display:inline-block;text-align:left}.bullet-list{margin:26px 0 0;padding-left:24px;color:var(--muted);font-size:1.2rem}.bullet-list.compact{font-size:1rem}.bullet-list li{margin:8px 0}.category-grid,.product-grid,.simple-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:34px}.category-card,.product-card,.simple-card{background:#fff;border:1px solid var(--line);border-radius:28px;overflow:hidden;box-shadow:var(--shadow)}.category-card__media{background:#f4f4f4;aspect-ratio:1.35}.category-card__media img{width:100%;height:100%;object-fit:contain;padding:24px}.category-card__body{padding:26px}.category-card__body h3,.product-card h3,.simple-card h2{font-size:1.9rem;line-height:1.1;margin:0 0 18px;letter-spacing:-.02em}.section-head{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;margin-bottom:28px}.product-card{display:flex;flex-direction:column}.product-card__image{display:grid;place-items:center;aspect-ratio:1.08;background:#f7f7f7;padding:30px}.product-card__image img{width:100%;height:100%;object-fit:contain}.product-card__body{padding:22px 22px 26px}.product-card .sku{color:var(--muted);margin:12px 0 20px}.product-card__actions{display:flex;flex-direction:column;align-items:flex-start;gap:12px}.text-link{font-weight:700;color:var(--primary-dark)}.pill-row{display:flex;gap:16px;flex-wrap:wrap}.pill{display:inline-flex;gap:10px;align-items:center;padding:14px 18px;border-radius:999px;background:#fff;border:1px solid var(--line);font-weight:700}.pill span{display:inline-grid;place-items:center;min-width:32px;height:32px;border-radius:999px;background:var(--surface-alt)}.page-hero{padding:84px 0 36px;background:linear-gradient(180deg,#f8f9fc,white)}.hero--product{padding:56px 0;background:linear-gradient(180deg,#f8f9fc,#fff)}.hero-grid{display:grid;grid-template-columns:1.05fr .95fr;gap:44px;align-items:center}.product-image-panel{background:#f7f7f7;border-radius:28px;padding:42px;min-height:420px;display:grid;place-items:center}.product-image-panel img{max-height:380px;object-fit:contain}.product-summary h1{font-size:clamp(2.2rem,4vw,3.4rem)}.fine-print{color:var(--muted)}.breadcrumbs{font-size:.95rem;color:var(--muted)}.two-col-layout{display:grid;grid-template-columns:1.05fr .95fr;gap:36px;align-items:start}.accordion{border-top:1px solid var(--line)}.accordion-item{border-bottom:1px solid var(--line)}.accordion-trigger{width:100%;padding:24px 0;background:none;border:none;text-align:left;font-size:1.08rem;font-weight:800;color:var(--primary-dark);position:relative}.accordion-trigger::after{content:'+';position:absolute;right:10px;top:50%;transform:translateY(-50%);font-size:1.3rem}.accordion-item.is-open .accordion-trigger::after{content:'−'}.accordion-panel{display:none;padding:0 0 24px;color:var(--muted)}.accordion-item.is-open .accordion-panel{display:block}.spec-table{width:100%;border-collapse:collapse}.spec-table th,.spec-table td{padding:14px 0;border-bottom:1px solid var(--line);text-align:left}.spec-table th{width:36%;color:var(--primary-dark)}.quote-form{position:sticky;top:96px;background:#fff;border:1px solid var(--line);border-radius:24px;padding:28px;box-shadow:var(--shadow)}.quote-form h2{font-size:2rem;margin:0 0 10px}.form-intro{color:var(--muted);font-size:.96rem;margin:0 0 18px}.product-mini-specs{border:1px solid var(--line);border-radius:18px;padding:14px 16px;display:grid;gap:12px;background:#fafbfe}.product-mini-specs div{display:flex;justify-content:space-between;gap:12px;font-size:.95rem}.product-mini-specs span{color:var(--muted)}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px}.form-grid label{display:flex;flex-direction:column;gap:8px;font-weight:700;font-size:.95rem}.form-grid input,.form-grid select,.form-grid textarea{border:1px solid var(--line);border-radius:12px;padding:14px 14px;background:#fff}.form-grid .full{grid-column:1/-1}.checkbox{flex-direction:row!important;align-items:flex-start}.checkbox input{margin-top:4px}.pagination{display:flex;gap:10px;justify-content:center;margin-top:34px;flex-wrap:wrap}.pagination a{width:44px;height:44px;border-radius:999px;display:grid;place-items:center;border:1px solid var(--line);background:#fff}.pagination a.active{background:var(--primary);color:#fff;border-color:var(--primary)}.site-footer{background:#0d1830;color:rgba(255,255,255,.9);padding:68px 0 30px}.footer-grid{display:grid;grid-template-columns:2fr 1fr 1fr;gap:30px}.footer-grid h3{margin:0 0 14px}.footer-grid a{display:block;color:rgba(255,255,255,.9);margin:8px 0}.footer-brand{font-size:2rem;font-weight:800}.footer-bottom{display:flex;justify-content:space-between;gap:20px;padding-top:24px;margin-top:24px;border-top:1px solid rgba(255,255,255,.16)}.search-results{display:grid;gap:18px;margin-top:26px}.search-result{background:#fff;border:1px solid var(--line);border-radius:20px;padding:20px}.simple-grid{grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}.simple-card{padding:24px}.simple-card h2{font-size:1.4rem}.simple-card p{color:var(--muted)}@media (max-width:1050px){.hero-grid,.two-col-layout,.category-grid,.product-grid{grid-template-columns:1fr 1fr}.brand-text strong{font-size:1.6rem}}@media (max-width:780px){.main-nav{display:none;position:absolute;top:88px;left:20px;right:20px;background:#0d1830;border-radius:20px;padding:18px;flex-direction:column;align-items:flex-start}.main-nav.is-open{display:flex}.nav-toggle{display:block}.hero--home{min-height:66vh}.hero-content{padding:86px 0}.hero h1,.page-hero h1,.section h2{font-size:2.35rem}.search-form{grid-template-columns:1fr}.search-suggestions{right:0}.category-grid,.product-grid,.hero-grid,.two-col-layout,.footer-grid,.form-grid{grid-template-columns:1fr}.quote-form{position:static}.section{padding:68px 0}.section-head,.footer-bottom,.nav-shell{align-items:flex-start;flex-direction:column}.product-image-panel{min-height:260px}}
'''
    (CSS_DIR / 'styles.css').write_text(css, encoding='utf-8')

    site_js = '''document.addEventListener('DOMContentLoaded',()=>{document.querySelectorAll('[data-nav-toggle]').forEach(btn=>btn.addEventListener('click',()=>{document.querySelector('[data-nav]')?.classList.toggle('is-open')}));document.querySelectorAll('[data-accordion]').forEach(acc=>{acc.querySelectorAll('.accordion-trigger').forEach(btn=>btn.addEventListener('click',()=>btn.parentElement.classList.toggle('is-open')))});});'''
    (JS_DIR / 'site.js').write_text(site_js, encoding='utf-8')

    search_js = f'''
const SEARCH_CONFIG = {{ mode: '{'local' if local_search else 'external'}', localIndex: '/assets/js/search-index.json', externalHint: 'Für sehr große Kataloge ab ca. 20k–50k Datensätzen sollte ein externer Suchindex wie Algolia oder Meilisearch verwendet werden.' }};
let __catalogCache;
async function loadCatalog(){{ if(__catalogCache) return __catalogCache; if(SEARCH_CONFIG.mode !== 'local') return []; const res = await fetch(SEARCH_CONFIG.localIndex); __catalogCache = await res.json(); return __catalogCache; }}
function normalize(s){{ return (s||'').toLowerCase(); }}
function score(item,q){{ q=normalize(q); let s=0; if(normalize(item.sku)===q) s+=100; if(normalize(item.name).includes(q)) s+=45; if(normalize(item.sku).includes(q)) s+=55; if(normalize(item.brand).includes(q)) s+=20; if(normalize(item.category).includes(q)) s+=10; return s; }}
function searchCatalog(items,q,limit=8){{ return items.map(item=>({{item,score:score(item,q)}})).filter(x=>x.score>0).sort((a,b)=>b.score-a.score).slice(0,limit).map(x=>x.item); }}
function renderSuggestions(container,results){{ if(!container) return; if(!results.length){{container.classList.remove('active'); container.innerHTML=''; return;}} container.innerHTML = results.map(r=>`<a href="${{r.url}}"><strong>${{r.sku}}</strong><br><span>${{r.name}}</span></a>`).join(''); container.classList.add('active'); }}
async function bootHeaderSearch(){{ const input=document.querySelector('[data-search-input]'); const box=document.querySelector('[data-search-suggestions]'); if(!input || SEARCH_CONFIG.mode!=='local') return; const items=await loadCatalog(); input.addEventListener('input',()=>{{ const q=input.value.trim(); if(q.length<2) return renderSuggestions(box,[]); renderSuggestions(box,searchCatalog(items,q,6)); }}); document.addEventListener('click',e=>{{ if(!box?.contains(e.target) && e.target!==input) box?.classList.remove('active'); }}); }}
async function bootSearchPage(){{ const root=document.getElementById('search-results'); const input=document.querySelector('[data-search-page-input]'); if(!root || !input) return; const params=new URLSearchParams(location.search); const q=params.get('q')||''; input.value=q; if(!q){{ root.innerHTML='<p class="lead">Geben Sie eine Suchanfrage ein.</p>'; return; }} if(SEARCH_CONFIG.mode!=='local'){{ root.innerHTML=`<div class="search-result"><h2>Externe Suche empfohlen</h2><p>${{SEARCH_CONFIG.externalHint}}</p></div>`; return; }} const items=await loadCatalog(); const results=searchCatalog(items,q,30); root.innerHTML = results.length ? results.map(r=>`<article class="search-result"><div class="eyebrow">${{r.brand}}</div><h2><a href="${{r.url}}">${{r.name}}</a></h2><p>SKU: ${{r.sku}}</p><a class="btn btn-primary" href="${{r.url}}#quote-form">Angebot anfordern</a></article>`).join('') : '<p class="lead">Keine Ergebnisse gefunden.</p>'; }}
window.addEventListener('DOMContentLoaded',()=>{{ bootHeaderSearch(); bootSearchPage(); }});
'''
    (JS_DIR / 'search.js').write_text(search_js, encoding='utf-8')

    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 280"><rect width="400" height="280" rx="28" fill="#eef1f7"/><g fill="#2557c6"><rect x="110" y="90" width="180" height="100" rx="14" opacity="0.22"/><path d="M164 111h72v58h-72z" opacity="0.45"/><circle cx="147" cy="140" r="12"/><circle cx="253" cy="140" r="12"/></g></svg>'
    (IMG_DIR / 'product-placeholder.svg').write_text(svg, encoding='utf-8')


def write_search_index(products, local_search: bool):
    data = [
        {'name': p['name'], 'sku': p['sku'], 'brand': p['brand'], 'category': p['category'], 'url': p['url']}
        for p in products
    ]
    (JS_DIR / 'search-index.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')


def write_sitemap(all_urls):
    unique_urls = []
    seen = set()
    for url in all_urls:
        if url not in seen:
            unique_urls.append(url)
            seen.add(url)

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in unique_urls:
        lines.append(f'  <url><loc>{SITE_URL}{url}</loc></url>')
    lines.append('</urlset>')

    (DIST / 'sitemap.xml').write_text('\n'.join(lines), encoding='utf-8')
    (DIST / 'robots.txt').write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding='utf-8')


def write_readme(products_count, brands_count, categories_count, local_search):
    readme = f'''# ERSAAL Static Catalog
