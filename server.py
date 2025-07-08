from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import json
from helpers import filter_links_with_llm, clean_url, get_google_search_links, scrape_products
import re
import os
from mangum import Mangum

app = FastAPI()
handler = Mangum(app)

class SearchRequest(BaseModel):
    query: str
    country: str

class ProductResult(BaseModel):
    link: str
    price: Optional[float] = None
    currency: Optional[str] = None
    productName: str
    country: str
    canonicalUrl: Optional[str] = None
    siteName: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    with open(os.path.join("static", "index.html"), encoding="utf-8") as f:
        return f.read()

@app.post("/search", response_model=List[ProductResult])
async def search_products(request: SearchRequest):
    print(f"[DEBUG] Received request: query={request.query}, country={request.country}")
    query = f"{request.query} in {request.country} only"
    try:
        print(f"[DEBUG] Constructed search query: {query}")
        links = get_google_search_links(query, num_results=100)
        print(f"[DEBUG] Found {len(links)} links from Google search.")
        filtered_links = filter_links_with_llm(request.query, links, request.country)
        print(f"[DEBUG] Filtered down to {len(filtered_links)} links after LLM filtering.")
        cleaned_links = [clean_url(url) for url in filtered_links if url.strip()]
        print(f"[DEBUG] Cleaned links: {cleaned_links}")
        if not cleaned_links:
            print("[DEBUG] No relevant e-commerce links found after cleaning.")
            return []
        results = await scrape_products(cleaned_links)
        print(f"[DEBUG] Results from scrape_products: {results}")
        # If results is a string, parse it into a list of dictionaries
        if isinstance(results, str):
            try:
                json_data = re.search(r"\[\s*{.*?}\s*\]", results, re.DOTALL)
                if json_data:
                    results = json.loads(json_data.group(0))
                else:
                    print("[DEBUG] No valid JSON array found in response.")
                    raise HTTPException(status_code=500, detail="No valid JSON array found in response.")
            except Exception as e:
                print(f"[DEBUG] Failed to parse JSON from LLM response: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to parse JSON from LLM response: {str(e)}")
        final_results = []
        for item in results:
            if isinstance(item, dict) and "price" in item and "link" in item:
                item["productName"] = request.query
                item["country"] = request.country
                final_results.append(item)
        print(f"[DEBUG] Final results: {final_results}")
        return final_results
    except Exception as e:
        print(f"[DEBUG] Exception occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 