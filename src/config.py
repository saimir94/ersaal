from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DIST = BASE_DIR / "dist"
DATA_DIR = BASE_DIR / "data"
ASSETS = DIST / "assets"
CSS_DIR = ASSETS / "css"
JS_DIR = ASSETS / "js"
IMG_DIR = ASSETS / "img"

SITE_URL = "https://www.ersaal.de"
SITE_NAME = "ERSAAL"
SITE_TAGLINE = "Industrie- und Technikhandel"

DEFAULT_FORM_ENDPOINT = "https://formspree.io/f/your-form-id"

PRODUCTS_PER_PAGE = 24
SEARCH_LOCAL_THRESHOLD = 20000

DEFAULT_BRAND = "ERSAAL"
DEFAULT_CATEGORY = "Industriekomponenten"

SUPPORTED_CSV_ENCODINGS = [
    "utf-8",
    "utf-8-sig",
    "cp1252",
    "latin1",
]