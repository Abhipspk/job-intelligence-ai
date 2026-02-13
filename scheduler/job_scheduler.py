#!/usr/bin/env python3
"""
ADVANCED Job Scheduler - Production Safe
"""

import os
import sys
import subprocess
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED


# ==========================================================
# PATH SETUP
# ==========================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_SCRIPT = os.path.join(BASE_DIR, "main.py")

LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "scheduler.log")


# ==========================================================
# LOGGING CONFIG
# ==========================================================
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# ==========================================================
# CONSOLE COLORS
# ==========================================================
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


# ==========================================================
# MAIN JOB RUNNER
# ==========================================================
def run_job_scraper():

    start_time = datetime.now()

    print("\n" + "=" * 60)
    print(f"{Colors.CYAN}⏰ Running Job Scraper at {start_time}{Colors.RESET}")
    print("=" * 60)

    logging.info("Job scraper started")

    try:

        print(f"📂 Running Script: {MAIN_SCRIPT}")
        print(f"📂 Working Directory: {BASE_DIR}")
        print(f"🐍 Python: {sys.executable}")

        result = subprocess.run(
            [sys.executable, MAIN_SCRIPT],
            cwd=BASE_DIR,  # ⭐ CRITICAL FIX
            capture_output=True,
            text=True,
            timeout=60 * 60
        )

        # ⭐ ALWAYS PRINT OUTPUT (DEBUG GOLD)
        print(result.stdout)

        if result.returncode == 0:
            print(f"{Colors.GREEN}✅ Job Scraper Completed{Colors.RESET}")
            logging.info("Job scraper completed successfully")

        else:
            print(f"{Colors.RED}❌ Job Scraper Failed{Colors.RESET}")
            print(result.stderr)
            logging.error(result.stderr)

    except subprocess.TimeoutExpired:
        print(f"{Colors.RED}❌ Job Timed Out{Colors.RESET}")
        logging.error("Job timed out")

    except Exception as e:
        print(f"{Colors.RED}❌ Scheduler Error: {e}{Colors.RESET}")
        logging.error(str(e))


# ==========================================================
# APSCHEDULER EVENT LISTENER
# ==========================================================
def job_listener(event):

    if event.exception:
        logging.error("Scheduled job crashed")
    else:
        logging.info("Scheduled job executed successfully")


# ==========================================================
# START SCHEDULER
# ==========================================================
def start_scheduler():

    scheduler = BlockingScheduler()

    scheduler.add_listener(
        job_listener,
        EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
    )

    scheduler.add_job(
        run_job_scraper,
        trigger="interval",
        hours=6,
        next_run_time=datetime.now(),
        max_instances=1,
        coalesce=True
    )

    print(f"{Colors.GREEN}🚀 Scheduler Started (Every 6 Hours){Colors.RESET}")
    print("📁 Logs → logs/scheduler.log")
    print("🛑 Press CTRL + C to stop")

    logging.info("Scheduler started")

    try:
        scheduler.start()

    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Scheduler stopped")
        logging.info("Scheduler stopped")


# ==========================================================
# ENTRY POINT
# ==========================================================
if __name__ == "__main__":
    start_scheduler()
