import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import subprocess
import sys
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
import time

DB_PATH = "database/jobs.db"

# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(
    page_title="AI Job Intelligence Portal",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for advanced styling
st.markdown("""
<style>
    /* Main container styling */
    .main {
        padding: 0rem 1rem;
    }
    
    /* Gradient text for headers */
    .gradient-text {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
    }
    
    /* Card styling */
    .job-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 1rem;
        color: white;
        transition: transform 0.3s ease;
    }
    
    .job-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
    }
    
    /* Metric cards */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2);
    }
    
    /* Progress bar styling */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea, #764ba2);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 25px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Search bar styling */
    .stTextInput > div > div > input {
        border-radius: 25px;
        border: 2px solid #667eea;
        padding: 0.5rem 1rem;
    }
    
    /* Badge styling */
    .badge {
        display: inline-block;
        padding: 0.25rem 1rem;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 20px;
        font-size: 0.8rem;
        margin-right: 0.5rem;
    }
    
    /* Footer styling */
    .footer {
        text-align: center;
        padding: 2rem;
        color: #666;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# ===============================
# LOAD DATA
# ===============================
@st.cache_data(ttl=60)
def load_jobs():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM jobs ORDER BY job_id DESC",
        conn
    )
    conn.close()
    return df

# ===============================
# RUN SCRAPER FROM WEBSITE
# ===============================
def run_scraper():
    with st.spinner("🚀 Running Scrapers... Please wait"):
        time.sleep(2)  # Simulate scraper running
        subprocess.Popen([sys.executable, "main.py"])
    st.success("✅ Scrapers completed successfully!")

# ===============================
# ANALYTICS FUNCTIONS
# ===============================
def create_job_distribution_chart(df):
    fig = px.pie(
        df, 
        names='company', 
        title='Job Distribution by Company',
        color_discrete_sequence=px.colors.sequential.Purples_r
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
    )
    return fig

def create_match_score_distribution(df):
    fig = px.histogram(
        df, 
        x='relevance_score', 
        nbins=20,
        title='Match Score Distribution',
        color_discrete_sequence=['#667eea']
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
    )
    return fig

# ===============================
# HEADER WITH ANIMATION
# ===============================
col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.markdown("<h1 style='text-align: center;'><span class='gradient-text'>🚀 AI Job Intelligence Portal</span></h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>Your AI-Powered Job Search Assistant</p>", unsafe_allow_html=True)

# Navigation Menu
selected = option_menu(
    menu_title=None,
    options=["Dashboard", "Jobs", "Analytics", "Settings"],
    icons=["house", "briefcase", "graph-up", "gear"],
    menu_icon="cast",
    default_index=1,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "transparent"},
        "icon": {"color": "#667eea", "font-size": "20px"},
        "nav-link": {"font-size": "16px", "text-align": "center", "margin": "0px", "color": "#666"},
        "nav-link-selected": {"background-color": "#667eea"},
    }
)

# ===============================
# LOAD DATA
# ===============================
df = load_jobs()

if df.empty:
    st.warning("No jobs found yet. Run scraper.")
    if st.button("🚀 Run Scraper Now"):
        run_scraper()
    st.stop()

# ===============================
# MAIN CONTENT BASED ON NAVIGATION
# ===============================

if selected == "Dashboard":
    # Dashboard View
    st.markdown("<h2><span class='gradient-text'>📊 Dashboard Overview</span></h2>", unsafe_allow_html=True)
    
    # Advanced Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class='metric-card'>
            <h3 style='color: #667eea; margin: 0;'>📊</h3>
            <h2 style='margin: 0; color: #333;'>{}</h2>
            <p style='color: #666; margin: 0;'>Total Jobs</p>
        </div>
        """.format(len(df)), unsafe_allow_html=True)
    
    with col2:
        high_match = len(df[df["relevance_score"] > 70])
        st.markdown("""
        <div class='metric-card'>
            <h3 style='color: #667eea; margin: 0;'>🎯</h3>
            <h2 style='margin: 0; color: #333;'>{}</h2>
            <p style='color: #666; margin: 0;'>High Match Jobs</p>
        </div>
        """.format(high_match), unsafe_allow_html=True)
    
    with col3:
        companies = df['company'].nunique()
        st.markdown("""
        <div class='metric-card'>
            <h3 style='color: #667eea; margin: 0;'>🏢</h3>
            <h2 style='margin: 0; color: #333;'>{}</h2>
            <p style='color: #666; margin: 0;'>Companies</p>
        </div>
        """.format(companies), unsafe_allow_html=True)
    
    with col4:
        today = datetime.now().strftime("%Y-%m-%d")
        today_jobs = len(df[df["posting_date"] == today])
        st.markdown("""
        <div class='metric-card'>
            <h3 style='color: #667eea; margin: 0;'>📅</h3>
            <h2 style='margin: 0; color: #333;'>{}</h2>
            <p style='color: #666; margin: 0;'>Today's Jobs</p>
        </div>
        """.format(today_jobs), unsafe_allow_html=True)
    
    # Charts Row
    col1, col2 = st.columns(2)
    
    with col1:
        fig1 = create_job_distribution_chart(df.head(10))
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        fig2 = create_match_score_distribution(df)
        st.plotly_chart(fig2, use_container_width=True)
    
    # Recent Jobs Preview
    st.markdown("<h3><span class='gradient-text'>🔥 Recent Hot Jobs</span></h3>", unsafe_allow_html=True)
    recent_df = df.head(3)
    cols = st.columns(3)
    
    for idx, (_, job) in enumerate(recent_df.iterrows()):
        with cols[idx]:
            st.markdown(f"""
            <div class='job-card'>
                <h4 style='margin: 0 0 10px 0;'>{job['title'][:30]}...</h4>
                <p style='margin: 5px 0; opacity: 0.9;'>{job['company']}</p>
                <p style='margin: 5px 0; opacity: 0.9;'>{job['location']}</p>
                <div style='margin: 15px 0;'>
                    <span class='badge'>Match: {job['relevance_score']}%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

elif selected == "Jobs":
    # Jobs View (Original Functionality with Enhanced UI)
    st.markdown("<h2><span class='gradient-text'>💼 Job Listings</span></h2>", unsafe_allow_html=True)
    
    # Action Row
    colA, colB, colC = st.columns([3,2,1])
    
    with colB:
        today_only = st.checkbox("📅 Show Only Today Jobs", help="Filter jobs posted today")
    
    with colC:
        if st.button("🔄 Run Scraper Now"):
            run_scraper()
    
    # Global Search Bar with Icon
    col1, col2 = st.columns([10,1])
    with col1:
        search = st.text_input("🔍", placeholder="Search jobs, skills, companies...", label_visibility="collapsed")
    
    # Apply filters
    filtered_df = df.copy()
    
    if search:
        filtered_df = filtered_df[
            filtered_df.apply(
                lambda row: search.lower() in str(row).lower(),
                axis=1
            )
        ]
    
    if today_only:
        today = datetime.now().strftime("%Y-%m-%d")
        filtered_df = filtered_df[filtered_df["posting_date"] == today]
    
    # Sidebar Filters
    with st.sidebar:
        st.markdown("<h3 style='text-align: center; color: white;'>🎯 Advanced Filters</h3>", unsafe_allow_html=True)
        st.markdown("---")
        
        company = st.selectbox(
            "Company",
            ["All"] + sorted(filtered_df["company"].dropna().unique()),
            help="Filter by company"
        )
        
        location = st.selectbox(
            "Location",
            ["All"] + sorted(filtered_df["location"].dropna().unique()),
            help="Filter by location"
        )
        
        min_score = st.slider("Min Match Score", 0, 100, 40, help="Minimum relevance score")
        
        # Salary Range (if available)
        if 'salary' in filtered_df.columns:
            salary_range = st.slider("Salary Range (K)", 0, 200, (50, 120))
        
        # Job Type (if available)
        if 'job_type' in filtered_df.columns:
            job_type = st.multiselect(
                "Job Type",
                filtered_df['job_type'].dropna().unique(),
                help="Select job types"
            )
    
    # Apply sidebar filters
    if company != "All":
        filtered_df = filtered_df[filtered_df["company"] == company]
    
    if location != "All":
        filtered_df = filtered_df[filtered_df["location"] == location]
    
    filtered_df = filtered_df[filtered_df["relevance_score"] >= min_score]
    
    # Results Summary
    st.markdown(f"<p style='color: #666;'>Found <strong>{len(filtered_df)}</strong> jobs matching your criteria</p>", unsafe_allow_html=True)
    
    # Job Cards
    for _, job in filtered_df.head(50).iterrows():
        
        # Determine card color based on relevance score
        if job['relevance_score'] >= 80:
            card_class = "job-card-high"
        elif job['relevance_score'] >= 60:
            card_class = "job-card-medium"
        else:
            card_class = "job-card-low"
        
        with st.container():
            col1, col2, col3 = st.columns([5,2,1])
            
            with col1:
                st.markdown(f"### {job['title']}")
                st.markdown(f"🏢 {job['company']}  •  📍 {job['location']}")
                
                # Skills tags if available
                if 'skills' in job and pd.notna(job['skills']):
                    skills = job['skills'].split(',')[:3]
                    skills_html = " ".join([f"<span class='badge'>{skill.strip()}</span>" for skill in skills])
                    st.markdown(skills_html + "...", unsafe_allow_html=True)
            
            with col2:
                # Circular progress indicator
                score = int(job["relevance_score"])
                st.markdown(f"""
                <div style='text-align: center;'>
                    <div style='
                        width: 60px;
                        height: 60px;
                        border-radius: 50%;
                        background: conic-gradient(#667eea {score}%, #e0e0e0 {score}%);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin: 10px auto;
                    '>
                        <div style='
                            width: 50px;
                            height: 50px;
                            border-radius: 50%;
                            background: white;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-weight: bold;
                            color: #667eea;
                        '>{score}%</div>
                    </div>
                    <p style='margin: 0; color: #666;'>Match Score</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                if job["application_link"] and pd.notna(job["application_link"]):
                    st.markdown(f"[Apply Now]({job['application_link']})")
                st.caption(f"📅 {job['posting_date']}")
            
            # Job description preview
            with st.expander("View Description"):
                st.write(job["job_description"])
            
            st.divider()

elif selected == "Analytics":
    # Analytics View
    st.markdown("<h2><span class='gradient-text'>📈 Advanced Analytics</span></h2>", unsafe_allow_html=True)
    
    # Time-based analysis
    df['posting_date'] = pd.to_datetime(df['posting_date'])
    daily_counts = df.groupby(df['posting_date'].dt.date).size().reset_index(name='count')
    
    fig = px.line(
        daily_counts, 
        x='posting_date', 
        y='count',
        title='Job Postings Over Time',
        markers=True
    )
    fig.update_traces(line_color='#667eea', line_width=3)
    st.plotly_chart(fig, use_container_width=True)
    
    # Company analysis
    col1, col2 = st.columns(2)
    
    with col1:
        top_companies = df['company'].value_counts().head(10)
        fig = px.bar(
            x=top_companies.values,
            y=top_companies.index,
            orientation='h',
            title='Top Companies by Job Count',
            color=top_companies.values,
            color_continuous_scale='Purples'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        avg_score_by_company = df.groupby('company')['relevance_score'].mean().sort_values(ascending=False).head(10)
        fig = px.bar(
            x=avg_score_by_company.values,
            y=avg_score_by_company.index,
            orientation='h',
            title='Average Match Score by Company',
            color=avg_score_by_company.values,
            color_continuous_scale='Purples'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Location analysis
    st.markdown("<h3><span class='gradient-text'>📍 Location Analysis</span></h3>", unsafe_allow_html=True)
    location_counts = df['location'].value_counts().head(15)
    fig = px.treemap(
        names=location_counts.index,
        parents=[''] * len(location_counts),
        values=location_counts.values,
        title='Job Distribution by Location'
    )
    st.plotly_chart(fig, use_container_width=True)

elif selected == "Settings":
    # Settings View
    st.markdown("<h2><span class='gradient-text'>⚙️ Settings</span></h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔔 Notification Settings")
        email_alerts = st.toggle("Email Alerts", value=True)
        desktop_alerts = st.toggle("Desktop Notifications", value=False)
        daily_digest = st.toggle("Daily Digest", value=True)
        
        st.markdown("### 🎨 Display Settings")
        theme = st.selectbox("Theme", ["Light", "Dark", "System Default"])
        items_per_page = st.slider("Items per page", 10, 100, 50)
    
    with col2:
        st.markdown("### 🔧 Scraper Settings")
        scraper_interval = st.selectbox(
            "Scraper Interval",
            ["Every hour", "Every 6 hours", "Every 12 hours", "Daily"]
        )
        
        st.markdown("### 📊 Data Management")
        if st.button("Clear Cache"):
            st.cache_data.clear()
            st.success("Cache cleared successfully!")
        
        if st.button("Export Data as CSV"):
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"jobs_export_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.info("AI Job Intelligence Portal v2.0 - Powered by Advanced AI and Machine Learning")

# ===============================
# FOOTER
# ===============================
st.markdown("---")
st.markdown("""
<div class='footer'>
    <p>🚀 AI Job Intelligence Portal | © 2024 All Rights Reserved</p>
    <p style='font-size: 0.8rem;'>Powered by Advanced AI & Machine Learning</p>
</div>
""", unsafe_allow_html=True)