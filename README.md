# ERSAAL Static Catalog

Production-ready static B2B quote-request catalog generated from CSV.

## What is included
- Static HTML product pages for all 4990 products
- SEO-friendly product URLs under `/produkt/`
- Paginated listing pages
- Brand and category landing pages
- `sitemap.xml` and `robots.txt`
- Lightweight search layer with a pluggable adapter
- Formspree-ready RFQ forms
- Clean, dependency-light generator (`build.py`)

## Deploy
Upload the contents of `dist/` to Cloudflare Pages, Vercel static hosting, Netlify, S3, or any CDN-backed static host.

## Regenerate site
```bash
python build.py
```

## Search strategy
Current build mode: `local JSON index`.

For very large catalogs (100k+ to 1M+ SKUs), keep HTML generation static but move search to Algolia or Meilisearch. The included `assets/js/search.js` is already structured for that switch.

## Form integration
Replace the placeholder Formspree endpoint in `build.py` and regenerate:
```python
DEFAULT_FORM_ENDPOINT = 'https://formspree.io/f/your-form-id'
```

## Scalability notes
- Keep product pages fully static for maximum cacheability.
- Split sitemap generation into multiple sitemap files when you exceed 50,000 URLs.
- For 1M+ products, precompute search indexes externally and publish brand/category pages selectively.
- Consider chunked builds and incremental pipelines per vendor/category.

## Dataset summary
- Products: 4990
- Brands: 1
- Categories: 1
