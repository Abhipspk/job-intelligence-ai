"""
=============================================================================
AI JOB INTELLIGENCE PORTAL - STREAMLIT APP v4.0
Mobile-friendly | Real-time scraping | Full job management
=============================================================================
"""
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os, sys, threading, subprocess, json, time
import plotly.express as px
import plotly.graph_objects as go

# ============================================================
# STREAMLIT OPTION MENU (graceful fallback if missing)
# ============================================================
try:
    from streamlit_option_menu import option_menu
    HAS_OPTION_MENU = True
except ImportError:
    HAS_OPTION_MENU = False

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="AI Job Portal | Abhilash",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"  # Mobile: collapsed by default
)

# ============================================================
# PATHS
# ============================================================
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DB_PATH   = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "database", "jobs.db"))
MAIN_PY   = os.path.join(BASE_DIR, "main.py")
IS_RENDER = bool(os.environ.get("RENDER") or os.environ.get("RENDER_EXTERNAL_URL"))

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ============================================================
# CSS - MOBILE RESPONSIVE + BEAUTIFUL
# ============================================================
st.markdown("""
<style>
    /* Global */
    * { box-sizing: border-box; }
    .main { padding: 0.5rem 1rem !important; }

    /* Hide default streamlit header on mobile */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Portal header */
    .portal-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 16px 20px;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin-bottom: 16px;
        box-shadow: 0 4px 20px rgba(102,126,234,0.4);
    }
    .portal-header h1 { margin: 0; font-size: 1.6rem; }
    .portal-header p  { margin: 4px 0 0; opacity: 0.9; font-size: 0.9rem; }

    /* Metric boxes */
    .metric-box {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border-radius: 12px;
        padding: 14px;
        text-align: center;
        box-shadow: 0 2px 10px rgba(102,126,234,0.3);
    }
    .metric-box .num  { font-size: 2rem; font-weight: 800; line-height: 1; }
    .metric-box .lbl  { font-size: 0.75rem; opacity: 0.9; margin-top: 4px; }

    /* Job cards */
    .job-card {
        background: white;
        border-left: 5px solid #667eea;
        padding: 14px 16px;
        border-radius: 10px;
        margin: 8px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .job-card.high  { border-left-color: #28a745; }
    .job-card.med   { border-left-color: #ffc107; }
    .job-card.low   { border-left-color: #dc3545; }

    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
    }
    .badge.high { background:#d4edda; color:#155724; }
    .badge.med  { background:#fff3cd; color:#856404; }
    .badge.low  { background:#f8d7da; color:#721c24; }
    .badge.applied { background:#cce5ff; color:#004085; }

    /* Company type pill */
    .company-pill {
        display: inline-block;
        background: #e2e3f0;
        color: #4a4a8a;
        padding: 1px 8px;
        border-radius: 12px;
        font-size: 10px;
    }

    /* Status bar */
    .status-bar {
        background: #f0f2ff;
        border-left: 4px solid #667eea;
        padding: 10px 14px;
        border-radius: 8px;
        margin-bottom: 12px;
        font-size: 13px;
    }

    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 8px 20px;
        font-weight: 600;
        font-size: 13px;
        transition: 0.2s;
    }
    .stButton>button:hover { opacity: 0.9; transform: scale(1.02); }

    /* Link button */
    .apply-btn {
        display: inline-block;
        background: #28a745;
        color: white !important;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        text-decoration: none;
    }

    /* Tab bar override */
    .stTabs [data-baseweb="tab"] {
        font-size: 13px;
        padding: 8px 12px;
    }

    /* Mobile */
    @media (max-width: 768px) {
        .metric-box .num { font-size: 1.5rem; }
        .portal-header h1 { font-size: 1.2rem; }
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# DATABASE HELPERS
# ============================================================

@st.cache_resource
def get_db_connection():
    """Create persistent DB connection."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def run_query(sql, params=()):
    """Run a SELECT query and return DataFrame."""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


def run_write(sql, params=()):
    """Run INSERT/UPDATE."""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.execute(sql, params)
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def get_stats():
    """Get dashboard statistics."""
    stats = {"total": 0, "pending": 0, "high": 0, "applied": 0}
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM jobs")
        stats["total"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM jobs WHERE applied=0")
        stats["pending"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM jobs WHERE relevance_score>=65 AND applied=0")
        stats["high"] = cur.fetchone()[0]
        try:
            cur.execute("SELECT COUNT(*) FROM applications")
            stats["applied"] = cur.fetchone()[0]
        except: pass
        conn.close()
    except Exception:
        pass
    return stats


def mark_applied(job_id):
    """Mark a job as applied and log it."""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.execute("UPDATE jobs SET applied=1 WHERE job_id=?", (job_id,))
        try:
            conn.execute("""
                INSERT OR IGNORE INTO applications
                  (job_id, company, role, applied_date, status)
                SELECT job_id, company, title, ?, 'Applied'
                FROM jobs WHERE job_id=?
            """, (datetime.now().strftime("%Y-%m-%d"), job_id))
        except: pass
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# ============================================================
# BACKGROUND SCRAPER STATE
# ============================================================
if "scraper_status" not in st.session_state:
    st.session_state.scraper_status = "idle"   # idle | running | done | error
if "scraper_message" not in st.session_state:
    st.session_state.scraper_message = ""
if "last_run_time" not in st.session_state:
    st.session_state.last_run_time = None

_scraper_running = threading.Event()


def _run_scraper_thread():
    """Background thread to run the scraper."""
    try:
        result = subprocess.run(
            [sys.executable, MAIN_PY],
            cwd=BASE_DIR,
            capture_output=True, text=True, timeout=3600
        )
        if result.returncode == 0:
            st.session_state.scraper_status = "done"
            st.session_state.scraper_message = "✅ Completed successfully"
        else:
            st.session_state.scraper_status = "error"
            st.session_state.scraper_message = f"⚠️ {result.stderr[:200]}"
    except subprocess.TimeoutExpired:
        st.session_state.scraper_status = "error"
        st.session_state.scraper_message = "❌ Timed out (1 hour)"
    except Exception as e:
        st.session_state.scraper_status = "error"
        st.session_state.scraper_message = f"❌ {str(e)[:200]}"
    finally:
        st.session_state.last_run_time = datetime.now()
        _scraper_running.clear()


def start_scraper():
    """Start scraper in background thread."""
    if not _scraper_running.is_set():
        _scraper_running.set()
        st.session_state.scraper_status = "running"
        st.session_state.scraper_message = "🔄 Running... (5-15 min)"
        t = threading.Thread(target=_run_scraper_thread, daemon=True)
        t.start()
        return True
    return False


# ============================================================
# SCORE HELPERS
# ============================================================
def score_class(score):
    if score >= 70: return "high"
    if score >= 50: return "med"
    return "low"

def score_badge(score):
    cls = score_class(score)
    return f'<span class="badge {cls}">{score:.0f}% Match</span>'


# ============================================================
# JOB CARD RENDERER
# ============================================================
def render_job_card(row, show_apply=True, key_prefix=""):
    score = float(row.get("relevance_score", 0) or 0)
    title = row.get("title", "Unknown")
    company = row.get("company", "")
    location = row.get("location", "")
    exp = row.get("experience_required", "")
    link = row.get("application_link", "")
    source = row.get("source_platform", "")
    job_id = row.get("job_id", 0)
    applied = bool(row.get("applied", 0))

    cls = score_class(score)
    apply_tag = '<span class="badge applied">✅ Applied</span>' if applied else ""

    st.markdown(f"""
    <div class="job-card {cls}">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:4px;">
            <b style="font-size:14px; flex:1;">{title}</b>
            <div>{score_badge(score)} {apply_tag}</div>
        </div>
        <div style="margin-top:6px; font-size:12px; color:#555;">
            🏢 <b>{company}</b> &nbsp;|&nbsp; 📍 {location} &nbsp;|&nbsp; 💼 {exp}
        </div>
        <div style="margin-top:4px; font-size:11px; color:#888;">
            🔌 {source}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if show_apply and not applied:
        c1, c2 = st.columns([1, 1])
        with c1:
            if link:
                st.link_button("🔗 Apply Now", link, use_container_width=True)
        with c2:
            if st.button("✅ Mark Applied", key=f"{key_prefix}_{job_id}",
                         use_container_width=True):
                mark_applied(job_id)
                st.rerun()
    elif applied:
        st.markdown("")


# ============================================================
# MAIN APP
# ============================================================
def main():
    # Header
    st.markdown("""
    <div class="portal-header">
        <h1>🤖 AI Job Intelligence Portal</h1>
        <p>Abhilash Dharmarajula · Automated Multi-Source Job Search</p>
    </div>
    """, unsafe_allow_html=True)

    # Navigation tabs
    tabs = st.tabs(["📊 Dashboard", "💼 Jobs", "✅ Applications", "📈 Analytics", "⚙️ Control"])

    stats = get_stats()

    # ===========================================================
    # TAB 1: DASHBOARD
    # ===========================================================
    with tabs[0]:
        # Metrics row
        c1, c2, c3, c4 = st.columns(4)
        for col, num, label in [
            (c1, stats["total"],   "Total Jobs"),
            (c2, stats["pending"], "Pending"),
            (c3, stats["high"],    "High Match (65%+)"),
            (c4, stats["applied"], "Applied"),
        ]:
            with col:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="num">{num:,}</div>
                    <div class="lbl">{label}</div>
                </div>
                """, unsafe_allow_html=True)
                st.write("")

        # Status + Run Now
        scraper_st = st.session_state.scraper_status
        msg = st.session_state.scraper_message

        st.markdown(f"""
        <div class="status-bar">
            <b>Scraper:</b>
            {"🔄 Running in background... Check back in 10-15 minutes" if scraper_st == "running"
            else msg if msg
            else "⏸️ Idle — Click Run Now to scrape fresh jobs"}
            {"<br><small>Last run: " + st.session_state.last_run_time.strftime("%Y-%m-%d %H:%M") + "</small>"
            if st.session_state.last_run_time else ""}
        </div>
        """, unsafe_allow_html=True)

        run_col, refresh_col = st.columns([2, 1])
        with run_col:
            if scraper_st != "running":
                if st.button("▶ Run Scraper Now", use_container_width=True):
                    start_scraper()
                    st.info("🚀 Scraper started! It runs in background. Refresh page in 10-15 min.")
                    st.rerun()
            else:
                st.info("⏳ Scraper running in background...")
        with refresh_col:
            if st.button("🔄 Refresh Page", use_container_width=True):
                st.rerun()

        # Auto-refresh while running
        if scraper_st == "running":
            time.sleep(0.1)
            st.rerun()

        st.markdown("---")

        # Top 10 jobs
        st.subheader("🔥 Top Matches Right Now")
        df_top = run_query("""
            SELECT job_id, title, company, location, relevance_score,
                   application_link, experience_required, applied,
                   source_platform, company_type
            FROM jobs
            WHERE applied = 0
            ORDER BY relevance_score DESC, scraped_date DESC
            LIMIT 10
        """)

        if df_top.empty:
            st.warning("📭 No jobs yet. Click **Run Scraper Now** to fetch fresh jobs!")
        else:
            for _, row in df_top.iterrows():
                render_job_card(row.to_dict(), key_prefix="dash")

    # ===========================================================
    # TAB 2: ALL JOBS
    # ===========================================================
    with tabs[1]:
        st.subheader("💼 Job Browser")

        # Filters
        fc1, fc2, fc3, fc4 = st.columns([2, 1, 1, 1])
        with fc1:
            search = st.text_input("🔍 Search title / company",
                                   placeholder="data analyst, SQL, Goldman...")
        with fc2:
            min_score = st.slider("Min Score %", 0, 100, 40)
        with fc3:
            source_opts = ["All Sources", "Naukri", "LinkedIn", "Greenhouse (Direct API)",
                           "Lever (Direct API)", "Workday (Direct API)",
                           "SmartRecruiters (Direct API)", "Indeed",
                           "Instahyre", "Company Career Page"]
            sel_source = st.selectbox("Source", source_opts)
        with fc4:
            show_applied = st.checkbox("Show Applied", False)

        # Build query
        where = f"WHERE relevance_score >= {min_score}"
        if not show_applied:
            where += " AND applied = 0"
        if search:
            s = search.replace("'", "")
            where += f" AND (LOWER(title) LIKE '%{s.lower()}%' OR LOWER(company) LIKE '%{s.lower()}%')"
        if sel_source != "All Sources":
            where += f" AND source_platform = '{sel_source}'"

        df = run_query(f"""
            SELECT job_id, title, company, location, experience_required,
                   relevance_score, application_link, source_platform,
                   company_type, applied
            FROM jobs {where}
            ORDER BY relevance_score DESC, scraped_date DESC
            LIMIT 100
        """)

        if df.empty:
            st.info("No jobs match your filters.")
        else:
            st.caption(f"Showing **{len(df)}** jobs")
            for _, row in df.iterrows():
                render_job_card(row.to_dict(), key_prefix="browse")

    # ===========================================================
    # TAB 3: APPLICATIONS TRACKER
    # ===========================================================
    with tabs[2]:
        st.subheader("✅ Application Tracker")

        df_apps = run_query("""
            SELECT j.title, j.company, j.location, j.application_link,
                   j.relevance_score, j.scraped_date, j.source_platform
            FROM jobs j
            WHERE j.applied = 1
            ORDER BY j.scraped_date DESC
        """)

        if df_apps.empty:
            st.info("No applications yet. Mark jobs as applied to track them here.")
        else:
            st.metric("Total Applications", len(df_apps))

            # Summary
            by_source = df_apps.groupby("source_platform").size().reset_index(name="count")
            if not by_source.empty:
                fig = px.pie(by_source, values="count", names="source_platform",
                             title="Applications by Source",
                             color_discrete_sequence=px.colors.sequential.Viridis)
                fig.update_layout(height=250, margin=dict(t=30, b=0))
                st.plotly_chart(fig, use_container_width=True)

            # Table
            display_df = df_apps[["title", "company", "location", "source_platform"]].copy()
            display_df.columns = ["Role", "Company", "Location", "Source"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # Links
            st.markdown("### 🔗 Quick Apply Links")
            for _, row in df_apps.iterrows():
                if row.get("application_link"):
                    st.markdown(f"- [{row['title']} @ {row['company']}]({row['application_link']})")

    # ===========================================================
    # TAB 4: ANALYTICS
    # ===========================================================
    with tabs[3]:
        st.subheader("📈 Market Analytics")

        col1, col2 = st.columns(2)

        with col1:
            # Top companies hiring
            df_co = run_query("""
                SELECT company, COUNT(*) as jobs, ROUND(AVG(relevance_score),0) as avg_match
                FROM jobs WHERE applied=0 AND relevance_score >= 50
                GROUP BY company ORDER BY jobs DESC LIMIT 15
            """)
            if not df_co.empty:
                fig = px.bar(df_co, x="jobs", y="company", orientation="h",
                             color="avg_match", color_continuous_scale="Viridis",
                             title="Top 15 Companies with Matching Jobs",
                             labels={"jobs": "Job Count", "company": ""})
                fig.update_layout(height=400, showlegend=False,
                                  coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Source breakdown
            df_src = run_query("""
                SELECT source_platform, COUNT(*) as jobs
                FROM jobs GROUP BY source_platform ORDER BY jobs DESC
            """)
            if not df_src.empty:
                fig2 = px.pie(df_src, values="jobs", names="source_platform",
                              title="Jobs by Source Platform",
                              color_discrete_sequence=px.colors.qualitative.Pastel)
                fig2.update_layout(height=400)
                st.plotly_chart(fig2, use_container_width=True)

        # Score distribution
        df_score = run_query("""
            SELECT
                CASE
                    WHEN relevance_score>=80 THEN '80-100% (Excellent)'
                    WHEN relevance_score>=65 THEN '65-79% (Good)'
                    WHEN relevance_score>=50 THEN '50-64% (Okay)'
                    WHEN relevance_score>=35 THEN '35-49% (Low)'
                    ELSE 'Below 35%'
                END as bucket, COUNT(*) as count
            FROM jobs GROUP BY bucket ORDER BY min(relevance_score) DESC
        """)
        if not df_score.empty:
            fig3 = px.bar(df_score, x="bucket", y="count",
                          title="Match Score Distribution",
                          color="count", color_continuous_scale="Blues")
            fig3.update_layout(height=280, showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)

        # Daily trend
        df_trend = run_query("""
            SELECT DATE(scraped_date) as date, COUNT(*) as jobs
            FROM jobs GROUP BY DATE(scraped_date) ORDER BY date DESC LIMIT 14
        """)
        if not df_trend.empty:
            fig4 = px.line(df_trend.sort_values("date"), x="date", y="jobs",
                           title="Jobs Found Per Day (Last 14 Days)", markers=True)
            fig4.update_layout(height=250)
            st.plotly_chart(fig4, use_container_width=True)

    # ===========================================================
    # TAB 5: CONTROL PANEL
    # ===========================================================
    with tabs[4]:
        st.subheader("⚙️ Control Panel")

        # Environment info
        env_type = "☁️ Render Cloud" if IS_RENDER else "💻 Local Machine"
        st.info(f"**Environment:** {env_type}")

        # Manual scraper trigger
        st.markdown("### 🤖 Run Scraper")
        scraper_st = st.session_state.scraper_status
        msg = st.session_state.scraper_message

        if scraper_st == "running":
            st.warning("⏳ Scraper currently running in background...")
        else:
            last = st.session_state.last_run_time
            if last:
                st.success(f"{msg}  |  Last run: {last.strftime('%Y-%m-%d %H:%M')}")
            if st.button("▶ Start Full Scrape", use_container_width=True):
                start_scraper()
                st.rerun()

        st.markdown("---")

        # DB management
        st.markdown("### 🗄️ Database")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Jobs",  stats["total"])
        c2.metric("Pending",     stats["pending"])
        c3.metric("High Match",  stats["high"])
        c4.metric("Applied",     stats["applied"])

        if st.button("🗑️ Clear Old Irrelevant Jobs (< 40% + > 30 days)"):
            run_write("""
                DELETE FROM jobs
                WHERE relevance_score < 40
                  AND scraped_date < date('now', '-30 days')
                  AND applied = 0
            """)
            st.success("Done!")
            st.rerun()

        st.markdown("---")

        # Mobile app instructions
        st.markdown("### 📱 Access on Mobile")
        deploy_url = os.environ.get("RENDER_EXTERNAL_URL", "your-app.onrender.com")
        st.code(f"""
Your App URL:
  https://{deploy_url}

To add to Phone Home Screen:
  1. Open Chrome on your phone
  2. Go to the URL above
  3. Tap the 3 dots menu (⋮)
  4. Tap "Add to Home screen"
  5. Tap "Add"

You now have a native-like app icon!
""")

        # Schedule info
        st.markdown("### ⏰ Auto-Schedule on Render (Free)")
        st.markdown("""
**Set up auto-scraping every 6 hours:**

1. Go to **Render Dashboard** → Your Project
2. Click **+ New** → **Cron Job**
3. Settings:
   - **Name:** `job-scraper-6h`
   - **Command:** `python main.py`
   - **Schedule:** `0 */6 * * *`
   - **Environment:** Copy from web service
4. **Cost:** $0 (included in free tier!)

Your jobs will auto-update at:
- 12:00 AM, 6:00 AM, 12:00 PM, 6:00 PM
        """)

        # Source control
        st.markdown("### 🔧 Scraping Sources")
        sources_info = {
            "Naukri (Selenium)":        "✅ Local | ❌ Render",
            "LinkedIn (Selenium)":       "✅ Local | ❌ Render",
            "Greenhouse API":            "✅ Local | ✅ Render",
            "Lever API":                 "✅ Local | ✅ Render",
            "Workday API":               "✅ Local | ✅ Render",
            "SmartRecruiters API":       "✅ Local | ✅ Render",
            "Indeed (requests)":         "✅ Local | ✅ Render",
            "Instahyre (requests)":      "✅ Local | ✅ Render",
            "Company Pages (requests)":  "✅ Local | ✅ Render",
        }
        for src, status in sources_info.items():
            st.caption(f"**{src}** — {status}")


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    main()