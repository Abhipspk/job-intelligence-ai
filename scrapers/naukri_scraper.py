# ============================================================================
# IMPROVED naukri_scraper.py - ACTUALLY GETS COMPANY NAMES
# ============================================================================

import time
from datetime import datetime
import re

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from scrapers.stealth_driver import StealthChromeDriver


def get_driver(self):
    return StealthChromeDriver.create_driver(self.config)



class NaukriScraper:
    def __init__(self, config):
        self.config = config
        self.base_url = "https://www.naukri.com"

    def build_search_url(self, keywords, location, experience=0):
        """Build Naukri search URL"""
        keywords_formatted = '-'.join(keywords.lower().split())
        location_formatted = location.lower().replace(" ", "-")
        
        url = f"{self.base_url}/{keywords_formatted}-jobs-in-{location_formatted}"
        
        # Add experience filter
        if experience == 0:
            url += "?experience=0"
        elif experience == 1:
            url += "?experience=1"
        
        return url

    def get_driver(self):
        """Create Chrome driver with full stealth + background mode"""

        chrome_options = Options()

        # =============================
        # BACKGROUND / HEADLESS MODE
        # =============================
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # =============================
        # STEALTH / ANTI DETECTION
        # =============================
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option(
            "excludeSwitches",
            ["enable-automation", "enable-logging"]
        )
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # =============================
        # PERFORMANCE
        # =============================
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # =============================
        # USER AGENT
        # =============================
        chrome_options.add_argument(
            f'user-agent={self.config["user_agent"]}'
        )

        # =============================
        # SILENT CHROME SERVICE
        # =============================
        service = Service(ChromeDriverManager().install())
        service.creationflags = 0x08000000  # Hide console window

        driver = webdriver.Chrome(
            service=service,
            options=chrome_options
        )

        # =============================
        # HIDE WEBDRIVER FLAG
        # =============================
        driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """)

        return driver


    def scrape_jobs(self, search_params):
        """
        IMPROVED - Scrape jobs from Naukri with better extraction
        """
        jobs = []
        
        url = self.build_search_url(
            search_params['keywords'],
            search_params['location'],
            search_params.get('experience', 0)
        )
        
        print(f"🔍 Scraping Naukri: {url}")
        
        driver = None
        try:
            driver = self.get_driver()
            driver.get(url)
            
            # Wait for jobs to load
            time.sleep(5)
            
            # Scroll to load more jobs
            self.scroll_page(driver, scrolls=3)
            
            # Get page source
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            
            # Find job cards - try multiple selectors
            job_cards = soup.find_all("div", class_="srp-jobtuple-wrapper")
            if not job_cards:
                job_cards = soup.find_all("article", class_="jobTuple")
            if not job_cards:
                job_cards = soup.find_all("div", class_="jobTuple")
            
            print(f"📊 Found {len(job_cards)} job listings")
            
            for card in job_cards:
                try:
                    job = self.extract_job_details(card, page_source)
                    if job:
                        jobs.append(job)
                        print(f"✅ {job['title']} at {job['company']}")
                except Exception as e:
                    print(f"⚠️ Error extracting job: {e}")
                    continue
            
        except Exception as e:
            print(f"❌ Error scraping Naukri: {e}")
        
        finally:
            if driver:
                driver.quit()
        
        return jobs

    def scroll_page(self, driver, scrolls=3):
        """Scroll page to load more jobs"""
        for i in range(scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

    def extract_job_details(self, card, page_source=None):
        """
        IMPROVED - Better extraction with fallbacks
        """
        job = {}
        
        # Title - try multiple approaches
        title_elem = (
            card.find("a", class_="title") or
            card.find("a", class_="jobTitle") or
            card.find("div", class_="title")
        )
        
        if not title_elem:
            return None
        
        job["title"] = self.clean_text(title_elem.text)
        
        # Application link
        if title_elem.get("href"):
            link = title_elem.get("href")
            if not link.startswith("http"):
                link = self.base_url + link
            job["application_link"] = link
        else:
            job["application_link"] = ""
        
        # Company - IMPROVED extraction
        company_elem = (
            card.find("a", class_="subTitle") or
            card.find("a", class_="comp-name") or
            card.find("div", class_="companyInfo") or
            card.find("span", class_="comp-name")
        )
        
        if company_elem:
            company_text = self.clean_text(company_elem.text)
            # Remove "reviews" and ratings
            company_text = re.sub(r'\(.*?\)', '', company_text)
            company_text = re.sub(r'\d+\.\d+', '', company_text)
            job["company"] = company_text.strip()
        else:
            # Try to extract from surrounding text
            job["company"] = self.extract_company_fallback(card)
        
        # Experience
        exp_elem = (
            card.find("span", class_="expwdth") or
            card.find("span", class_="exp") or
            card.find("li", class_="fleft experience")
        )
        job["experience_required"] = self.clean_text(exp_elem.text) if exp_elem else "Not specified"
        
        # Salary
        salary_elem = (
            card.find("span", class_="salaryTxt") or
            card.find("span", class_="salary") or
            card.find("li", class_="fleft salary")
        )
        job["salary"] = self.clean_text(salary_elem.text) if salary_elem else "Not disclosed"
        
        # Location
        location_elem = (
            card.find("span", class_="locWdth") or
            card.find("span", class_="location") or
            card.find("li", class_="fleft location")
        )
        job["location"] = self.clean_text(location_elem.text) if location_elem else "Not specified"
        
        # Skills
        skills_elem = card.find("ul", class_="tags") or card.find("div", class_="tags")
        if skills_elem:
            skills = []
            for li in skills_elem.find_all("li"):
                skill_text = self.clean_text(li.text)
                if skill_text:
                    skills.append(skill_text)
            job["skills_required"] = ", ".join(skills)
        else:
            job["skills_required"] = ""
        
        # Description
        desc_elem = (
            card.find("div", class_="job-description") or
            card.find("div", class_="job_description") or
            card.find("span", class_="job-description")
        )
        job["job_description"] = self.clean_text(desc_elem.text) if desc_elem else ""
        
        # If description is empty, try to get full text from card
        if not job["job_description"]:
            job["job_description"] = self.clean_text(card.text)[:500]
        
        # Metadata
        job["source_platform"] = "Naukri"
        job["posting_date"] = datetime.now().strftime("%Y-%m-%d")
        job["company_type"] = self.guess_company_type(job["company"])
        
        return job

    def extract_company_fallback(self, card):
        """
        Fallback method to extract company name from card text
        """
        card_text = self.clean_text(card.text)
        
        # Look for patterns like "Company Name - Location"
        # or "Company Name (Rating)"
        lines = card_text.split('\n')
        for line in lines:
            line = line.strip()
            # Skip title, experience, salary lines
            if any(skip in line.lower() for skip in ['year', 'month', 'lakh', 'experience', 'days ago']):
                continue
            # If line has reasonable length (3-50 chars), might be company
            if 3 <= len(line) <= 50 and not line.isdigit():
                # Clean up
                line = re.sub(r'\(.*?\)', '', line)  # Remove parentheses
                line = re.sub(r'\d+\.\d+', '', line)  # Remove ratings
                line = line.strip()
                if line:
                    return line
        
        return "Company Not Listed"

    def guess_company_type(self, company_name):
        """
        Guess company type from name
        """
        company_lower = company_name.lower()
        
        # MNCs
        mncs = ['microsoft', 'google', 'amazon', 'meta', 'apple', 'netflix',
                'deloitte', 'accenture', 'pwc', 'ey', 'kpmg',
                'tcs', 'infosys', 'wipro', 'cognizant', 'hcl', 'tech mahindra',
                'ibm', 'oracle', 'sap', 'cisco', 'dell', 'hp']
        
        if any(mnc in company_lower for mnc in mncs):
            return "MNC"
        
        # Startups (common indicators)
        if any(indicator in company_lower for indicator in ['labs', 'technologies', 'solutions', 'tech', 'io', 'ai']):
            return "Startup"
        
        return "Mid-sized"

    def clean_text(self, text):
        """
        Clean extracted text
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove special characters
        text = text.replace('\n', ' ').replace('\r', ' ')
        # Remove emojis and special unicode
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)
        
        return text.strip()