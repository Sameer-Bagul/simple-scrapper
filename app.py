import streamlit as st
import asyncio
import pandas as pd
from datetime import datetime

from scraper_careers import scrape_careers  # Import the async scraper we just created

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Ultimate Job Scraper", layout="wide")

st.title("🕵️‍♂️ Ultimate Job & Career Page Scraper")
st.markdown("""
This app searches for career pages, job postings, and contact emails across the web for a given query.
It probes multiple domains, checks common career/contact paths, and extracts emails automatically.
""")

# Sidebar inputs
st.sidebar.header("Search Settings")
query = st.sidebar.text_input("Search Query", "MERN stack developer")
max_results = st.sidebar.slider("Max DuckDuckGo Results", 20, 200, 60)
run_scrape = st.sidebar.button("Start Scraping")

# Display spinner while running
if run_scrape:
    if not query.strip():
        st.error("Please enter a valid search query!")
    else:
        st.info(f"🔍 Searching for domains & career pages for: **{query}** ...")
        with st.spinner("Scraping in progress... This may take a few minutes depending on results."):

            # Run async scraping
            df = asyncio.run(scrape_careers(query, max_results=max_results))

            if df.empty:
                st.warning("No results found.")
            else:
                st.success(f"✅ Found {len(df)} pages!")

                # Highlight job-like pages
                job_df = df[df["is_job_like"]]
                other_df = df[~df["is_job_like"]]

                st.subheader("📌 Job-like Pages")
                st.dataframe(job_df[["domain", "url", "title", "emails"]].reset_index(drop=True))

                st.subheader("📄 Other Pages")
                st.dataframe(other_df[["domain", "url", "title", "emails"]].reset_index(drop=True))

                # Download CSV
                csv_file = df.to_csv(index=False).encode("utf-8")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    label="⬇️ Download All Results as CSV",
                    data=csv_file,
                    file_name=f"job_scrape_{timestamp}.csv",
                    mime="text/csv"
                )

st.sidebar.markdown("---")
st.sidebar.markdown("Made with ❤️ by Sam. Scrape responsibly and respect site rules.")
