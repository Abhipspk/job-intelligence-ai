# ============================================================================
# COMPANY SCRAPER V3 — HYBRID (REQUESTS + SELENIUM FALLBACK)
# ============================================================================

import json
import os
import time
import random
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class CompanyScraperV3:

    # ==========================================================
    # INIT
    # ==========================================================
    def __init__(self, scraping_config, company_config, companies_json_path):

        self.config = scraping_config
        self.company_config = company_config

        with open(companies_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Supports both formats
        if isinstance(data, list):
            self.companies = data
        else:
            self.companies = data.get("hyderabad_companies", [])

        print(f"✅ Loaded {len(self.companies)} companies (Hybrid Mode)")

    # ==========================================================
    # THREAD SCRAPER
    # ==========================================================
    def scrape_all_companies(self, priority_filter=None):

        companies = self.filter_companies(priority_filter)

        results = []

        with ThreadPoolExecutor(max_workers=self.config["max_threads"]) as executor:

            futures = {
                executor.submit(self.smart_scrape_company, c): c
                for c in companies
            }

            for future in as_completed(futures):
                jobs = future.result()
                if jobs:
                    results.extend(jobs)

        print(f"✅ Company jobs scraped: {len(results)}")
        return results

    # ==========================================================
    # SMART SCRAPER
    # ==========================================================
    def smart_scrape_company(self, company):

        try:
            # Try fast method first
            jobs = self.requests_scrape(company)

            if jobs:
                return jobs

            # If nothing found → Selenium fallback
            return self.selenium_scrape(company)

        except Exception as e:
            print(f"❌ {company['name']} failed: {e}")
            return []

    # ==========================================================
    # REQUESTS SCRAPER (FAST)
    # ==========================================================
    def requests_scrape(self, company):

        url = company.get("career_url") or company.get("url")

        if not url:
            return []

        headers = {
            "User-Agent": self.config["user_agent"]
        }

        try:
            res = requests.get(
                url,
                headers=headers,
                timeout=self.config["timeout"]
            )

            if res.status_code != 200:
                return []

            soup = BeautifulSoup(res.text, "html.parser")

            jobs = []

            for a in soup.find_all("a"):

                text = a.get_text(strip=True)

                if self.is_job_text(text):

                    jobs.append(self.build_job(company, text, a.get("href")))

            if jobs:
                print(f"⚡ Requests success → {company['name']} ({len(jobs)})")

            return jobs

        except:
            return []

    # ==========================================================
    # SELENIUM SCRAPER (FALLBACK)
    # ==========================================================
    def selenium_scrape(self, company):

        url = company.get("career_url") or company.get("url")

        if not url:
            return []

        driver = None

        try:
            driver = self.get_driver()
            driver.get(url)

            time.sleep(random.uniform(4, 7))

            soup = BeautifulSoup(driver.page_source, "html.parser")

            jobs = []

            for a in soup.find_all("a"):

                text = a.get_text(strip=True)

                if self.is_job_text(text):

                    jobs.append(self.build_job(company, text, a.get("href")))

            if jobs:
                print(f"🤖 Selenium success → {company['name']} ({len(jobs)})")

            return jobs

        except Exception as e:
            print(f"⚠ Selenium error {company['name']}: {e}")
            return []

        finally:
            if driver:
                driver.quit()

    # ==========================================================
    # DRIVER (HEADLESS SAFE)
    # ==========================================================
    def get_driver(self):

        chrome_options = Options()

        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--log-level=3")

        chrome_options.add_argument(
            f"user-agent={self.config['user_agent']}"
        )

        return webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

    # ==========================================================
    # FILTER
    # ==========================================================
    def filter_companies(self, priority_filter):

        if not priority_filter:
            return self.companies

        return [
            c for c in self.companies
            if c.get("priority", 2) == priority_filter
        ]

    # ==========================================================
    # JOB TEXT CHECK
    # ==========================================================
    def is_job_text(self, text):

        if not text or len(text) < 6:
            return False

        keywords = self.company_config["job_keywords"]

        return any(k in text.lower() for k in keywords)

    # ==========================================================
    # BUILD JOB
    # ==========================================================
    def build_job(self, company, text, href):

        return {
            "title": text,
            "company": company["name"],
            "location": company.get("location", "Hyderabad"),
            "job_description": text,
            "skills_required": "",
            "experience_required": "0-2 years",
            "application_link": href or "",
            "source_platform": "Company Career Page",
            "company_type": company.get("type", "IT")
        }
