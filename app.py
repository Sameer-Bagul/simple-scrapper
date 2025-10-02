import streamlit as st
import asyncio
from scraper import scrape_jobs
from datetime import datetime

st.set_page_config(page_title="Job Email Scraper", layout="wide")

st.title("💼 Job Email Scraper")
st.write("Enter a job role or keyword, and this app will search job sites for listings + extract contact emails.")

query = st.text_input("🔍 Enter job role (e.g. MERN Developer, React Native jobs)", "MERN stack developer")
max_results = st.slider("Max results to fetch", 10, 100, 30)

if st.button("Start Scraping"):
    with st.spinner("Scraping in progress... please wait ⏳"):
        df = asyncio.run(scrape_jobs(query, max_results))
        if df.empty:
            st.warning("No job listings found. Try a broader query.")
        else:
            st.success(f"✅ Found {len(df)} job listings with emails")
            st.dataframe(df)

            # Save CSV
            filename = f"jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False)
            st.download_button("📥 Download CSV", data=df.to_csv(index=False), file_name=filename, mime="text/csv")
