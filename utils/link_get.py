import os
from typing import List
from googlesearch import search

def get_google_search_links(query: str, num_results: int = 10) -> List[str]:
    links = []
    for url in search(query, num_results=num_results, lang="en"):
        links.append(url)
    return links 