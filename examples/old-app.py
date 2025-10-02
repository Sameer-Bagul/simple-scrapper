# ------------------------------
# Ultimate Job Scraper (DDGS-powered)
# ------------------------------

from ddgs import DDGS   # Correct new package
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from urllib.parse import urlparse
from datetime import datetime
import sys

MAX_RESULTS = 50
USER_AGENT = "Mozilla/5.0 (compatible; JobScraper/1.0; +https://example.com/bot)"
EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}"

scraped_data = []
visited_domains = set()

def scrape_page(url: str) -> dict | None:
    """Scrape a page to extract job title, description, and emails."""
    try:
        res = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        if res.status_code != 200:
            return None

        soup = BeautifulSoup(res.text, "lxml")
        title_tag = soup.find("h1") or soup.find("title")
        title_text = title_tag.get_text(strip=True) if title_tag else "N/A"
        description = soup.get_text(separator=" ", strip=True)[:500]
        emails = set(re.findall(EMAIL_PATTERN, res.text))

        return {
            "title": title_text,
            "description": description,
            "emails": ", ".join(emails) if emails else "N/A",
            "company": "N/A",
            "location": "N/A",
            "salary": "N/A"
        }
    except Exception as e:
        print(f"⚠️ Error scraping {url}: {e}")
        return None

def job_scraper(query: str, max_results: int = MAX_RESULTS):
    with DDGS() as ddg:
        results = list(ddg.text(query, max_results=max_results))  # ensure list
        if not results:
            print("❌ No search results found.")
            return

        for r in results:
            url = r.get("href")
            if not url:
                continue

            domain = urlparse(url).netloc.lower()
            if domain in visited_domains:
                continue
            visited_domains.add(domain)

            print(f"🔎 Scraping: {url}")
            page_data = scrape_page(url)
            if page_data:
                page_data.update({
                    "query": query,
                    "url": url,
                    "domain": domain,
                    "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                scraped_data.append(page_data)

        if scraped_data:
            df = pd.DataFrame(scraped_data)
            filename = f"jobs_auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False)
            print(f"✅ Data saved to {filename}")
        else:
            print("⚠️ No data scraped.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Please provide a search query.")
        print("👉 Example: python app.py 'React Native developer jobs'")
        sys.exit(1)

    search_query = " ".join(sys.argv[1:])
    print(f"🔍 Searching for jobs: {search_query}")
    job_scraper(search_query, max_results=50)
