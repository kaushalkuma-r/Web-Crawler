import json
import re
from utils.llm_call import call_llm
from utils.link_get import get_google_search_links
from utils.scraper_llm import scrape_products

__all__ = [
    'filter_links_with_llm',
    'clean_url',
    'get_google_search_links',
    'scrape_products',
]

def filter_links_with_llm(query, links, country):
    prompt = (
        f"You are an expert e-commerce assistant. "
        f"Given the product search query: '{query}', and the following list of URLs from a web search, "
        f"return ONLY the links that are actual e-commerce product pages where a user can buy the product '{query}' in '{country}'. "
        f"Exclude links to forums, news, Wikipedia, YouTube, Reddit, or any non-shopping sites. "
        f"Exclude links for different products, models, variants, or countries. "
        f"Exclude links for similar but not exact products. "
        f"Exclude links for other countries (check domain, language, or content). "
        f"Only include links where the product and country match exactly. "
        f"Return the filtered links as a JSON array of URLs, nothing else.\n\n"
        f"Query: {query}\n"
        f"Country: {country}\n"
        f"Links: {json.dumps(links, ensure_ascii=False, indent=2)}"
    )
    response = call_llm(prompt)
    try:
        filtered = json.loads(response)
        if isinstance(filtered, list):
            return [url for url in filtered if isinstance(url, str)]
    except Exception:
        pass
    filtered = []
    for line in response.splitlines():
        line = line.strip().strip('"')
        if line.startswith('http'):
            filtered.append(line)
    return filtered

def clean_url(url):
    url = url.strip().strip('"').strip("',. ")
    url = re.sub(r'\["\',.\s]+$', '', url)
    return url 