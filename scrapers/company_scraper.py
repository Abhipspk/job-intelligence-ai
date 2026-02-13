# ============================================================================
# FILE: scrapers/company_scraper.py (PRODUCTION THREAD VERSION)
# ============================================================================

import json
import os
import time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed


class CompanyScraper:

    # ==========================================================
    # INIT
    # ==========================================================
    def __init__(self, scraping_config):

        self.config = scraping_config

        json_path = os.path.join("data", "companies.json")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.companies = data["hyderabad_companies"]

        # Thread count config
        self.max_threads = self.config.get("max_threads", 8)

    # ==========================================================
    # MAIN MULTI THREAD SCRAPER
    # ==========================================================
    def scrape_all_companies(self):

        all_jobs = []

        print(f"\n🏢 Multi-thread scraping {len(self.companies)} companies...")
        print(f"⚡ Threads: {self.max_threads}")

        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:

            future_to_company = {
                executor.submit(self.scrape_company_safe, company): company
                for company in self.companies
            }

            for future in as_completed(future_to_company):

                company = future_to_company[future]

                try:
                    jobs = future.result()

                    if jobs:
                        all_jobs.extend(jobs)
                        print(f"✅ {company['name']} → {len(jobs)} jobs")

                except Exception as e:
                    print(f"❌ Thread Error {company['name']}: {e}")

        print(f"🏁 Company scraping finished → {len(all_jobs)} jobs collected\n")

        return all_jobs

    # ==========================================================
    # SAFE WRAPPER (Retries)
    # ==========================================================
    def scrape_company_safe(self, company):

        retries = self.config.get("max_retries", 2)

        for attempt in range(retries):

            try:
                return self.scrape_company(company)

            except Exception as e:
                if attempt == retries - 1:
                    print(f"❌ Failed {company['name']} after retries: {e}")
                    return []
                time.sleep(2)

        return []

    # ==========================================================
    # SINGLE COMPANY SCRAPER
    # ==========================================================
    def scrape_company(self, company):

        headers = {
            "User-Agent": self.config["user_agent"]
        }

        response = requests.get(
            company["career_url"],
            headers=headers,
            timeout=self.config["timeout"]
        )

        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        jobs = []

        keywords = [
            "engineer", "analyst", "data", "developer",
            "sql", "python", "etl", "bi", "report"
        ]

        for link in soup.find_all("a"):

            text = link.get_text(strip=True)

            if not text:
                continue

            if len(text) < 6:
                continue

            if any(keyword in text.lower() for keyword in keywords):

                job = self.normalize_job(company, text, link.get("href"))
                jobs.append(job)

        return jobs

    # ==========================================================
    # NORMALIZE JOB FORMAT
    # ==========================================================
    def normalize_job(self, company, title, link):

        return {
            "title": title[:150],
            "company": company["name"],
            "location": "Hyderabad",
            "job_description": title,
            "skills_required": "",
            "experience_required": "0-2 years",
            "application_link": link if link else "",
            "source_platform": "Company Career Page",
            "company_type": company.get("company_type", "IT")
        }
