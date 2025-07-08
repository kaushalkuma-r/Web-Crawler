import sys
import asyncio
import json
from link_get import get_google_search_links
from scraper_llm import scrape_products
from llm_call import call_llm
import re

BATCH_SIZE = 15
MIN_RESULTS = 20  # Set N here

def filter_links_with_llm(query, links,country):
    prompt = (
        f"You are an expert e-commerce assistant. "
        f"Given the product search query: '{query}', and the following list of URLs from a web search, "
        f"return ONLY the links that are actual e-commerce product pages where a user can buy the product. "
        f"Exclude links to forums, news, Wikipedia, YouTube, Reddit, or any non-shopping sites. "
        f"Make sure that links do not belong to any different country like they might have different country domain so make sure of that."
        f"This is the country {country}"
        f"Return the filtered links as a JSON array of URLs, nothing else.\n\n"
        f"Query: {query}\n"
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
    url = re.sub(r'["\',.\s]+$', '', url)
    return url

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        query = sys.argv[1]
        country = sys.argv[2]
    else:
        query = input("Enter product query: ")
        country = input("Enter country code (ISO-2): ")

    print(f"Searching for '{query}' in country '{country}'...")
    links = get_google_search_links(query,country=country)
    print(f"Found {len(links)} links. Filtering with LLM...")
    filtered_links = filter_links_with_llm(query, links,country)
    cleaned_links = [clean_url(url) for url in filtered_links if url.strip()]
    print(f"Filtered links ({len(cleaned_links)}):")
    print(json.dumps(cleaned_links, indent=2, ensure_ascii=False))

    seen = set()
    final_results = []
    i = 0
    while len(final_results) < MIN_RESULTS and i < len(cleaned_links):
        batch = cleaned_links[i:i+BATCH_SIZE]
        print(f"Processing batch {i//BATCH_SIZE + 1}: {batch}")
        results = asyncio.run(scrape_products(batch))
        # Parse and enrich results
        for item in results:
            if isinstance(item, dict) and "price" in item and "link" in item and item["price"] is not None:
                key = (item["link"], item["price"], item.get("currency"))
                if key not in seen:
                    item["productName"] = query
                    item["country"] = country
                    final_results.append(item)
                    seen.add(key)
        i += BATCH_SIZE
        print(f"Current unique results: {len(final_results)}")
        if i >= len(cleaned_links):
            print("No more links to process.")
            break

    print(json.dumps(final_results, indent=2, ensure_ascii=False))