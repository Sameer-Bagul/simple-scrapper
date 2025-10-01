from ddgs import DDGS
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from urllib.parse import urlparse
from datetime import datetime

# ------------------------------
# Configurations
# ------------------------------
MAX_RESULTS = 50  # number of links to fetch per query
USER_AGENT = "Mozilla/5.0 (compatible; JobScraper/1.0; +https://example.com/bot)"
EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}"

# ------------------------------
# Global storage
# ------------------------------
scraped_data = []
visited_domains = set()

# ------------------------------
# Helper functions
# ------------------------------
def scrape_page(url):
    """Scrape a page to extract title, description, and emails."""
    try:
        res = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        if res.status_code != 200:
            return None

        soup = BeautifulSoup(res.text, "html.parser")
        # Page title or fallback
        title_tag = soup.find("h1") or soup.find("title")
        title_text = title_tag.get_text().strip() if title_tag else "N/A"

        # Short description snippet
        description = soup.get_text(separator=" ", strip=True)[:500]

        # Extract emails
        emails = set(re.findall(EMAIL_PATTERN, res.text))

        # Optional: try to extract company, location, salary heuristically
        # (requires site-specific parsing for better accuracy)
        company = "N/A"
        location = "N/A"
        salary = "N/A"

        return {
            "title": title_text,
            "description": description,
            "emails": ", ".join(emails),
            "company": company,
            "location": location,
            "salary": salary
        }

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

# ------------------------------
# Main Scraper Function
# ------------------------------
def job_scraper(query, max_results=MAX_RESULTS):
    """
    Main automated scraper.
    1. Searches DuckDuckGo for the query
    2. Deduplicates domains
    3. Scrapes each page and saves structured data to CSV
    """
    with DDGS() as ddg:
        results = ddg.text(query, max_results=max_results)
        if not results:
            print("No search results found.")
            return

        for r in results:
            url = r['href']
            if not url:
                continue
            domain = urlparse(url).netloc.lower()
            if domain in visited_domains:
                continue  # skip already scraped domains
            visited_domains.add(domain)

            print(f"Scraping: {url}")
            page_data = scrape_page(url)
            if page_data:
                page_data.update({
                    "query": query,
                    "url": url,
                    "domain": domain,
                    "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                scraped_data.append(page_data)

        # Save to CSV
        df = pd.DataFrame(scraped_data)
        df.to_csv("jobs_auto.csv", index=False)
        print("✅ Data saved to jobs_auto.csv")

# ------------------------------
# Run Example
# ------------------------------
if __name__ == "__main__":
    search_query = "React Native developer jobs"  # Example query
    job_scraper(search_query, max_results=50)
