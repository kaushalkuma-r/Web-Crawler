import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
from typing import List, Dict
from llm_call import call_llm

SELECTORS = [
    '[itemprop="price"]', '.price', '.product-price', '.a-price .a-offscreen', '.priceblock_ourprice', '.priceblock_dealprice', '#priceblock_ourprice', '#priceblock_dealprice', '.offer-price', '.selling-price', '.product-price', '.price-final', '.price__regular', '.price__sale', '.product__price', '.product__price--final', '.product__price--sale',
]

def extract_price_value(text):
    cleaned = re.sub(r'[^\d.,]', '', text)
    matches = re.findall(r'\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?', cleaned)
    for m in matches:
        val = m.replace(',', '.') if m.count(',') == 1 and m.count('.') == 0 else m.replace(',', '')
        try:
            price = float(val)
            return price
        except Exception:
            continue
    return None

def extract_currency(text):
    # Try to extract a currency symbol or code from the text
    if '$' in text:
        return 'USD'
    if '€' in text:
        return 'EUR'
    if '₹' in text:
        return 'INR'
    if '£' in text:
        return 'GBP'
    if 'CAD' in text or 'C$' in text:
        return 'CAD'
    if 'AUD' in text or 'A$' in text:
        return 'AUD'
    return None

def fetch_html(url: str, timeout: int = 10) -> str:
    async def _fetch():
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            return resp.text
    return asyncio.run(_fetch()) if not asyncio.get_event_loop().is_running() else _fetch()

def extract_price_statements(html: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    statements = set()
    for tag in soup.find_all(True):
        text = tag.get_text(separator=' ', strip=True)
        for line in re.split(r'[\n\r\.|!|?]', text):
            line = line.strip()
            if 'price' in line.lower() and re.search(r'\d', line):
                statements.add(line)
    return list(statements)

async def scrape_product(url: str) -> Dict:
    try:
        html = await fetch_html(url)
    except Exception as e:
        return {"link": url, "error": str(e)}
    soup = BeautifulSoup(html, "lxml")
    # Product name
    title = soup.title.string.strip() if soup.title else ""
    h1 = soup.find('h1')
    product_name = h1.get_text(strip=True) if h1 else title
    # Canonical URL
    canonical = soup.find('link', rel='canonical')
    canonical_url = canonical['href'] if canonical and canonical.has_attr('href') else url
    # Site name
    parsed = urlparse(url)
    site_name = parsed.netloc
    # Collect price statements for LLM
    price_statements = extract_price_statements(html)
    return {
        "link": url,
        "productName": product_name,
        "canonicalUrl": canonical_url,
        "siteName": site_name,
        "priceStatements": price_statements,
    }

def build_llm_price_prompt(scraped: List[Dict]) -> str:
    prompt = (
        "You are an expert at extracting product prices from e-commerce web page content. "
        "Given the following price-related statements for each product page, extract the most likely price and currency for the product on that page. "
        "Return your answer as a JSON list, where each item is: { 'link': ..., 'price': ..., 'currency': ... }. "
        "If you cannot find a price, use null.\n\n"
    )
    for item in scraped:
        prompt += f"Link: {item['link']}\n"
        for stmt in item['priceStatements']:
            prompt += f"- {stmt}\n"
        prompt += "\n"
    prompt += "\nOutput:"
    return prompt

async def scrape_products(urls: List[str]) -> List[Dict]:
    scraped = await asyncio.gather(*(scrape_product(url) for url in urls))
    # Build LLM prompt
    prompt = build_llm_price_prompt(scraped)
    llm_response = call_llm(prompt)
    # Try to parse LLM response as JSON
    try:
        import json
        llm_prices = json.loads(llm_response)
        link_to_price = {item['link']: item for item in llm_prices if 'link' in item}
    except Exception:
        link_to_price = {}
    # Merge LLM price/currency into results
    results = []
    for item in scraped:
        link = item['link']
        price = link_to_price.get(link, {}).get('price')
        currency = link_to_price.get(link, {}).get('currency')
        out = {
            "link": link,
            "price": price,
            "currency": currency,
            "productName": item["productName"],
            "canonicalUrl": item["canonicalUrl"],
            "siteName": item["siteName"],
        }
        results.append(out)
    return results 