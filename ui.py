import streamlit as st
import pandas as pd
from datetime import datetime
from ddgs import DDGS
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse

# ------------------------------
# Configurations
# ------------------------------
USER_AGENT = "Mozilla/5.0 (compatible; JobScraper/1.0; +https://example.com/bot)"
EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}"

# ------------------------------
# Helper functions
# ------------------------------
def scrape_page(url):
    try:
        res = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        if res.status_code != 200:
            return None

        soup = BeautifulSoup(res.text, "html.parser")
        title_tag = soup.find("h1") or soup.find("title")
        title_text = title_tag.get_text().strip() if title_tag else "N/A"
        description = soup.get_text(separator=" ", strip=True)[:500]
        emails = set(re.findall(EMAIL_PATTERN, res.text))

        return {
            "title": title_text,
            "description": description,
            "emails": ", ".join(emails),
        }
    except Exception:
        return None

def job_scraper(query, max_results=20):
    scraped_data = []
    visited_domains = set()

    with DDGS() as ddg:
        results = ddg.text(query, max_results=max_results)

        for r in results:
            url = r.get("href")
            if not url:
                continue
            domain = urlparse(url).netloc.lower()
            if domain in visited_domains:
                continue
            visited_domains.add(domain)

            page_data = scrape_page(url)
            if page_data:
                page_data.update({
                    "query": query,
                    "url": url,
                    "domain": domain,
                    "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                scraped_data.append(page_data)

    return pd.DataFrame(scraped_data)

# ------------------------------
# Streamlit UI
# ------------------------------
st.title("🔎 Simple Job Scraper")

query = st.text_input("Enter job search query:", "React Native developer jobs")
max_results = st.slider("Number of results", 10, 100, 20)

if st.button("Run Scraper"):
    st.info(f"Searching for: **{query}** ...")
    df = job_scraper(query, max_results)
    
    if df.empty:
        st.warning("No results found.")
    else:
        st.success(f"Found {len(df)} results")
        st.dataframe(df)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, f"jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv")
