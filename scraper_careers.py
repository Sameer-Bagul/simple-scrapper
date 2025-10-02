# scraper_careers.py
# Async career/contact page finder + email extractor
# Usage: python scraper_careers.py "MERN stack" --max 80

import asyncio
import argparse
import re
from datetime import datetime
from urllib.parse import urlparse, urljoin

import httpx
import pandas as pd
from bs4 import BeautifulSoup
from ddgs import DDGS

# -----------------------------
# Config
# -----------------------------
USER_AGENT = "Mozilla/5.0 (compatible; CareerFinder/1.0; +https://example.com/bot)"
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.I)
OBFUSCATIONS = [
    (r"\[at\]|\(at\)|\s+at\s+", "@"),
    (r"\[dot\]|\(dot\)|\s+dot\s+", "."),
    (r"\s*\[underscore\]\s*", "_"),
]
JOB_KEYWORDS = ["job", "jobs", "career", "careers", "apply", "hiring", "vacancy", "vacancies", "open position", "openings", "join our team"]

# candidate paths to probe on each domain (career paths + contact)
COMMON_PATHS = [
    "/careers", "/careers/", "/jobs", "/jobs/", "/about/careers", "/company/careers",
    "/careers.html", "/careers.php", "/join-us", "/join-us/", "/vacancies", "/open-positions",
    "/work-with-us", "/about-us/careers", "/team", "/about", "/contact", "/contact-us"
]

# concurrency
SEM_MAX = 20
TIMEOUT = 12

# -----------------------------
# Utilities
# -----------------------------
def clean_obfuscation(text: str) -> str:
    s = text
    for pattern, repl in OBFUSCATIONS:
        s = re.sub(pattern, repl, s, flags=re.I)
    return s

def extract_emails_from_html(html: str) -> list:
    emails = set()
    # mailto links
    try:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select('a[href^="mailto:"]'):
            addr = a.get("href").split("mailto:")[1].split("?")[0].strip()
            if addr:
                emails.add(addr)
    except Exception:
        pass

    # regex on cleaned text and raw html
    cleaned = clean_obfuscation(html)
    for m in EMAIL_RE.findall(cleaned):
        emails.add(m.strip().lower())

    return sorted(emails)

def is_job_like(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in JOB_KEYWORDS)

# -----------------------------
# Async fetch/probe
# -----------------------------
sem = asyncio.Semaphore(SEM_MAX)

async def fetch(client: httpx.AsyncClient, url: str) -> tuple[str, int, str]:
    """Return (url, status_code, text) or (url, 0, '') on failure."""
    try:
        async with sem:
            r = await client.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT, follow_redirects=True)
            return (url, r.status_code, r.text)
    except Exception:
        return (url, 0, "")

async def probe_domain(client: httpx.AsyncClient, domain: str) -> list:
    """Probe common paths on a domain; return list of (url, status, html)."""
    scheme = "https"
    base = f"{scheme}://{domain}"
    urls = [base] + [urljoin(base, p) for p in COMMON_PATHS]
    tasks = [fetch(client, u) for u in urls]
    results = await asyncio.gather(*tasks)
    # filter successful pages (200)
    return [r for r in results if r[1] == 200 and r[2]]

# -----------------------------
# Search + discovery
# -----------------------------
def ddg_search_domains(query: str, max_results: int = 50) -> set:
    """Use ddgs to search many query patterns and collect domains."""
    domains = set()
    # query templates to broaden discovery
    templates = [
        "{q} jobs",
        "{q} careers",
        "{q} \"career\"",
        "{q} \"apply\"",
        "{q} \"hiring\"",
        "{q} site:linkedin.com {q}",
        "{q} site:indeed.com {q}",
        "{q} site:glassdoor.com {q}"
    ]
    with DDGS() as ddg:
        for t in templates:
            q = t.format(q=query)
            try:
                for item in ddg.text(q, max_results=max_results//len(templates)):
                    href = item.get("href") or item.get("link")
                    if not href:
                        continue
                    parsed = urlparse(href)
                    domain = parsed.netloc.lower()
                    if domain:
                        domains.add(domain)
            except Exception:
                continue
    return domains

# -----------------------------
# Higher-level scraping flow
# -----------------------------
async def scrape_careers(query: str, max_results: int = 60) -> pd.DataFrame:
    """Discover domains, probe career/contact paths, extract emails & metadata."""
    print(f"[+] Searching for domains for query: {query}")
    domains = ddg_search_domains(query, max_results=max_results)
    print(f"[+] Discovered {len(domains)} unique domains. Probing common career/contact paths...")

    async with httpx.AsyncClient() as client:
        tasks = [probe_domain(client, d) for d in domains]
        probe_results = await asyncio.gather(*tasks)

    rows = []
    for domain, probes in zip(domains, probe_results):
        # probes is list of (url, status, html)
        for url, status, html in probes:
            title = ""
            snippet = ""
            try:
                soup = BeautifulSoup(html, "html.parser")
                title_tag = soup.find("h1") or soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else ""
                snippet = soup.get_text(separator=" ", strip=True)[:800]
            except Exception:
                pass

            emails = extract_emails_from_html(html)
            job_like = is_job_like(snippet) or is_job_like(title)

            rows.append({
                "domain": domain,
                "url": url,
                "status": status,
                "title": title or "N/A",
                "snippet": snippet,
                "is_job_like": job_like,
                "emails": ";".join(emails) if emails else "",
                "scraped_at": datetime.now().isoformat()
            })
    df = pd.DataFrame(rows)
    # prefer job_like pages first
    df = df.sort_values(by=["is_job_like", "domain"], ascending=[False, True])
    return df

# -----------------------------
# CLI runner
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Discover career/contact pages and extract emails.")
    parser.add_argument("query", help="Search query e.g. 'MERN stack'")
    parser.add_argument("--max", type=int, default=60, help="Rough maximum number of DDG results to consider")
    parser.add_argument("--out", type=str, default=None, help="CSV output filename (auto if not set)")
    args = parser.parse_args()

    df = asyncio.run(scrape_careers(args.query, max_results=args.max))
    if args.out:
        out_file = args.out
    else:
        out_file = f"careers_{args.query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(out_file, index=False)
    print(f"[+] Saved {len(df)} rows to {out_file}")

if __name__ == "__main__":
    main()
