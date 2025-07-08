import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
from typing import List, Dict
from llm_call import call_llm
from show_price_content import show_price_statements

SELECTORS = [
    '[itemprop="price"]', '.price', '.product-price', '.a-price .a-offscreen', '.priceblock_ourprice', '.priceblock_dealprice', '#priceblock_ourprice', '#priceblock_dealprice', '.offer-price', '.selling-price', '.product-price', '.price-final', '.price__regular', '.price__sale', '.product__price', '.product__price--final', '.product__price--sale',
]

def fetch_html(url: str, timeout: int = 10) -> str:
    async def _fetch():
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            return resp.text
    return asyncio.run(_fetch()) if not asyncio.get_event_loop().is_running() else _fetch()

def filter_price_statements(statements):
    blacklist = [
        "font", "weight", "width", "height", "divToUpdate", "feature_div",
        "color", "padding", "margin", "border", "background", "iconName",
        "class", "style", "display", "updateOnHover", "customClientFunction",
        "isPrefetchable", "loadingBar", "nodeType", "Entry", "sys", "type",
        "updatedAt", "content", "marks", "data", "icon", "featureDiv", "feature",
        "div", "span", "css", "em", "px"
    ]
    filtered = []
    for s in statements:
        if not any(b in s.lower() for b in blacklist):
            filtered.append(s)
    return filtered

async def scrape_product(url: str) -> Dict:
    try:
        html = await fetch_html(url)
    except Exception as e:
        return {"link": url, "error": str(e)}
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.string.strip() if soup.title else ""
    h1 = soup.find('h1')
    product_name = h1.get_text(strip=True) if h1 else title
    canonical = soup.find('link', rel='canonical')
    canonical_url = canonical['href'] if canonical and canonical.has_attr('href') else url
    parsed = urlparse(url)
    site_name = parsed.netloc
    raw_statements = list(show_price_statements(soup))
    price_statements = filter_price_statements(raw_statements)
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
        "Make sure that price that you select is not a discount , any warranty price, emi price, Apple Care price, etc"
        "It should be the most likely price of the product so carefully go through the whole information and then select the price."
        "Return your answer as a JSON list, where each item is: { 'link': ..., 'price': ..., 'currency': ... }. "
        "You have to find the correct currency and cannot use PHP, etc or anything for this case. Make sure that currency and price is correct."
        "Apply a little bit of logic to check if the price is right according to the currency and product and if it is not then use null"
        "If you cannot find a price, use null.\n\n"
    )
    for item in scraped:
        if "priceStatements" not in item:
            continue  # skip errored or malformed items
        prompt += f"Link: {item['link']}\n"
        for stmt in item['priceStatements']:
            prompt += f"- {stmt}\n"
        prompt += "\n"
    prompt += "\nOutput:"
    return prompt

async def scrape_products(urls: List[str]) -> List[Dict]:
    scraped = await asyncio.gather(*(scrape_product(url) for url in urls))
    prompt = build_llm_price_prompt(scraped)
    llm_response = call_llm(prompt)
    # print("LLM response:")
    return llm_response