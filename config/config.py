# ============================================================================
# ADVANCED PRODUCTION CONFIG - ENTERPRISE READY (ENV SECURED)
# ============================================================================

import os
from dotenv import load_dotenv

# Load ENV variables
load_dotenv()

# ============================================================================
# PROFILE CONFIG
# ============================================================================

YOUR_PROFILE = {
    "name": "Dharmarajula Abhilash",
    "email": os.getenv("EMAIL_SENDER"),

    "location": "Hyderabad",

    "experience_years": 0,
    "max_experience_required": 2,

    "target_roles": [
        "Data Analyst",
        "Associate Data Engineer",
        "Data Engineer",
        "SQL Developer",
        "Business Analyst",
        "System Engineer",
        "Junior Data Analyst",
        "Analyst",
        "MIS Executive",
        "Reporting Analyst"
    ],

    "skills": [
        "SQL", "Python", "Power BI", "Tableau", "Excel",
        "pandas", "numpy", "Data Analysis", "ETL",
        "MySQL", "PostgreSQL", "Data Visualization",
        "Statistical Analysis", "Azure", "Git", "R"
    ],

    "preferred_locations": [
        "Hyderabad",
        "Bangalore",
        "Remote",
        "Work from Home"
    ]
}

# ============================================================================
# EMAIL CONFIG (SECURE ENV VERSION)
# ============================================================================

EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,

    "sender_email": os.getenv("EMAIL_SENDER"),
    "sender_password": os.getenv("EMAIL_PASSWORD"),
    "recipient_email": os.getenv("EMAIL_SENDER"),

    "send_daily_digest": True,
    "send_immediate_alerts": True,
    "digest_time": "07:00"
}

# ============================================================================
# SCRAPING CONFIG
# ============================================================================

SCRAPING_CONFIG = {

    "user_agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",

    "timeout": 20,
    "max_retries": 3,
    "request_delay": 2,
    "scrape_interval_hours": 6,

    "max_threads": 10,
    "company_scrape_batch_size": 50,

    "random_delay_min": 1,
    "random_delay_max": 3
}

# ============================================================================
# MATCHING CONFIG
# ============================================================================

MATCHING_CONFIG = {

    "min_relevance_score": 35,
    "high_priority_score": 65,

    "keyword_weight": 0.25,
    "experience_weight": 0.35,
    "location_weight": 0.20,
    "company_type_weight": 0.10,
    "salary_weight": 0.10,

    "enable_ai_matching": False,
    "enable_embedding_cache": True
}

# ============================================================================
# DATABASE CONFIG
# ============================================================================

DATABASE_CONFIG = {
    "db_path": os.getenv("DB_PATH", "database/jobs.db"),
    "backup_interval_days": 7,
    "batch_insert_size": 100,
    "enable_wal_mode": True
}

# ============================================================================
# JOB SOURCE CONTROL
# ============================================================================

JOB_SOURCES = {

    "naukri": {
        "enabled": True,
        "priority": 1
    },

    "linkedin": {
        "enabled": True,
        "priority": 1
    },

    "indeed": {
        "enabled": True,
        "priority": 1
    },

    "instahyre": {
        "enabled": True,
        "priority": 2
    },

    "company_pages": {
        "enabled": True,
        "priority": 2,
        "companies_json_path": os.getenv(
            "COMPANY_JSON_PATH",
            "data/companies.json"
        )
    }
}

# ============================================================================
# COMPANY SCRAPER CONFIG
# ============================================================================

COMPANY_SCRAPER_CONFIG = {

    "priority_1_hours": 24,
    "priority_2_hours": 72,
    "priority_3_hours": 168,

    "job_keywords": [
        "data", "analyst", "engineer", "developer",
        "sql", "python", "etl", "reporting",
        "bi", "analytics"
    ]
}

# ============================================================================
# FALLBACK LOCAL COMPANY LIST
# ============================================================================

HYDERABAD_COMPANIES = [
    {"name": "Deloitte", "career_url": "https://www2.deloitte.com/us/en/pages/careers/articles/join-deloitte-search-jobs.html", "company_type": "MNC"},
    {"name": "Accenture", "career_url": "https://www.accenture.com/in-en/careers/jobsearch", "company_type": "MNC"},
    {"name": "TCS", "career_url": "https://www.tcs.com/careers", "company_type": "MNC"},
    {"name": "Infosys", "career_url": "https://www.infosys.com/careers/", "company_type": "MNC"},
    {"name": "Wipro", "career_url": "https://careers.wipro.com/", "company_type": "MNC"},
    {"name": "Microsoft", "career_url": "https://careers.microsoft.com", "company_type": "MNC"},
    {"name": "Amazon", "career_url": "https://www.amazon.jobs/", "company_type": "MNC"},
    {"name": "Google", "career_url": "https://careers.google.com/jobs/", "company_type": "MNC"},
    {"name": "PhonePe", "career_url": "https://www.phonepe.com/careers/", "company_type": "Startup"},
    {"name": "Flipkart", "career_url": "https://www.flipkartcareers.com/", "company_type": "Startup"},
]
