import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "leads.db")

# Optional keys - every enricher module checks its own key and
# silently skips itself if the key is missing/blank. Nothing breaks
# without them, they just add more data when present.
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "").strip()
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "").strip()

# Scraping etiquette
REQUEST_TIMEOUT = 8  # seconds
USER_AGENT = "Mozilla/5.0 (compatible; LeadEnricherBot/1.0; +https://example.com/bot)"
MIN_DELAY_BETWEEN_REQUESTS_TO_SAME_DOMAIN = 2  # seconds
