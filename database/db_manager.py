# ============================================================================
# FILE: database/db_manager.py
# ============================================================================

import sqlite3
from datetime import datetime
import os

class DatabaseManager:
    def __init__(self, db_path='database/jobs.db'):
        self.db_path = db_path
        # Create database directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
    
    def get_connection(self):
        """Create database connection"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database with required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Jobs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                company_type TEXT,
                location TEXT,
                experience_required TEXT,
                skills_required TEXT,
                tools_tech_stack TEXT,
                salary TEXT,
                job_description TEXT,
                application_link TEXT,
                source_platform TEXT,
                posting_date DATE,
                scraped_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                freshness_score INTEGER,
                relevance_score REAL,
                applied BOOLEAN DEFAULT 0,
                is_duplicate BOOLEAN DEFAULT 0,
                UNIQUE(title, company, location)
            )
        ''')
        
        # Applications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                application_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER,
                company TEXT,
                role TEXT,
                applied_date DATE,
                resume_version TEXT,
                application_link TEXT,
                status TEXT DEFAULT 'Applied',
                follow_up_date DATE,
                response_date DATE,
                notes TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            )
        ''')
        
        # Keywords table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS keywords (
                keyword_id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT UNIQUE,
                category TEXT,
                frequency INTEGER DEFAULT 1,
                last_seen DATE
            )
        ''')
        
        # Companies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS companies (
                company_id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT UNIQUE,
                company_type TEXT,
                career_page_url TEXT,
                last_scraped TIMESTAMP,
                jobs_count INTEGER DEFAULT 0,
                response_rate REAL DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully")
    
    def insert_job(self, job_data):
        """Insert a new job into database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO jobs (
                    title, company, company_type, location, experience_required,
                    skills_required, tools_tech_stack, salary, job_description,
                    application_link, source_platform, posting_date, 
                    freshness_score, relevance_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_data['title'],
                job_data['company'],
                job_data.get('company_type', 'Unknown'),
                job_data['location'],
                job_data.get('experience_required', 'Not specified'),
                job_data.get('skills_required', ''),
                job_data.get('tools_tech_stack', ''),
                job_data.get('salary', 'Not disclosed'),
                job_data['job_description'],
                job_data['application_link'],
                job_data['source_platform'],
                job_data.get('posting_date', datetime.now().strftime('%Y-%m-%d')),
                job_data.get('freshness_score', 100),
                job_data.get('relevance_score', 0)
            ))
            conn.commit()
            job_id = cursor.lastrowid
            print(f"✅ Job inserted: {job_data['title']} at {job_data['company']}")
            return job_id
        except sqlite3.IntegrityError:
            print(f"⚠️  Duplicate job skipped: {job_data['title']} at {job_data['company']}")
            return None
        finally:
            conn.close()
    
    def get_jobs(self, filters=None, limit=None):
        """Retrieve jobs with optional filters"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM jobs WHERE 1=1"
        params = []
        
        if filters:
            if 'min_score' in filters:
                query += " AND relevance_score >= ?"
                params.append(filters['min_score'])
            if 'location' in filters:
                query += " AND location LIKE ?"
                params.append(f"%{filters['location']}%")
            if 'not_applied' in filters and filters['not_applied']:
                query += " AND applied = 0"
        
        query += " ORDER BY relevance_score DESC, scraped_date DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, params)
        jobs = cursor.fetchall()
        conn.close()
        return jobs
    
    def mark_as_applied(self, job_id, resume_version):
        """Mark a job as applied"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE jobs SET applied = 1 WHERE job_id = ?",
            (job_id,)
        )
        
        # Also insert into applications table
        cursor.execute(
            "SELECT title, company, application_link FROM jobs WHERE job_id = ?",
            (job_id,)
        )
        job_info = cursor.fetchone()
        
        cursor.execute('''
            INSERT INTO applications (
                job_id, company, role, applied_date, resume_version, application_link
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            job_id,
            job_info[1],  # company
            job_info[0],  # title
            datetime.now().strftime('%Y-%m-%d'),
            resume_version,
            job_info[2]   # application_link
        ))
        
        conn.commit()
        conn.close()
        print(f"✅ Job marked as applied: {job_info[0]} at {job_info[1]}")
    
    def get_stats(self):
        """Get database statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total jobs
        cursor.execute("SELECT COUNT(*) FROM jobs")
        stats['total_jobs'] = cursor.fetchone()[0]
        
        # Jobs not applied
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE applied = 0")
        stats['not_applied'] = cursor.fetchone()[0]
        
        # High priority jobs (>80% match)
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE relevance_score >= 80 AND applied = 0")
        stats['high_priority'] = cursor.fetchone()[0]
        
        # Total applications
        cursor.execute("SELECT COUNT(*) FROM applications")
        stats['total_applications'] = cursor.fetchone()[0]
        
        conn.close()
        return stats