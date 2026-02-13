#!/usr/bin/env python3
"""
Automated Job Intelligence System
Main entry point - PRODUCTION VERSION
"""
import warnings
warnings.filterwarnings("ignore")
import sys
import os
from datetime import datetime
import logging
logging.getLogger("selenium").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)


# ⭐ FIX WINDOWS EMOJI PRINT CRASH
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except:
        pass

# ==========================================================
# IMPORT CONFIG
# ==========================================================
sys.path.append(os.path.dirname(__file__))

from config.config import (
    YOUR_PROFILE,
    EMAIL_CONFIG,
    SCRAPING_CONFIG,
    MATCHING_CONFIG,
    DATABASE_CONFIG,
    JOB_SOURCES,
    COMPANY_SCRAPER_CONFIG
)

# ==========================================================
# IMPORT COMPONENTS
# ==========================================================
from database.db_manager import DatabaseManager
from scrapers.naukri_scraper import NaukriScraper
from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.company_scraper_v2 import CompanyScraperV2
from analyzers.job_matcher import JobMatcher
from notifiers.email_sender import EmailSender


# ==========================================================
# MAIN FUNCTION
# ==========================================================
def main():

    print("=" * 60)
    print("🤖 AUTOMATED JOB INTELLIGENCE SYSTEM")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # ======================================================
    # INITIALIZE COMPONENTS
    # ======================================================
    print("📦 Initializing components...")

    db = DatabaseManager(DATABASE_CONFIG["db_path"])

    naukri_scraper = None
    linkedin_scraper = None
    company_scraper = None

    # ------------------------------------------------------
    # SCRAPER INIT BASED ON CONFIG
    # ------------------------------------------------------

    if JOB_SOURCES.get("naukri", {}).get("enabled"):
        naukri_scraper = NaukriScraper(SCRAPING_CONFIG)

    if JOB_SOURCES.get("linkedin", {}).get("enabled"):
        linkedin_scraper = LinkedInScraper(SCRAPING_CONFIG)

    if JOB_SOURCES.get("company_pages", {}).get("enabled"):
        company_scraper = CompanyScraperV2(
            SCRAPING_CONFIG,
            COMPANY_SCRAPER_CONFIG,
            JOB_SOURCES   # ✅ CRITICAL FIX
        )

    matcher = JobMatcher(YOUR_PROFILE, MATCHING_CONFIG)
    emailer = EmailSender(EMAIL_CONFIG)

    print("✅ All components initialized")
    print()

    # ======================================================
    # STEP 1 — SCRAPE JOB PORTALS
    # ======================================================
    print("🔍 STEP 1: Scraping job portals...")

    all_jobs = []

    for role in YOUR_PROFILE["target_roles"]:
        for location in YOUR_PROFILE["preferred_locations"]:

            if location.lower() in ["remote", "work from home"]:
                continue

            print(f"\n📍 Searching: {role} in {location}")

            search_params = {
                "keywords": role,
                "location": location,
                "experience": YOUR_PROFILE["experience_years"]
            }

            # -----------------------------
            # NAUKRI
            # -----------------------------
            if naukri_scraper:
                try:
                    jobs = naukri_scraper.scrape_jobs(search_params)
                    all_jobs.extend(jobs)
                    print(f"🟢 Naukri Added: {len(jobs)}")
                except Exception as e:
                    print(f"❌ Naukri Error: {e}")

            # -----------------------------
            # LINKEDIN
            # -----------------------------
            if linkedin_scraper:
                try:
                    jobs = linkedin_scraper.scrape_jobs(search_params)
                    all_jobs.extend(jobs)
                    print(f"🔵 LinkedIn Added: {len(jobs)}")
                except Exception as e:
                    print(f"❌ LinkedIn Error: {e}")

    print(f"\n✅ Portal jobs scraped: {len(all_jobs)}")
    print()

    # ======================================================
    # STEP 1B — COMPANY SCRAPING (THREAD BASED)
    # ======================================================
    if company_scraper:

        print("🏢 STEP 1B: Scraping Company Career Pages...")

        try:
            company_jobs = company_scraper.scrape_all_companies(
                priority_filter=JOB_SOURCES["company_pages"]["priority"]
            )

            all_jobs.extend(company_jobs)

            print(f"🏢 Company Jobs Added: {len(company_jobs)}")

        except Exception as e:
            print(f"❌ Company Scraper Error: {e}")

    print(f"\n✅ Total jobs after company scraping: {len(all_jobs)}")
    print()

    # ======================================================
    # STEP 2 — ANALYZE JOBS
    # ======================================================
    print("🧠 STEP 2: Analyzing jobs...")

    relevant_jobs = []

    for job in all_jobs:

        if not matcher.is_relevant_job(job):
            continue

        score = matcher.calculate_relevance_score(job)
        job["relevance_score"] = score

        if score >= MATCHING_CONFIG["min_relevance_score"]:
            relevant_jobs.append(job)
            print(f"✅ {job.get('title','Unknown')} - {score}%")

    print(f"\n✅ Relevant jobs found: {len(relevant_jobs)}")
    print()

    # ======================================================
    # STEP 3 — SAVE DATABASE
    # ======================================================
    print("💾 STEP 3: Saving to database...")

    new_jobs_count = 0
    high_priority_jobs = []

    for job in relevant_jobs:

        job_id = db.insert_job(job)

        if job_id:
            new_jobs_count += 1

            if job["relevance_score"] >= MATCHING_CONFIG["high_priority_score"]:
                high_priority_jobs.append(job)

    print(f"✅ New jobs saved: {new_jobs_count}")
    print()

    # ======================================================
    # STEP 4 — EMAIL NOTIFICATIONS
    # ======================================================
    print("📧 STEP 4: Sending notifications...")

    if EMAIL_CONFIG["send_immediate_alerts"]:
        for job in high_priority_jobs[:3]:
            emailer.send_high_priority_alert(job)

    if EMAIL_CONFIG["send_daily_digest"]:

        stats = db.get_stats()

        jobs_data = {
            "new_jobs": relevant_jobs,
            "top_jobs": db.get_jobs(
                {"min_score": 70, "not_applied": True},
                limit=10
            )
        }

        emailer.send_daily_digest(jobs_data, stats)

    print("✅ Notifications sent")
    print()

    # ======================================================
    # SUMMARY
    # ======================================================
    print("=" * 60)
    print("📊 EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Jobs Scraped: {len(all_jobs)}")
    print(f"Relevant Jobs: {len(relevant_jobs)}")
    print(f"New Jobs Saved: {new_jobs_count}")
    print(f"High Priority: {len(high_priority_jobs)}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


# ==========================================================
# ENTRY POINT
# ==========================================================
if __name__ == "__main__":
    main()
