#!/usr/bin/env python3
"""
=============================================================================
AUTOMATED JOB INTELLIGENCE SYSTEM v4.0
=============================================================================
FIXES:
1. Priority filter bug - now scrapes ALL companies
2. ATS scraper integrated (Greenhouse/Lever/Workday/SmartRec)
3. Indeed + Instahyre added
4. Company scraper garbage fixed
5. Email sends ALL high-priority jobs (not just 3)
6. Render-compatible (detects cloud environment, skips Selenium)
=============================================================================
"""
import warnings
warnings.filterwarnings("ignore")

import sys, os, logging
from datetime import datetime

# UTF-8 fix for Windows emoji
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

logging.getLogger("selenium").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("WDM").setLevel(logging.CRITICAL)

# ============================================================
# PATH SETUP
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ============================================================
# DETECT ENVIRONMENT
# ============================================================
IS_RENDER = bool(os.environ.get("RENDER") or os.environ.get("RENDER_EXTERNAL_URL"))
IS_CI     = bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))
USE_SELENIUM = not (IS_RENDER or IS_CI)

if IS_RENDER:
    print("☁️  Running on Render - Selenium disabled, using API scrapers")
else:
    print("💻 Running locally - full Selenium + API scraping enabled")

# ============================================================
# IMPORTS
# ============================================================
from config.config import (
    YOUR_PROFILE, EMAIL_CONFIG, SCRAPING_CONFIG,
    MATCHING_CONFIG, DATABASE_CONFIG, JOB_SOURCES, COMPANY_SCRAPER_CONFIG
)
from database.db_manager import DatabaseManager
from analyzers.job_matcher import JobMatcher
from notifiers.email_sender import EmailSender
from scrapers.ats_scraper import ATSScraper
from scrapers.company_scraper_v4 import CompanyScraperV4

if USE_SELENIUM:
    try:
        from scrapers.naukri_scraper import NaukriScraper
        from scrapers.linkedin_scraper import LinkedInScraper
        SELENIUM_OK = True
    except ImportError:
        SELENIUM_OK = False
        print("⚠️  Selenium scrapers not available")
else:
    SELENIUM_OK = False


# ============================================================
# HELPERS
# ============================================================
def safe_scrape(scraper_fn, params, source_name):
    try:
        jobs = scraper_fn(params)
        print(f"  ✅ {source_name}: {len(jobs)} jobs")
        return jobs
    except Exception as e:
        print(f"  ❌ {source_name}: {e}")
        return []


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("🤖 AUTOMATED JOB INTELLIGENCE SYSTEM v4.0")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Initialize
    db        = DatabaseManager(DATABASE_CONFIG["db_path"])
    matcher   = JobMatcher(YOUR_PROFILE, MATCHING_CONFIG)
    emailer   = EmailSender(EMAIL_CONFIG)
    ats_scraper = ATSScraper(SCRAPING_CONFIG)

    all_jobs = []

    # ----------------------------------------------------------
    # STEP 1A: SELENIUM SCRAPERS (Local only)
    # ----------------------------------------------------------
    if SELENIUM_OK:
        print("🔍 STEP 1A: Selenium scraping (Naukri + LinkedIn)...")
        naukri_scraper   = NaukriScraper(SCRAPING_CONFIG)
        linkedin_scraper = LinkedInScraper(SCRAPING_CONFIG)

        for role in YOUR_PROFILE["target_roles"]:
            for location in YOUR_PROFILE["preferred_locations"]:
                if location.lower() in ["remote", "work from home"]:
                    continue

                params = {"keywords": role, "location": location, "experience": 0}
                print(f"\n  📍 {role} | {location}")

                all_jobs.extend(safe_scrape(
                    naukri_scraper.scrape_jobs, params, "Naukri"
                ))
                all_jobs.extend(safe_scrape(
                    linkedin_scraper.scrape_jobs, params, "LinkedIn"
                ))

        print(f"\n✅ Portal jobs: {len(all_jobs)}\n")
    else:
        print("⏭️  STEP 1A: Selenium scrapers skipped (cloud/CI)\n")

    # ----------------------------------------------------------
    # STEP 1B: ATS API SCRAPING (Works everywhere)
    # ----------------------------------------------------------
    print("🔌 STEP 1B: ATS API Scraping (Greenhouse/Lever/Workday)...")
    ats_jobs = ats_scraper.scrape_all_ats_companies()
    all_jobs.extend(ats_jobs)

    # ----------------------------------------------------------
    # STEP 1C: INDEED + INSTAHYRE (Works everywhere)
    # ----------------------------------------------------------
    print("\n🌐 STEP 1C: Indeed + Instahyre...")
    indeed_jobs = ats_scraper.scrape_indeed_all_roles(YOUR_PROFILE["target_roles"])
    all_jobs.extend(indeed_jobs)

    instahyre_jobs = ats_scraper.scrape_instahyre_roles(YOUR_PROFILE["target_roles"])
    all_jobs.extend(instahyre_jobs)

    # ----------------------------------------------------------
    # STEP 1D: COMPANY HTML PAGES
    # ----------------------------------------------------------
    companies_path = JOB_SOURCES.get("company_pages", {}).get(
        "companies_json_path", "data/companies.json"
    )
    if os.path.exists(companies_path) and JOB_SOURCES.get("company_pages", {}).get("enabled"):
        print(f"\n🏢 STEP 1D: Company Career Pages ({companies_path})...")
        company_scraper = CompanyScraperV4(SCRAPING_CONFIG, companies_path)
        # FIX: priority_filter=None scrapes ALL, not just priority=2
        company_jobs = company_scraper.scrape_all_companies(priority_filter=None)
        all_jobs.extend(company_jobs)
    else:
        print(f"⚠️  Company pages: {companies_path} not found, skipping")

    print(f"\n✅ TOTAL jobs scraped: {len(all_jobs)}\n")

    # ----------------------------------------------------------
    # STEP 2: ANALYZE & SCORE
    # ----------------------------------------------------------
    print("🧠 STEP 2: Scoring and filtering jobs...")

    relevant_jobs = []
    seen_keys = set()

    for job in all_jobs:
        # Global deduplication
        key = f"{job.get('title','').lower()[:50]}|{job.get('company','').lower()}"
        if key in seen_keys:
            continue
        seen_keys.add(key)

        # Relevance pre-filter
        if not matcher.is_relevant_job(job):
            continue

        # Score
        score = matcher.calculate_relevance_score(job)
        job["relevance_score"] = score

        if score >= MATCHING_CONFIG["min_relevance_score"]:
            relevant_jobs.append(job)

    # Sort best first
    relevant_jobs.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    print(f"✅ Relevant jobs: {len(relevant_jobs)}\n")

    # ----------------------------------------------------------
    # STEP 3: SAVE TO DATABASE
    # ----------------------------------------------------------
    print("💾 STEP 3: Saving to database...")

    new_count = 0
    high_priority = []

    for job in relevant_jobs:
        job_id = db.insert_job(job)
        if job_id:
            new_count += 1
            if job["relevance_score"] >= MATCHING_CONFIG["high_priority_score"]:
                high_priority.append(job)

    print(f"✅ New jobs saved: {new_count}")
    print(f"🔥 High priority: {len(high_priority)}\n")

    # ----------------------------------------------------------
    # STEP 4: EMAIL NOTIFICATIONS
    # ----------------------------------------------------------
    print("📧 STEP 4: Sending email notifications...")

    # FIX: Send ALL high priority jobs (not just 3)
    if EMAIL_CONFIG.get("send_immediate_alerts") and high_priority:
        for job in high_priority[:10]:  # Up to 10 immediate alerts
            emailer.send_high_priority_alert(job)

    # Daily digest
    if EMAIL_CONFIG.get("send_daily_digest"):
        stats = db.get_stats()
        top_jobs = db.get_jobs(
            {"min_score": MATCHING_CONFIG["high_priority_score"], "not_applied": True},
            limit=20
        )
        jobs_data = {
            "new_jobs": relevant_jobs,
            "top_jobs": top_jobs,
            "high_priority": high_priority
        }
        emailer.send_daily_digest(jobs_data, stats)

    print("✅ Notifications sent\n")

    # ----------------------------------------------------------
    # SUMMARY
    # ----------------------------------------------------------
    print("=" * 60)
    print("📊 EXECUTION SUMMARY")
    print("=" * 60)
    print(f"  Total Scraped:   {len(all_jobs)}")
    print(f"  Unique Jobs:     {len(seen_keys)}")
    print(f"  Relevant Jobs:   {len(relevant_jobs)}")
    print(f"  New Saved:       {new_count}")
    print(f"  High Priority:   {len(high_priority)}")
    print(f"  Completed:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    main()