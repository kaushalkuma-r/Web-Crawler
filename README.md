# Universal Price Aggregator

A production-grade microservice that, given a country and product query, performs a live web search, scrapes e-commerce results, matches products semantically, normalizes currencies, and returns sorted price data.

## Features
- Country-restricted Google search for e-commerce links (first 3 pages)
- Scrapes product title, price, currency, canonical URL, and site name
- Uses LLM/embeddings to filter for true product matches (cosine ≥ 0.8)
- Normalizes all prices to the target country's currency (via exchangerate.host)
- Returns a JSON array sorted by ascending price

## API
### POST `/aggregate-prices`
**Request:**
```json
{
  "country": "<ISO-2>",
  "query": "<free-text product spec>"
}
```
**Response:**
```json
[
  {
    "link": "https://…",
    "price": 123.45,
    "currency": "USD",
    "productName": "…",
    "source": "Amazon US",
    "matchedScore": 0.92,
    "scrapedAt": "2025-07-07T18:00:00Z"
  }
]
```

## Setup
1. Clone the repo
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the service:
   ```bash
   uvicorn main:app --reload
   ```

## Notes
- Scraping logic is stubbed; for production, use Playwright or similar for robust scraping.
- Embedding model: `all-MiniLM-L6-v2` via `sentence-transformers`.
- Currency mapping is basic; use a full mapping for global support.
- Google search is performed via public SERP scraping with country restriction (`gl` param).
- Anti-bot and proxy handling are not included in this demo.

## Architecture
- **FastAPI** for the web service
- **httpx** for async HTTP requests
- **BeautifulSoup** for HTML parsing
- **sentence-transformers** for semantic matching
- **exchangerate.host** for currency conversion

## TODO
- Implement robust scraping for real e-commerce sites
- Add proxy/anti-bot support for Google and e-commerce scraping
- Expand currency and country mapping
- Add more e-commerce domain heuristics 