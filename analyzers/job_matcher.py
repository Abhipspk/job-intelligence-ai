# ============================================================================
# IMPROVED job_matcher.py - ACTUALLY MATCHES FRESHER JOBS
# ============================================================================

import re
from datetime import datetime
from collections import Counter


class JobMatcher:
    def __init__(self, your_profile, config):
        self.profile = your_profile
        self.config = config
        
        # Fresher keywords - expanded list
        self.fresher_keywords = [
            'fresher', 'freshers', 'entry level', 'entry-level',
            '0 year', '0 years', '0-1', '0 to 1', '0-2', '0 to 2',
            '1 year', '0 month', 'graduate', 'trainee', 'intern',
            'internship', 'junior', 'associate', 'beginner',
            'campus', 'no experience', 'recent graduate'
        ]

    def calculate_relevance_score(self, job):
        """
        IMPROVED - More lenient scoring for freshers
        """
        score = 0
        
        # 1. Keyword match (25%)
        keyword_score = self.calculate_keyword_match(job)
        score += keyword_score * self.config['keyword_weight']
        
        # 2. Experience match (35%) - MOST IMPORTANT FOR FRESHERS
        exp_score = self.calculate_experience_match(job)
        score += exp_score * self.config['experience_weight']
        
        # 3. Location match (20%)
        loc_score = self.calculate_location_match(job)
        score += loc_score * self.config['location_weight']
        
        # 4. Company type (10%)
        company_score = self.calculate_company_score(job)
        score += company_score * self.config['company_type_weight']
        
        # 5. Salary (10%)
        salary_score = 50  # Default
        score += salary_score * self.config['salary_weight']
        
        # BONUS: If explicitly fresher-friendly, add 15 points
        if self.is_explicitly_fresher_friendly(job):
            score += 15
        
        return round(min(score, 100), 2)

    def calculate_keyword_match(self, job):
        """
        IMPROVED - More flexible keyword matching
        """
        job_text = f"{job.get('title','')} {job.get('skills_required','')} {job.get('job_description','')}".lower()
        
        matched_skills = []
        partial_matches = []
        
        for skill in self.profile['skills']:
            skill_lower = skill.lower()
            
            # Exact match
            if skill_lower in job_text:
                matched_skills.append(skill)
            # Partial match (e.g., "python" matches "python3")
            elif any(skill_lower in word for word in job_text.split()):
                partial_matches.append(skill)
        
        # Score: full points for exact, half points for partial
        total_skills = len(self.profile['skills'])
        if total_skills == 0:
            return 50  # Default if no skills defined
        
        exact_score = (len(matched_skills) / total_skills) * 100
        partial_score = (len(partial_matches) / total_skills) * 50
        
        final_score = min(exact_score + partial_score, 100)
        
        # If at least 2 key skills match, boost score
        key_skills = ['sql', 'python', 'excel', 'power bi', 'tableau']
        key_matches = sum(1 for s in matched_skills if s.lower() in key_skills)
        if key_matches >= 2:
            final_score += 10
        
        return min(final_score, 100)

    def calculate_experience_match(self, job):
        """
        MASSIVELY IMPROVED - Actually catches fresher jobs
        """
        exp_text = job.get('experience_required', '').lower()
        title = job.get('title', '').lower()
        description = job.get('job_description', '').lower()
        
        # Check all text for fresher indicators
        all_text = f"{exp_text} {title} {description}"
        
        # PRIORITY 1: Explicit fresher keywords
        for keyword in self.fresher_keywords:
            if keyword in all_text:
                return 100  # Perfect match!
        
        # PRIORITY 2: Extract numbers from experience requirement
        years_pattern = r'(\d+)\s*(?:to|-|–)\s*(\d+)\s*(?:year|yr)'
        matches = re.findall(years_pattern, exp_text)
        
        if matches:
            # Get the maximum experience required
            max_exp = max(int(m[1]) for m in matches)
            
            if max_exp == 0:
                return 100
            elif max_exp == 1:
                return 95
            elif max_exp == 2:
                return 90
            elif max_exp <= self.profile['max_experience_required']:
                return 75
            else:
                return 40
        
        # PRIORITY 3: Single number mentions
        single_year = re.findall(r'(\d+)\s*(?:year|yr)', exp_text)
        if single_year:
            years = int(single_year[0])
            if years == 0:
                return 100
            elif years == 1:
                return 90
            elif years == 2:
                return 80
            elif years <= 3:
                return 60
            else:
                return 30
        
        # PRIORITY 4: If no experience mentioned, assume it's open
        if not exp_text or exp_text == 'not specified':
            # Check title for hints
            if any(word in title for word in ['junior', 'associate', 'trainee', 'intern']):
                return 85
            else:
                return 70  # Might be open to freshers
        
        # Default: Assume might be suitable
        return 60

    def calculate_location_match(self, job):
        """
        IMPROVED - Better location matching
        """
        job_location = job.get('location', '').lower()
        
        # Exact matches
        for pref_loc in self.profile['preferred_locations']:
            if pref_loc.lower() in job_location:
                return 100
        
        # Remote/WFH matches
        remote_keywords = ['remote', 'work from home', 'wfh', 'anywhere', 'pan india']
        if any(kw in job_location for kw in remote_keywords):
            return 95
        
        # Hybrid
        if 'hybrid' in job_location:
            return 85
        
        # Other metros (close enough)
        metro_cities = ['pune', 'mumbai', 'delhi', 'chennai', 'kolkata']
        if any(city in job_location for city in metro_cities):
            return 50
        
        # Different location
        return 30

    def calculate_company_score(self, job):
        """
        Score based on company type
        """
        company_type = job.get('company_type', '').lower()
        company_name = job.get('company', '').lower()
        
        # MNC/Big companies
        mnc_keywords = ['microsoft', 'google', 'amazon', 'deloitte', 'accenture', 'tcs', 'infosys', 'wipro', 'cognizant']
        if company_type == 'mnc' or any(mnc in company_name for mnc in mnc_keywords):
            return 100
        
        # Startups
        if company_type == 'startup':
            return 90
        
        # Others
        return 70

    def is_explicitly_fresher_friendly(self, job):
        """
        Check if job is explicitly for freshers
        """
        title = job.get('title', '').lower()
        exp_text = job.get('experience_required', '').lower()
        desc = job.get('job_description', '')[:500].lower()  # First 500 chars
        
        all_text = f"{title} {exp_text} {desc}"
        
        # Strong fresher indicators
        strong_indicators = [
            'fresher', 'freshers only', 'entry level', 'graduate trainee',
            '0 year', '0 years', 'campus', 'internship', 'trainee program'
        ]
        
        return any(indicator in all_text for indicator in strong_indicators)

    def is_relevant_job(self, job):
        """
        IMPROVED - Much more lenient quick filter
        """
        title = job.get('title', '').lower()
        desc = job.get('job_description', '')[:300].lower()
        skills = job.get('skills_required', '').lower()
        
        all_text = f"{title} {desc} {skills}"
        
        # Relevant keywords - EXPANDED
        keywords = [
            # Data roles
            'data', 'analyst', 'analytics', 'analysis',
            # Engineering
            'engineer', 'engineering',
            # Specific skills
            'sql', 'python', 'excel', 'power bi', 'tableau',
            'database', 'etl', 'reporting', 'dashboard',
            # Related terms
            'bi', 'business intelligence', 'mis', 'report',
            'statistics', 'statistical', 'visualization',
            # Common job types
            'junior', 'associate', 'trainee', 'intern',
            # Tools
            'mysql', 'postgresql', 'pandas', 'numpy'
        ]
        
        # Match if ANY keyword present
        if any(keyword in all_text for keyword in keywords):
            return True
        
        # Special case: Check if it's a fresher role in tech
        if self.is_explicitly_fresher_friendly(job):
            tech_indicators = ['it', 'software', 'technology', 'computer', 'tech']
            if any(tech in all_text for tech in tech_indicators):
                return True
        
        return False

    def extract_keywords(self, text, top_n=20):
        """
        IMPROVED - Better keyword extraction
        """
        # Clean text
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Split into words
        words = text.split()
        
        # Expanded stopwords
        stopwords = {
            'the', 'and', 'for', 'with', 'this', 'that', 'from', 'are', 'will',
            'have', 'you', 'your', 'about', 'would', 'should', 'could', 'been',
            'their', 'were', 'they', 'what', 'which', 'when', 'where', 'who',
            'our', 'can', 'all', 'more', 'than', 'some', 'into', 'very', 'also'
        }
        
        # Filter
        keywords = [w for w in words if len(w) > 2 and w not in stopwords]
        
        # Count frequency
        word_freq = Counter(keywords)
        
        return [word for word, count in word_freq.most_common(top_n)]

    def explain_score(self, job):
        """
        NEW - Explain why a job got its score (for debugging)
        """
        components = {
            'keyword_match': self.calculate_keyword_match(job),
            'experience_match': self.calculate_experience_match(job),
            'location_match': self.calculate_location_match(job),
            'company_score': self.calculate_company_score(job),
            'is_fresher_friendly': self.is_explicitly_fresher_friendly(job)
        }
        
        total_score = self.calculate_relevance_score(job)
        
        return {
            'total_score': total_score,
            'breakdown': components
        }