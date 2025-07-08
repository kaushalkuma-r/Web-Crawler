
import os
from pathlib import Path
from typing import List, Optional

import requests
from dotenv import load_dotenv   # pip install python-dotenv

# Load .env (if present)
load_dotenv(Path(__file__).resolve().parent / ".env")

API_KEY = os.getenv("SERPAPI_KEY")
if not API_KEY:
    raise RuntimeError("SERPAPI_KEY not found in environment or .env file.")
def get_google_search_links(
    query: str,
    total_results: int = 20,
    country: Optional[str] = None,
    language: Optional[str] = None,
) -> List[str]:
    """
    Collect up to `total_results` organic URLs using SerpAPI pagination.
    Google caps `num` at 100, so we loop over pages with `start`.
    """
    links, fetched = [], 0
    while fetched < total_results:
        batch_size = min(100, total_results - fetched)      # 100 per page max
        params = {
            "engine": "google",
            "q": query,
            "api_key": API_KEY,
            "num": batch_size,
            "start": fetched,       # 0, 100, 200…
        }
        if country:
            params["gl"] = country.lower()
        if language:
            params["hl"] = language.lower()

        r = requests.get("https://serpapi.com/search", params=params, timeout=15)
        r.raise_for_status()
        data = r.json()

        page_links = [
            item["link"]
            for item in data.get("organic_results", [])
            if "link" in item
        ]
        if not page_links:       # nothing returned ⇒ stop early
            break

        links.extend(page_links)
        fetched += len(page_links)

        # Safety: break if Google returns fewer than requested (end of SERP)
        if len(page_links) < batch_size:
            break

    return links[:total_results]   # trim in case of extras


# Example: grab first 250 French‑biased links
if __name__ == "__main__":
    french_links = get_google_search_links("buy iPhone 15 online", total_results=30, country="fr")
    print(len(french_links), "links fetched")
