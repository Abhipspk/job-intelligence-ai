# ============================================================================
# FILE: notifiers/email_sender.py
# ============================================================================

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

class EmailSender:
    def __init__(self, email_config):
        self.config = email_config
    
    def send_email(self, subject, body_html, body_text=None):
        """Send email via Gmail SMTP"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.config['sender_email']
            msg['To'] = self.config['recipient_email']
            msg['Subject'] = subject
            
            # Add text and HTML parts
            if body_text:
                part1 = MIMEText(body_text, 'plain')
                msg.attach(part1)
            
            part2 = MIMEText(body_html, 'html')
            msg.attach(part2)
            
            # Connect to Gmail SMTP
            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            server.starttls()
            server.login(self.config['sender_email'], self.config['sender_password'])
            
            # Send email
            server.send_message(msg)
            server.quit()
            
            print(f"✅ Email sent: {subject}")
            return True
            
        except Exception as e:
            print(f"❌ Error sending email: {e}")
            return False
    
    def send_daily_digest(self, jobs_data, stats):
        """Send daily job digest email"""
        subject = f"🎯 Daily Job Intel - {len(jobs_data['new_jobs'])} New Matches - {datetime.now().strftime('%b %d')}"
        
        html_body = self.generate_digest_html(jobs_data, stats)
        text_body = self.generate_digest_text(jobs_data, stats)
        
        return self.send_email(subject, html_body, text_body)
    
    def send_high_priority_alert(self, job):
        """Send immediate alert for high-match job"""
        subject = f"🔥 HIGH MATCH ({job['relevance_score']}%) - {job['title']} at {job['company']}"
        
        html_body = f"""
        <html>
        <body>
            <h2>🔥 High Priority Job Match!</h2>
            <h3>{job['title']}</h3>
            <p><strong>Company:</strong> {job['company']}</p>
            <p><strong>Location:</strong> {job['location']}</p>
            <p><strong>Match Score:</strong> {job['relevance_score']}%</p>
            <p><strong>Experience:</strong> {job['experience_required']}</p>
            <p><strong>Skills:</strong> {job['skills_required']}</p>
            <br>
            <a href="{job['application_link']}" style="background:#007bff;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">
                Apply Now
            </a>
            <br><br>
            <p><em>This job matches {job['relevance_score']}% of your profile. Apply within 24 hours!</em></p>
        </body>
        </html>
        """
        
        return self.send_email(subject, html_body)
    
    def generate_digest_html(self, jobs_data, stats):
        """Generate HTML email body for daily digest"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background: #007bff; color: white; padding: 20px; }}
                .job-card {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .high-match {{ border-left: 5px solid #28a745; }}
                .score {{ font-size: 24px; font-weight: bold; color: #28a745; }}
                .button {{ background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎯 Your Daily Job Intelligence Report</h1>
                <p>{datetime.now().strftime('%A, %B %d, %Y')}</p>
            </div>
            
            <div style="padding: 20px;">
                <h2>📊 Summary</h2>
                <ul>
                    <li>New Jobs Found: <strong>{stats['total_jobs']}</strong></li>
                    <li>High Match (>80%): <strong>{stats['high_priority']}</strong></li>
                    <li>Pending Applications: <strong>{stats['not_applied']}</strong></li>
                </ul>
                
                <h2>🔥 Top Matches</h2>
        """
        
        # Add top 5 jobs
        for job in jobs_data['top_jobs'][:5]:
            html += f"""
                <div class="job-card high-match">
                    <h3>{job[1]}</h3>  <!-- title -->
                    <p><strong>{job[2]}</strong> | {job[4]}</p>  <!-- company | location -->
                    <p class="score">{job[15]}% Match</p>  <!-- relevance_score -->
                    <p><strong>Skills:</strong> {job[6]}</p>  <!-- skills_required -->
                    <p><strong>Experience:</strong> {job[5]}</p>  <!-- experience_required -->
                    <a href="{job[10]}" class="button">Apply Now</a>
                </div>
            """
        
        html += """
            </div>
        </body>
        </html>
        """
        
        return html
    
    def generate_digest_text(self, jobs_data, stats):
        """Generate plain text version"""
        text = f"""
        YOUR DAILY JOB INTELLIGENCE REPORT
        {datetime.now().strftime('%A, %B %d, %Y')}
        
        ═══════════════════════════════════════
        SUMMARY
        ═══════════════════════════════════════
        New Jobs Found: {stats['total_jobs']}
        High Match (>80%): {stats['high_priority']}
        Pending Applications: {stats['not_applied']}
        
        ═══════════════════════════════════════
        TOP MATCHES
        ═══════════════════════════════════════
        """
        
        for i, job in enumerate(jobs_data['top_jobs'][:5], 1):
            text += f"""
        {i}. {job[1]}
           Company: {job[2]}
           Location: {job[4]}
           Match: {job[15]}%
           Apply: {job[10]}
        
        """
        
        return text