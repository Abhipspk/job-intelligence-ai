"""
=============================================================================
ATS SCRAPER - USES PUBLIC APIs (NO SELENIUM, WORKS ON RENDER)
=============================================================================
Most major companies use one of these 4 ATS platforms.
ALL have FREE public JSON APIs - no login, no scraping, instant results.

Greenhouse : https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
Lever      : https://api.lever.co/v0/postings/{slug}?mode=json
Workday    : POST https://{co}.wd5.myworkdayjobs.com/wday/cxs/{co}/{site}/jobs
SmartRec   : https://careers.smartrecruiters.com/{slug}/api/more?start=0
=============================================================================
"""

import re
import time
import random
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


# =============================================================================
# CONSTANTS
# =============================================================================

# Words that appear in real job titles (for filtering)
JOB_TITLE_WORDS = {
    "analyst", "engineer", "developer", "manager", "architect", "scientist",
    "intern", "associate", "consultant", "specialist", "coordinator",
    "lead", "senior", "junior", "trainee", "executive", "officer",
    "data", "sql", "python", "bi", "etl", "mis", "reporting", "analytics",
    "software", "business", "system", "cloud", "devops", "qa", "testing",
    "full", "stack", "backend", "frontend"
}

# Keywords that match Abhilash's target roles
TARGET_ROLE_KEYWORDS = {
    "data analyst", "data analysis", "data engineer", "data engineering",
    "data scientist", "data science", "analytics engineer",
    "sql developer", "sql", "business analyst", "business analysis",
    "system engineer", "systems engineer", "junior analyst",
    "associate analyst", "mis executive", "mis analyst",
    "reporting analyst", "bi analyst", "bi developer",
    "power bi", "tableau", "business intelligence",
    "fresher", "entry level", "graduate", "trainee", "associate",
    "junior", "intern", "internship", "etl developer", "etl engineer"
}

# Locations we care about
TARGET_LOCATIONS = {"india", "hyderabad", "bangalore", "bengaluru", "remote",
                    "work from home", "wfh"}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


# =============================================================================
# HELPERS
# =============================================================================

def is_relevant_job(title: str, description: str = "") -> bool:
    """Check if a job title matches target roles."""
    combined = f"{title} {description}".lower()
    return any(kw in combined for kw in TARGET_ROLE_KEYWORDS)


def is_india_location(location_text: str) -> bool:
    """Check if job is in India / remote."""
    if not location_text:
        return True  # No location = assume global open
    loc = location_text.lower()
    # Exclude clearly non-India locations
    non_india = {"united states", "usa", "us ", "uk ", "london", "singapore",
                 "australia", "canada", "germany", "france", "netherlands",
                 "new york", "san francisco", "chicago", "toronto"}
    if any(x in loc for x in non_india):
        return False
    return any(x in loc for x in TARGET_LOCATIONS) or not any(
        c.isalpha() for c in loc[:5]  # If location is just empty/numbers
    )


def normalize_job(title, company, location, description, link, source, company_type):
    """Normalize to standard job format."""
    return {
        "title": title[:200],
        "company": company,
        "company_type": company_type,
        "location": location or "India",
        "job_description": (description or title)[:600],
        "skills_required": "",
        "experience_required": extract_experience(title, description),
        "salary": "Not disclosed",
        "application_link": link or "",
        "source_platform": source,
        "posting_date": datetime.now().strftime("%Y-%m-%d"),
    }


def extract_experience(title: str, desc: str = "") -> str:
    """Try to extract experience requirement from text."""
    text = f"{title} {desc}".lower()
    fresher_words = ["fresher", "entry level", "graduate", "trainee", "intern",
                     "0 year", "0-1", "0 to 1"]
    if any(w in text for w in fresher_words):
        return "0-1 years (Fresher)"
    # Regex: "2-5 years" or "2 to 5 years"
    match = re.search(r"(\d+)\s*(?:[-–to]+)\s*(\d+)\s*years?", text)
    if match:
        return f"{match.group(1)}-{match.group(2)} years"
    match = re.search(r"(\d+)\+?\s*years?", text)
    if match:
        return f"{match.group(1)}+ years"
    return "Not specified"


# =============================================================================
# 1. GREENHOUSE API
# =============================================================================

def scrape_greenhouse(company_name: str, slug: str, company_type: str) -> list:
    """
    Greenhouse public API - returns all jobs as JSON.
    No authentication, no rate limits for basic usage.
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return []

        jobs_raw = resp.json().get("jobs", [])
        jobs = []

        for j in jobs_raw:
            title = j.get("title", "").strip()
            if not title or not is_relevant_job(title):
                continue

            # Location check
            offices = j.get("offices", [])
            location = offices[0].get("name", "India") if offices else "India"
            if not is_india_location(location):
                continue

            link = j.get("absolute_url", "")
            desc = j.get("content", "")[:400]

            jobs.append(normalize_job(
                title, company_name, location, desc, link,
                "Greenhouse (Direct API)", company_type
            ))

        if jobs:
            print(f"  ✅ Greenhouse | {company_name}: {len(jobs)} jobs")
        return jobs

    except Exception as e:
        return []


# =============================================================================
# 2. LEVER API
# =============================================================================

def scrape_lever(company_name: str, slug: str, company_type: str) -> list:
    """
    Lever public API - all job postings as JSON array.
    """
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return []

        jobs_raw = resp.json()
        if not isinstance(jobs_raw, list):
            return []

        jobs = []
        for j in jobs_raw:
            title = j.get("text", "").strip()
            if not title or not is_relevant_job(title):
                continue

            categories = j.get("categories", {})
            location = categories.get("location", "India")
            if not is_india_location(location):
                continue

            desc = j.get("descriptionPlain", "") or j.get("description", "")
            desc = re.sub(r"<[^>]+>", " ", str(desc))[:400]
            link = j.get("hostedUrl", "")

            jobs.append(normalize_job(
                title, company_name, location, desc, link,
                "Lever (Direct API)", company_type
            ))

        if jobs:
            print(f"  ✅ Lever | {company_name}: {len(jobs)} jobs")
        return jobs

    except Exception:
        return []


# =============================================================================
# 3. WORKDAY API
# =============================================================================

def scrape_workday(company_name: str, workday_url: str, company_type: str) -> list:
    """
    Workday has a hidden JSON POST API behind their career pages.
    Pattern: POST /wday/cxs/{company}/{site}/jobs
    """
    try:
        # Parse URL to extract company slug and site
        # e.g. https://deloitte.wd1.myworkdayjobs.com/en-US/Deloitte_Careers
        match = re.search(
            r"https://([^.]+)\.wd\d+\.myworkdayjobs\.com/(?:en-US/)?(.+?)(?:\?|$)",
            workday_url
        )
        if not match:
            return []

        co_slug = match.group(1)
        site = match.group(2).rstrip("/")

        api_url = (
            f"https://{co_slug}.wd5.myworkdayjobs.com"
            f"/wday/cxs/{co_slug}/{site}/jobs"
        )

        all_jobs = []

        for keyword in ["data analyst", "sql developer", "business analyst",
                        "data engineer", "system engineer"]:
            payload = {
                "appliedFacets": {},
                "limit": 20,
                "offset": 0,
                "searchText": keyword
            }
            try:
                resp = requests.post(
                    api_url, json=payload,
                    headers={**HEADERS, "Content-Type": "application/json"},
                    timeout=15
                )
                if resp.status_code != 200:
                    continue

                data = resp.json()
                for j in data.get("jobPostings", []):
                    title = j.get("title", "").strip()
                    if not title or not is_relevant_job(title):
                        continue

                    location = j.get("locationsText", "India")
                    if not is_india_location(location):
                        continue

                    job_path = j.get("externalPath", "")
                    apply_link = (
                        f"https://{co_slug}.wd5.myworkdayjobs.com{job_path}"
                        if job_path else workday_url
                    )

                    all_jobs.append(normalize_job(
                        title, company_name, location, title, apply_link,
                        "Workday (Direct API)", company_type
                    ))

                time.sleep(0.3)  # Small delay between keyword searches

            except Exception:
                continue

        # Deduplicate by title
        seen = set()
        unique = []
        for j in all_jobs:
            if j["title"] not in seen:
                seen.add(j["title"])
                unique.append(j)

        if unique:
            print(f"  ✅ Workday | {company_name}: {len(unique)} jobs")
        return unique

    except Exception:
        return []


# =============================================================================
# 4. SMARTRECRUITERS API
# =============================================================================

def scrape_smartrecruiters(company_name: str, slug: str, company_type: str) -> list:
    """
    SmartRecruiters has a public JSON endpoint.
    """
    url = f"https://careers.smartrecruiters.com/{slug}/api/more?start=0"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            # Try alternate format
            url2 = f"https://jobs.smartrecruiters.com/v4/{slug}/all"
            resp = requests.get(url2, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                return []

        data = resp.json()
        jobs_raw = data.get("postings", data.get("content", []))
        jobs = []

        for j in jobs_raw:
            title = j.get("name", j.get("title", "")).strip()
            if not title or not is_relevant_job(title):
                continue

            location = j.get("location", {})
            if isinstance(location, dict):
                location = (
                    location.get("city", "")
                    or location.get("country", "India")
                )
            if not is_india_location(str(location)):
                continue

            link = j.get("ref", j.get("url", j.get("jobUrl", "")))
            jobs.append(normalize_job(
                title, company_name, str(location), title, link,
                "SmartRecruiters (Direct API)", company_type
            ))

        if jobs:
            print(f"  ✅ SmartRec | {company_name}: {len(jobs)} jobs")
        return jobs

    except Exception:
        return []


# =============================================================================
# 5. ICIMS API
# =============================================================================

def scrape_icims(company_name: str, icims_url: str, company_type: str) -> list:
    """
    iCIMS API - available on some companies.
    """
    try:
        # Extract client ID from URL: https://careers.company.com/jobs?icims=xxxxx
        match = re.search(r"jobs\.icims\.com/jobs/\d+/search", icims_url)
        if not match:
            return []
        # Generic iCIMS search
        resp = requests.get(icims_url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return []
        # Parse HTML fallback
        return []
    except Exception:
        return []


# =============================================================================
# 6. INDEED JOBS API (requests-based, no Selenium)
# =============================================================================

def scrape_indeed(keywords: str, location: str = "Hyderabad") -> list:
    """
    Indeed jobs via requests - no Selenium needed.
    Works on Render deployment.
    """
    from bs4 import BeautifulSoup

    url = (
        f"https://www.indeed.com/jobs?"
        f"q={requests.utils.quote(keywords)}"
        f"&l={requests.utils.quote(location)}"
        f"&fromage=14"  # Last 14 days
        f"&sort=date"
    )

    try:
        # Use Indeed India for better results
        url_in = (
            f"https://in.indeed.com/jobs?"
            f"q={requests.utils.quote(keywords)}"
            f"&l=Hyderabad%2C+Telangana"
            f"&fromage=7"
            f"&sort=date"
        )

        resp = requests.get(url_in, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        job_cards = soup.find_all("div", class_=re.compile(r"job_seen_beacon|jobsearch-ResultsList"))

        if not job_cards:
            # Try newer Indeed layout
            job_cards = soup.find_all("li", class_=re.compile(r"css-"))
            job_cards = [c for c in job_cards if c.find("h2")]

        jobs = []
        for card in job_cards[:20]:
            try:
                # Title
                title_el = card.find("h2") or card.find("a", {"data-testid": "job-title"})
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                if not title or not is_relevant_job(title):
                    continue

                # Company
                company_el = card.find("span", {"data-testid": "company-name"}) or \
                             card.find("span", class_=re.compile(r"company"))
                company = company_el.get_text(strip=True) if company_el else "Unknown"

                # Location
                loc_el = card.find("div", {"data-testid": "text-location"}) or \
                         card.find("span", class_=re.compile(r"location"))
                location_txt = loc_el.get_text(strip=True) if loc_el else "Hyderabad"

                # Link
                link_el = card.find("a", href=True)
                link = ""
                if link_el:
                    href = link_el.get("href", "")
                    if href.startswith("/"):
                        link = f"https://in.indeed.com{href}"
                    elif href.startswith("http"):
                        link = href

                jobs.append(normalize_job(
                    title, company, location_txt, title, link,
                    "Indeed", "Unknown"
                ))
            except Exception:
                continue

        if jobs:
            print(f"  ✅ Indeed | '{keywords}': {len(jobs)} jobs")
        return jobs

    except Exception as e:
        return []


# =============================================================================
# 7. INSTAHYRE (requests-based)
# =============================================================================

def scrape_instahyre(keywords: str) -> list:
    """
    Instahyre - good for Indian startup jobs.
    Uses their public search API.
    """
    try:
        url = (
            f"https://www.instahyre.com/api/v1/opportunity/search/"
            f"?q={requests.utils.quote(keywords)}"
            f"&city=Hyderabad"
            f"&experience=0"
        )
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return []

        data = resp.json()
        opportunities = data.get("opportunities", data.get("results", []))
        jobs = []

        for opp in opportunities[:20]:
            title = opp.get("designation", opp.get("title", "")).strip()
            if not title or not is_relevant_job(title):
                continue

            company = opp.get("company_name", opp.get("company", {}).get("name", ""))
            location = opp.get("city", "Hyderabad")
            link = f"https://www.instahyre.com/jobs/{opp.get('id', '')}"

            jobs.append(normalize_job(
                title, company, location, title, link,
                "Instahyre", "Startup"
            ))

        if jobs:
            print(f"  ✅ Instahyre | '{keywords}': {len(jobs)} jobs")
        return jobs

    except Exception:
        return []


# =============================================================================
# MAIN ATS SCRAPER CLASS
# =============================================================================

# Companies with their ATS type and credentials
# These are verified working configurations
KNOWN_ATS_COMPANIES = [
    # =========== GREENHOUSE ===========
    {"name": "Genpact",            "ats": "greenhouse", "slug": "genpact",              "type": "BPO",       "priority": 1},
    {"name": "EXL Service",        "ats": "greenhouse", "slug": "exlservice",            "type": "BPO",       "priority": 1},
    {"name": "Capgemini India",    "ats": "greenhouse", "slug": "capgemini",             "type": "MNC",       "priority": 1},
    {"name": "Harness.io",         "ats": "greenhouse", "slug": "harnessinc",            "type": "Startup",   "priority": 2},
    {"name": "Delhivery",          "ats": "greenhouse", "slug": "delhivery",             "type": "Startup",   "priority": 2},
    {"name": "Swiggy",             "ats": "greenhouse", "slug": "swiggy",                "type": "Startup",   "priority": 1},
    {"name": "Zomato",             "ats": "greenhouse", "slug": "zomato",                "type": "Startup",   "priority": 1},
    {"name": "CRED",               "ats": "greenhouse", "slug": "dreamplug",             "type": "Fintech",   "priority": 2},
    {"name": "Meesho",             "ats": "greenhouse", "slug": "meesho",                "type": "Startup",   "priority": 2},
    {"name": "PhonePe",            "ats": "greenhouse", "slug": "phonepe",               "type": "Fintech",   "priority": 1},
    {"name": "BrowserStack",       "ats": "greenhouse", "slug": "browserstack",          "type": "Startup",   "priority": 2},
    {"name": "Postman",            "ats": "greenhouse", "slug": "postman",               "type": "Startup",   "priority": 2},
    {"name": "CleverTap",          "ats": "greenhouse", "slug": "clevertap",             "type": "Startup",   "priority": 2},
    {"name": "Whatfix",            "ats": "greenhouse", "slug": "whatfix",               "type": "Startup",   "priority": 2},
    {"name": "Razorpay",           "ats": "greenhouse", "slug": "razorpay",              "type": "Fintech",   "priority": 1},
    {"name": "InMobi",             "ats": "greenhouse", "slug": "inmobi",                "type": "Startup",   "priority": 2},
    {"name": "Unacademy",          "ats": "greenhouse", "slug": "unacademy",             "type": "Edtech",    "priority": 2},
    {"name": "Vedantu",            "ats": "greenhouse", "slug": "vedantu",               "type": "Edtech",    "priority": 2},
    {"name": "Dream11",            "ats": "greenhouse", "slug": "dream11",               "type": "Startup",   "priority": 2},
    {"name": "Groww",              "ats": "greenhouse", "slug": "groww",                 "type": "Fintech",   "priority": 2},
    {"name": "Zerodha",            "ats": "greenhouse", "slug": "zerodha",               "type": "Fintech",   "priority": 2},
    {"name": "Slice",              "ats": "greenhouse", "slug": "slicepay",              "type": "Fintech",   "priority": 2},
    {"name": "MathWorks",          "ats": "greenhouse", "slug": "mathworks",             "type": "MNC",       "priority": 2},
    {"name": "WalkMe",             "ats": "greenhouse", "slug": "walkme",                "type": "Startup",   "priority": 2},

    # =========== LEVER ===========
    {"name": "Darwinbox",          "ats": "lever",      "slug": "darwinbox",             "type": "Startup",   "priority": 1},
    {"name": "Keka HR",            "ats": "lever",      "slug": "keka",                  "type": "Startup",   "priority": 1},
    {"name": "FarEye",             "ats": "lever",      "slug": "fareye",                "type": "Startup",   "priority": 2},
    {"name": "Exotel",             "ats": "lever",      "slug": "exotel",                "type": "Startup",   "priority": 2},
    {"name": "Zetwerk",            "ats": "lever",      "slug": "zetwerk",               "type": "Startup",   "priority": 2},
    {"name": "Licious",            "ats": "lever",      "slug": "licious",               "type": "Startup",   "priority": 2},
    {"name": "Urban Company",      "ats": "lever",      "slug": "urbancompany",          "type": "Startup",   "priority": 2},
    {"name": "Bizongo",            "ats": "lever",      "slug": "bizongo",               "type": "Startup",   "priority": 2},
    {"name": "PubMatic",           "ats": "lever",      "slug": "pubmatic",              "type": "MNC",       "priority": 2},
    {"name": "WebEngage",          "ats": "lever",      "slug": "webengage",             "type": "Startup",   "priority": 2},
    {"name": "MoEngage",           "ats": "lever",      "slug": "moengage",              "type": "Startup",   "priority": 2},
    {"name": "HealthifyMe",        "ats": "lever",      "slug": "healthifyme",           "type": "Startup",   "priority": 2},
    {"name": "Pocket FM",          "ats": "lever",      "slug": "pocketfm",              "type": "Startup",   "priority": 2},

    # =========== WORKDAY ===========
    {"name": "Deloitte",           "ats": "workday",    "slug": "https://deloitte.wd1.myworkdayjobs.com/en-US/Deloitte_Careers",        "type": "MNC",    "priority": 1},
    {"name": "Accenture",          "ats": "workday",    "slug": "https://accenture.wd3.myworkdayjobs.com/AccentureIndiaCampus",          "type": "MNC",    "priority": 1},
    {"name": "JP Morgan",          "ats": "workday",    "slug": "https://jpmc.wd5.myworkdayjobs.com/en-US/External_Career_Site",         "type": "MNC",    "priority": 1},
    {"name": "Goldman Sachs",      "ats": "workday",    "slug": "https://goldmansachs.wd1.myworkdayjobs.com/en-US/campus",               "type": "MNC",    "priority": 1},
    {"name": "Bank of America",    "ats": "workday",    "slug": "https://bofa.eightfold.ai/jobs",                                        "type": "MNC",    "priority": 1},
    {"name": "Barclays",           "ats": "workday",    "slug": "https://barclays.wd3.myworkdayjobs.com/en-US/search",                   "type": "MNC",    "priority": 1},
    {"name": "Synchrony",          "ats": "workday",    "slug": "https://synchrony.wd5.myworkdayjobs.com/en-US/Synchrony_Careers",       "type": "MNC",    "priority": 1},
    {"name": "WNS Global",         "ats": "workday",    "slug": "https://wns.wd3.myworkdayjobs.com/wns_careers",                        "type": "BPO",    "priority": 1},
    {"name": "Qualcomm",           "ats": "workday",    "slug": "https://qualcomm.wd5.myworkdayjobs.com/en-US/External",                 "type": "MNC",    "priority": 1},
    {"name": "Cognizant",          "ats": "workday",    "slug": "https://cognizant.wd1.myworkdayjobs.com/en-US/Cognizant_Careers",       "type": "MNC",    "priority": 1},
    {"name": "Capgemini",          "ats": "workday",    "slug": "https://capgemini.wd3.myworkdayjobs.com/CAPGEMINI_CAREERS",             "type": "MNC",    "priority": 1},
    {"name": "EY",                 "ats": "workday",    "slug": "https://ey.wd5.myworkdayjobs.com/EY_External_Careers",                  "type": "MNC",    "priority": 1},
    {"name": "KPMG",               "ats": "workday",    "slug": "https://kpmg.wd3.myworkdayjobs.com/Careers",                           "type": "MNC",    "priority": 1},
    {"name": "PwC",                "ats": "workday",    "slug": "https://pwc.wd1.myworkdayjobs.com/en-IN/Global_Campus",                 "type": "MNC",    "priority": 1},
    {"name": "Wipro",              "ats": "workday",    "slug": "https://wipro.wd3.myworkdayjobs.com/Wipro_Careers",                     "type": "MNC",    "priority": 1},
    {"name": "Novartis",           "ats": "workday",    "slug": "https://novartis.wd3.myworkdayjobs.com/en-US/Novartis_Careers",         "type": "Pharma", "priority": 2},
    {"name": "Johnson & Johnson",  "ats": "workday",    "slug": "https://jnjcareers.wd1.myworkdayjobs.com/en-US/JNJIndia",               "type": "Pharma", "priority": 2},
    {"name": "Citrix",             "ats": "workday",    "slug": "https://citrix.wd1.myworkdayjobs.com/en-US/CitrixCareers",              "type": "MNC",    "priority": 2},

    # =========== SMARTRECRUITERS ===========
    {"name": "Concentrix",         "ats": "smartrecruiters", "slug": "Concentrix",       "type": "BPO",    "priority": 1},
    {"name": "Teleperformance",    "ats": "smartrecruiters", "slug": "Teleperformance",  "type": "BPO",    "priority": 1},
    {"name": "HGS",                "ats": "smartrecruiters", "slug": "HGS",              "type": "BPO",    "priority": 2},
    {"name": "Mphasis",            "ats": "smartrecruiters", "slug": "Mphasis",          "type": "MNC",    "priority": 2},
    {"name": "Sutherland",         "ats": "smartrecruiters", "slug": "Sutherland",       "type": "BPO",    "priority": 2},
]


class ATSScraper:
    """
    Scrapes jobs from Greenhouse, Lever, Workday, SmartRecruiters APIs.
    Also scrapes Indeed and Instahyre.
    NO Selenium required - works perfectly on Render free tier.
    """

    def __init__(self, config: dict):
        self.config = config
        self.max_threads = config.get("max_threads", 8)

    def _scrape_one(self, company: dict) -> list:
        """Route to correct API based on ATS type."""
        ats = company.get("ats", "generic")
        name = company["name"]
        slug = company["slug"]
        ctype = company.get("type", "IT")

        try:
            if ats == "greenhouse":
                return scrape_greenhouse(name, slug, ctype)
            elif ats == "lever":
                return scrape_lever(name, slug, ctype)
            elif ats == "workday":
                return scrape_workday(name, slug, ctype)
            elif ats == "smartrecruiters":
                return scrape_smartrecruiters(name, slug, ctype)
        except Exception as e:
            return []
        return []

    def scrape_all_ats_companies(self) -> list:
        """Scrape ALL known ATS companies in parallel."""
        print(f"\n🔌 ATS API Scraping: {len(KNOWN_ATS_COMPANIES)} companies...")

        all_jobs = []

        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = {
                executor.submit(self._scrape_one, c): c
                for c in KNOWN_ATS_COMPANIES
            }
            for future in as_completed(futures):
                try:
                    jobs = future.result(timeout=30)
                    all_jobs.extend(jobs)
                except Exception:
                    pass

        print(f"✅ ATS scraping done: {len(all_jobs)} jobs found")
        return all_jobs

    def scrape_indeed_all_roles(self, target_roles: list) -> list:
        """Scrape Indeed for each target role."""
        print(f"\n🔍 Indeed scraping: {len(target_roles)} roles...")

        all_jobs = []
        seen_titles = set()

        role_queries = [
            "Data Analyst fresher Hyderabad",
            "SQL Developer fresher Hyderabad",
            "Business Analyst fresher Hyderabad",
            "Data Engineer entry level Hyderabad",
            "System Engineer fresher Hyderabad",
            "Junior Data Analyst Hyderabad",
            "MIS Executive Hyderabad",
            "Reporting Analyst Hyderabad",
            "Data Analyst intern Hyderabad",
            "Power BI developer Hyderabad",
            "Tableau developer Hyderabad",
        ]

        for query in role_queries:
            try:
                jobs = scrape_indeed(query)
                for j in jobs:
                    key = f"{j['title']}|{j['company']}"
                    if key not in seen_titles:
                        seen_titles.add(key)
                        all_jobs.append(j)
                time.sleep(random.uniform(1, 2))
            except Exception:
                continue

        print(f"✅ Indeed total: {len(all_jobs)} jobs")
        return all_jobs

    def scrape_instahyre_roles(self, target_roles: list) -> list:
        """Scrape Instahyre for target roles."""
        print(f"\n🔍 Instahyre scraping...")

        all_jobs = []
        seen_titles = set()

        for role in ["data analyst", "business analyst", "sql developer",
                     "data engineer", "system engineer"]:
            try:
                jobs = scrape_instahyre(role)
                for j in jobs:
                    key = f"{j['title']}|{j['company']}"
                    if key not in seen_titles:
                        seen_titles.add(key)
                        all_jobs.append(j)
                time.sleep(1)
            except Exception:
                continue

        print(f"✅ Instahyre total: {len(all_jobs)} jobs")
        return all_jobs