# ============================================================================
# FILE: scrapers/company_scraper_v2.py
# ADVANCED MULTI THREAD COMPANY SCRAPER (LIST JSON COMPATIBLE)
# ============================================================================

import json
import os
import time
import random
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed


class CompanyScraperV2:

    # ==========================================================
    # INIT
    # ==========================================================
    def __init__(self, scraping_config, company_config, job_sources):

        self.config = scraping_config
        self.company_config = company_config
        self.job_sources = job_sources

        json_path = job_sources["company_pages"]["companies_json_path"]

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 🔥 FIX FOR LIST JSON
        if isinstance(data, list):
            self.companies = data
        else:
            self.companies = data.get("hyderabad_companies", [])

        print(f"✅ Loaded {len(self.companies)} companies")


    # ==========================================================
    # MAIN SCRAPE CONTROLLER
    # ==========================================================
    def scrape_all_companies(self, priority_filter=None):

        companies = self.filter_companies(priority_filter)

        print(f"🏢 Companies to scrape: {len(companies)}")

        results = []

        max_threads = self.config.get("max_threads", 5)

        with ThreadPoolExecutor(max_workers=max_threads) as executor:

            future_map = {
                executor.submit(self.safe_scrape_company, c): c
                for c in companies
            }

            for future in as_completed(future_map):
                try:
                    jobs = future.result()
                    if jobs:
                        results.extend(jobs)
                except Exception as e:
                    company = future_map[future]
                    print(f"❌ Thread error {company.get('name')} → {e}")

        print(f"✅ Company jobs scraped: {len(results)}")
        return results

    # ==========================================================
    # PRIORITY FILTER
    # ==========================================================
    def filter_companies(self, priority_filter):

        if not priority_filter:
            return self.companies

        return [
            c for c in self.companies
            if c.get("priority", 2) == priority_filter
        ]

    # ==========================================================
    # SAFE SCRAPE (RETRY LOGIC)
    # ==========================================================
    def safe_scrape_company(self, company):

        retries = self.config.get("max_retries", 3)

        for attempt in range(retries):

            try:
                return self.scrape_company(company)

            except Exception as e:
                print(
                    f"⚠ Retry {attempt+1}/{retries} "
                    f"{company.get('name')} → {e}"
                )
                time.sleep(2)

        return []

    # ==========================================================
    # CORE SCRAPER
    # ==========================================================
    def scrape_company(self, company):

        headers = {
            "User-Agent": self.config["user_agent"]
        }

        # Random delay (Anti-bot protection)
        delay = random.uniform(
            self.config.get("random_delay_min", 1),
            self.config.get("random_delay_max", 3)
        )
        time.sleep(delay)

        url = company.get("career_url") or company.get("url")

        if not url:
            return []

        response = requests.get(
            url,
            headers=headers,
            timeout=self.config.get("timeout", 20)
        )

        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        jobs = []

        for link in soup.find_all("a"):

            text = link.get_text(strip=True)

            if self.is_job_text(text):

                jobs.append(
                    self.build_job(company, text, link)
                )

        print(f"✅ {company.get('name')} → {len(jobs)} jobs")

        return jobs

    # ==========================================================
    # JOB TEXT DETECTION
    # ==========================================================
    def is_job_text(self, text):

        if not text or len(text) < 5:
            return False

        keywords = self.company_config.get("job_keywords", [
            "engineer", "analyst", "developer",
            "data", "sql", "python", "bi"
        ])

        return any(k in text.lower() for k in keywords)

    # ==========================================================
    # BUILD JOB OBJECT
    # ==========================================================
    def build_job(self, company, text, link):

        href = link.get("href", "")

        # Handle relative URLs
        if href and href.startswith("/"):
            base = company.get("career_url", "")
            href = base.rstrip("/") + href

        return {
            "title": text,
            "company": company.get("name", "Unknown"),
            "location": company.get("location", "Hyderabad"),
            "job_description": text,
            "skills_required": "",
            "experience_required": "0-2 years",
            "application_link": href,
            "source_platform": "Company Career Page",
            "company_type": company.get("type", "IT")
        }
