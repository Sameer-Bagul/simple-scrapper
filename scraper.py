import asyncio
import httpx
import re
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime
from ddgs import DDGS

USER_AGENT = "Mozilla/5.0 (compatible; JobScraper/3.0)"
EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}"
JOB_KEYWORDS = ["job", "apply", "hiring", "career", "vacancy", "salary", "position"]

def clean_obfuscated_emails(text: str):
    """Normalize common obfuscations like [at], (dot)."""
    text = text.replace("[at]", "@").replace("(at)", "@").replace(" at ", "@")
    text = text.replace("[dot]", ".").replace("(dot)", ".").replace(" dot ", ".")
    return text

async def fetch_page(client, url):
    try:
        res = await client.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        if res.status_code != 200:
            return None
        return res.text
    except Exception:
        return None

def extract_page_data(html, url):
    soup = BeautifulSoup(html, "html.parser")

    # Title
    title_tag = soup.find("h1") or soup.find("title")
    title_text = title_tag.get_text().strip() if title_tag else "N/A"

    # Description
    description = soup.get_text(separator=" ", strip=True)[:800]

    # Emails
    mailto_links = [a['href'].replace("mailto:", "") for a in soup.find_all('a', href=True) if a['href'].startswith("mailto:")]
    regex_emails = re.findall(EMAIL_PATTERN, clean_obfuscated_emails(html))
    emails = set(mailto_links + regex_emails)

    # Heuristics
    is_job_page = any(keyword in description.lower() for keyword in JOB_KEYWORDS)
    company = "N/A"
    location = "N/A"
    salary = "N/A"

    return {
        "title": title_text,
        "description": description,
        "emails": ", ".join(emails),
        "company": company,
        "location": location,
        "salary": salary,
        "is_job": is_job_page,
        "url": url,
        "domain": urlparse(url).netloc.lower(),
        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

async def scrape_jobs(query, max_results=30):
    scraped_data, visited_domains = [], set()

    # DuckDuckGo search
    with DDGS() as ddg:
        results = ddg.text(f"{query} jobs", max_results=max_results)

    async with httpx.AsyncClient() as client:
        tasks, urls = [], []
        for r in results:
            url = r.get("href")
            if not url:
                continue
            domain = urlparse(url).netloc.lower()
            if domain in visited_domains:
                continue
            visited_domains.add(domain)
            urls.append(url)
            tasks.append(fetch_page(client, url))

        responses = await asyncio.gather(*tasks)

        for url, html in zip(urls, responses):
            if not html:
                continue
            data = extract_page_data(html, url)
            if data["is_job"]:  # filter only job-like pages
                scraped_data.append(data)

    return pd.DataFrame(scraped_data)
