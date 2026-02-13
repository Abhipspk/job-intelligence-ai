# ============================================================================
# linkedin_scraper.py - LINKEDIN JOB SCRAPER
# ============================================================================

import time
from datetime import datetime
import re

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from scrapers.stealth_driver import StealthChromeDriver


def get_driver(self):
    return StealthChromeDriver.create_driver(self.config)



class LinkedInScraper:
    def __init__(self, config):
        self.config = config
        self.base_url = "https://www.linkedin.com/jobs/search"

    def build_search_url(self, keywords, location, experience=0):
        """Build LinkedIn search URL"""
        keywords_encoded = keywords.replace(' ', '%20')
        location_encoded = location.replace(' ', '%20')
        
        # LinkedIn URL format
        url = f"{self.base_url}?keywords={keywords_encoded}&location={location_encoded}"
        
        # Experience level filter (Entry level = f_E=2)
        if experience == 0:
            url += "&f_E=1,2"  # Internship and Entry level
        
        # Sort by date
        url += "&sortBy=DD"
        
        return url

    def get_driver(self):
        """Create stealth background Chrome driver"""

        chrome_options = Options()

        # Background mode
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # Anti detection
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option(
            "excludeSwitches",
            ["enable-automation", "enable-logging"]
        )
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # Performance
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # User agent
        chrome_options.add_argument(
            f'user-agent={self.config["user_agent"]}'
        )

        # Silent driver service
        service = Service(ChromeDriverManager().install())
        service.creationflags = 0x08000000

        driver = webdriver.Chrome(
            service=service,
            options=chrome_options
        )

        return driver


    def scrape_jobs(self, search_params):
        """
        Scrape jobs from LinkedIn
        """
        jobs = []
        
        url = self.build_search_url(
            search_params['keywords'],
            search_params['location'],
            search_params.get('experience', 0)
        )
        
        print(f"🔍 Scraping LinkedIn: {url}")
        
        driver = None
        try:
            driver = self.get_driver()
            driver.get(url)
            
            # Wait for jobs to load
            time.sleep(5)
            
            # Scroll to load more
            self.scroll_page(driver, scrolls=2)
            
            # Get page source
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            
            # Find job cards
            job_cards = soup.find_all("div", class_="base-card")
            if not job_cards:
                job_cards = soup.find_all("li", class_="jobs-search-results__list-item")
            
            print(f"📊 Found {len(job_cards)} LinkedIn job listings")
            
            for card in job_cards:
                try:
                    job = self.extract_job_details(card)
                    if job:
                        jobs.append(job)
                        print(f"✅ {job['title']} at {job['company']}")
                except Exception as e:
                    print(f"⚠️ Error: {e}")
                    continue
            
        except Exception as e:
            print(f"❌ LinkedIn scraping error: {e}")
        
        finally:
            if driver:
                driver.quit()
        
        return jobs

    def scroll_page(self, driver, scrolls=2):
        """Scroll to load more jobs"""
        for i in range(scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)

    def extract_job_details(self, card):
        """Extract job details from card"""
        job = {}
        
        # Title
        title_elem = card.find("h3", class_="base-search-card__title")
        if not title_elem:
            title_elem = card.find("a", class_="base-card__full-link")
        
        if not title_elem:
            return None
        
        job["title"] = title_elem.text.strip()
        
        # Application link
        link_elem = card.find("a", class_="base-card__full-link")
        if link_elem and link_elem.get("href"):
            job["application_link"] = link_elem.get("href")
        else:
            job["application_link"] = ""
        
        # Company
        company_elem = card.find("h4", class_="base-search-card__subtitle")
        if not company_elem:
            company_elem = card.find("a", class_="hidden-nested-link")
        
        job["company"] = company_elem.text.strip() if company_elem else "Company Not Listed"
        
        # Location
        location_elem = card.find("span", class_="job-search-card__location")
        job["location"] = location_elem.text.strip() if location_elem else "Not specified"
        
        # Posted date
        date_elem = card.find("time", class_="job-search-card__listdate")
        if not date_elem:
            date_elem = card.find("time")
        
        if date_elem:
            job["posting_date"] = date_elem.get("datetime", datetime.now().strftime("%Y-%m-%d"))
        else:
            job["posting_date"] = datetime.now().strftime("%Y-%m-%d")
        
        # Description (limited from card)
        desc_elem = card.find("p", class_="base-search-card__snippet")
        job["job_description"] = desc_elem.text.strip() if desc_elem else ""
        
        # Skills (not usually in cards)
        job["skills_required"] = ""
        
        # Experience (try to extract from title/description)
        job["experience_required"] = self.extract_experience(job)
        
        # Salary
        job["salary"] = "Not disclosed"
        
        # Metadata
        job["source_platform"] = "LinkedIn"
        job["company_type"] = "Unknown"
        
        return job

    def extract_experience(self, job):
        """Extract experience from title/description"""
        text = f"{job['title']} {job.get('job_description', '')}".lower()
        
        # Fresher indicators
        if any(word in text for word in ['fresher', 'entry level', 'graduate', 'intern']):
            return "0-1 years (Fresher friendly)"
        
        # Try to find numbers
        years = re.findall(r'(\d+)\s*(?:to|-|–)\s*(\d+)\s*(?:year|yr)', text)
        if years:
            return f"{years[0][0]}-{years[0][1]} years"
        
        return "Not specified"