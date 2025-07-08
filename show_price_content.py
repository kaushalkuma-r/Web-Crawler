import sys
import httpx
from bs4 import BeautifulSoup
import re

SELECTORS = [
    '[itemprop="price"]', '.price', '.product-price', '.a-price .a-offscreen', '.priceblock_ourprice', '.priceblock_dealprice', '#priceblock_ourprice', '#priceblock_dealprice', '.offer-price', '.selling-price', '.product-price', '.price-final', '.price__regular', '.price__sale', '.product__price', '.product__price--final', '.product__price--sale',
]

def fetch_html(url):
    resp = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15, follow_redirects=True)
    resp.raise_for_status()
    return resp.text

def show_price_statements(soup):
    statements = set()
    # Check all text nodes for lines with 'price' and a digit
    for tag in soup.find_all(True):
        text = tag.get_text(separator=' ', strip=True)
        # Split into sentences/lines for more granular matching
        for line in re.split(r'[\n\r\.|!|?]', text):
            line = line.strip()
            if 'price' in line.lower() and re.search(r'\d', line):
                statements.add(line)
    # if statements:
    #     for s in sorted(statements):
    #         print(s)
    # else:
    #     print("No price statement found.")
    
    return statements

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter product page URL: ")
    try:
        show_price_statements(url)
    except Exception as e:
        print(f"Error: {e}") 