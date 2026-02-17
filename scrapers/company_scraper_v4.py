"""
=============================================================================
COMPANY SCRAPER V4 - SMART JOB DETECTION (NO GARBAGE)
=============================================================================
Fixes from V3:
1. Minimum title length of 15 chars (no "Accessibility", "Shop" etc.)
2. Blacklist nav words (accessibility, privacy, cookie, shop, about, blog)
3. Requires title to look like an actual job (has a job-like word in it)
4. Better URL construction for relative links
5. Deduplication within each company
6. Proper threading
=============================================================================
"""

import re
import json
import time
import random
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime


# =============================================================================
# CONSTANTS
# =============================================================================

# A real job title should contain at least ONE of these words
REAL_JOB_INDICATORS = {
    "analyst", "engineer", "developer", "manager", "architect", "scientist",
    "intern", "associate", "consultant", "specialist", "coordinator", "officer",
    "executive", "lead", "senior", "junior", "trainee", "fresher",
    "director", "head", "vp", "president", "data", "sql", "python",
    "software", "business", "system", "cloud", "devops", "qa", "testing",
    "full stack", "backend", "frontend", "mobile", "ios", "android",
    "machine learning", "artificial intelligence", "deep learning",
    "product", "project", "program", "operations", "finance", "marketing",
    "sales", "human resources", "hr", "mis", "reporting", "bi", "etl"
}

# Nav links / page sections that are NOT jobs (blacklist)
NAV_BLACKLIST = {
    "accessibility", "privacy", "cookie", "cookies", "terms",
    "login", "sign in", "register", "about us", "contact us",
    "home", "careers", "jobs", "search", "apply now", "submit",
    "back", "next", "previous", "more", "view all", "see all",
    "refurbished", "shop", "store", "buy", "cart", "checkout",
    "blog", "news", "press", "media", "investors", "sitemap",
    "faqs", "faq", "help", "support", "feedback", "survey",
    "linkedin", "twitter", "facebook", "instagram", "youtube",
    "facebook", "glassdoor", "indeed", "naukri",
    "our culture", "our values", "diversity", "inclusion",
    "benefits", "perks", "life at", "meet our team",
    "learn more", "read more", "find out", "explore",
    "global", "worldwide", "international", "locations",
    "zambia", "kenya", "nigeria", "ghana",  # Country names appearing as nav
}

TARGET_KEYWORDS = [
    "data analyst", "data engineer", "data scientist", "sql developer",
    "business analyst", "system engineer", "mis executive", "mis analyst",
    "reporting analyst", "bi analyst", "bi developer",
    "power bi", "tableau", "python developer", "analytics",
    "etl developer", "fresher", "entry level", "junior", "trainee",
    "associate analyst", "data analytics", "junior analyst",
    "software engineer", "software developer",  # Broad catch for tech freshers
]


def is_valid_job_title(title: str) -> bool:
    """
    Determine if a text string looks like an actual job title.
    Returns False for nav links, page sections, etc.
    """
    if not title:
        return False

    title_lower = title.lower().strip()

    # Length check: real job titles are 10-200 chars
    if len(title_lower) < 10 or len(title_lower) > 200:
        return False

    # Blacklist check: reject if title IS a known nav word
    for bl_word in NAV_BLACKLIST:
        if title_lower == bl_word or title_lower.startswith(bl_word + " ") or \
           title_lower.endswith(" " + bl_word):
            return False

    # Must contain at least one real job indicator word
    if not any(indicator in title_lower for indicator in REAL_JOB_INDICATORS):
        return False

    # Reject if it looks like a URL fragment
    if title.startswith("http") or title.startswith("/") or title.startswith("www"):
        return False

    return True


def matches_our_roles(title: str, desc: str = "") -> bool:
    """Check if job matches Abhilash's target roles."""
    combined = f"{title} {desc}".lower()
    return any(kw in combined for kw in TARGET_KEYWORDS)


def extract_experience(title: str, desc: str = "") -> str:
    """Extract experience requirement."""
    text = f"{title} {desc}".lower()
    fresher_indicators = ["fresher", "entry level", "0 year", "0-1", "graduate",
                          "intern", "trainee", "campus", "no experience"]
    if any(fi in text for fi in fresher_indicators):
        return "0-1 years (Fresher)"
    match = re.search(r"(\d+)\s*[-–to]+\s*(\d+)\s*years?", text)
    if match:
        return f"{match.group(1)}-{match.group(2)} years"
    return "0-2 years"


def build_absolute_link(href: str, base_url: str) -> str:
    """Convert relative URL to absolute."""
    if not href:
        return base_url
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        # Extract domain from base URL
        parts = base_url.split("/")
        if len(parts) >= 3:
            domain = "/".join(parts[:3])
            return domain + href
    return base_url


# =============================================================================
# MAIN SCRAPER CLASS
# =============================================================================

class CompanyScraperV4:

    def __init__(self, scraping_config: dict, companies_json_path: str):
        self.config = scraping_config
        self.max_threads = scraping_config.get("max_threads", 8)

        with open(companies_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.companies = data if isinstance(data, list) else \
                         data.get("hyderabad_companies", [])

        print(f"✅ CompanyScraperV4 loaded: {len(self.companies)} companies")

    def scrape_all_companies(self, priority_filter=None) -> list:
        """
        Scrape ALL companies (not just priority=2).
        FIX: priority_filter=None means scrape everything.
        """
        companies_to_scrape = self.companies
        if priority_filter is not None:
            companies_to_scrape = [
                c for c in self.companies
                if c.get("priority", 2) <= priority_filter  # <= not ==
            ]

        print(f"\n🏢 HTML Company Scraping: {len(companies_to_scrape)} companies...")

        all_jobs = []

        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = {
                executor.submit(self._safe_scrape, c): c
                for c in companies_to_scrape
            }
            for future in as_completed(futures):
                try:
                    jobs = future.result(timeout=25)
                    all_jobs.extend(jobs)
                except Exception:
                    pass

        # Global dedup
        seen = set()
        unique = []
        for j in all_jobs:
            key = f"{j['title'].lower()}|{j['company'].lower()}"
            if key not in seen:
                seen.add(key)
                unique.append(j)

        print(f"✅ HTML company scraping done: {len(unique)} unique jobs")
        return unique

    def _safe_scrape(self, company: dict) -> list:
        """Scrape with retries and error handling."""
        for attempt in range(2):
            try:
                return self._scrape_company(company)
            except Exception:
                if attempt == 0:
                    time.sleep(1)
        return []

    def _scrape_company(self, company: dict) -> list:
        """
        Scrape a single company's career page.
        Uses requests + BeautifulSoup (no Selenium).
        """
        url = company.get("career_url") or company.get("url", "")
        if not url:
            return []

        company_name = company.get("name", "Unknown")
        company_type = company.get("type", company.get("company_type", "IT"))

        # Polite delay
        time.sleep(random.uniform(0.5, 1.5))

        headers = {
            "User-Agent": self.config.get(
                "user_agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            resp = requests.get(url, headers=headers,
                                timeout=self.config.get("timeout", 15))
        except Exception:
            return []

        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []
        seen_titles = set()

        # Strategy 1: Find <a> tags that look like job titles
        for tag in soup.find_all("a", href=True):
            title = tag.get_text(strip=True)

            if not is_valid_job_title(title):
                continue
            if not matches_our_roles(title):
                continue
            if title.lower() in seen_titles:
                continue

            seen_titles.add(title.lower())
            href = build_absolute_link(tag.get("href", ""), url)

            jobs.append({
                "title": title,
                "company": company_name,
                "company_type": company_type,
                "location": "Hyderabad",
                "job_description": title,
                "skills_required": "",
                "experience_required": extract_experience(title),
                "salary": "Not disclosed",
                "application_link": href,
                "source_platform": "Company Career Page",
                "posting_date": datetime.now().strftime("%Y-%m-%d"),
            })

        # Strategy 2: Check heading tags (h1/h2/h3) for job titles
        for tag in soup.find_all(["h2", "h3", "h4"]):
            title = tag.get_text(strip=True)

            if not is_valid_job_title(title):
                continue
            if not matches_our_roles(title):
                continue
            if title.lower() in seen_titles:
                continue

            seen_titles.add(title.lower())

            # Try to find a nearby link
            parent = tag.parent
            link_tag = parent.find("a", href=True) if parent else None
            href = build_absolute_link(
                link_tag.get("href", "") if link_tag else "", url
            )

            jobs.append({
                "title": title,
                "company": company_name,
                "company_type": company_type,
                "location": "Hyderabad",
                "job_description": title,
                "skills_required": "",
                "experience_required": extract_experience(title),
                "salary": "Not disclosed",
                "application_link": href or url,
                "source_platform": "Company Career Page",
                "posting_date": datetime.now().strftime("%Y-%m-%d"),
            })

        if jobs:
            print(f"  ✅ {company_name}: {len(jobs)} jobs")

        return jobs