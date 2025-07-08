import sys
import asyncio
import json
from link_get import get_google_search_links
from scraper_llm import scrape_products
from llm_call import call_llm
import re
from typing import Optional


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
    # Try to parse JSON array from response
    try:
        filtered = json.loads(response)
        if isinstance(filtered, list):
            return [url for url in filtered if isinstance(url, str)]
    except Exception:
        pass
    # Fallback: try to extract links line by line
    filtered = []
    for line in response.splitlines():
        line = line.strip().strip('"')
        if line.startswith('http'):
            filtered.append(line)
    return filtered

def clean_url(url):
    # Remove trailing quotes, commas, whitespace, and any trailing punctuation not valid in URLs
    url = url.strip().strip('"').strip("',. ")
    # Remove any trailing characters that are not valid in URLs
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
    links = get_google_search_links(query, country=country)
    print(f"Found {len(links)} links. Filtering with LLM...")
    filtered_links = filter_links_with_llm(query, links,country)
    # Clean URLs
    cleaned_links = [clean_url(url) for url in filtered_links if url.strip()]
    print(f"Filtered links ({len(cleaned_links)}):")
    print(json.dumps(cleaned_links, indent=2, ensure_ascii=False))
    if not cleaned_links:
        print("No relevant e-commerce links found.")
        sys.exit(0)
    print("Scraping filtered links and extracting prices with LLM...")
    results = asyncio.run(scrape_products(cleaned_links))
    # print(results,type(results))
    # Filter out results with null price and require product name to contain the query (case-insensitive, ignoring whitespace)
    # If results is a string, parse it into a list of dictionaries
    if isinstance(results, str):
        try:
            json_data = re.search(r"\[\s*{.*?}\s*\]", results, re.DOTALL)
            if json_data:
                results = json.loads(json_data.group(0))
            else:
                print("No valid JSON array found in response.")
                sys.exit(1)
        except Exception as e:
            print("Failed to parse JSON from LLM response:", str(e))
            sys.exit(1)

    # Add productName and country to each item
    final_results = []
    for item in results:
        if isinstance(item, dict) and "price" in item and "link" in item:
            item["productName"] = query
            item["country"] = country
            final_results.append(item)

    # Print the final result
    print(json.dumps(final_results, indent=2, ensure_ascii=False))
