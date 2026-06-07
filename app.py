"""
AI Code Review Agent — Streamlit Dashboard
"""

import os
import sys
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.pipeline import Pipeline, PipelineResult
from agent.reviewer import ReviewComment
from utils.export import to_markdown, to_csv

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Code Reviewer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Sora:wght@400;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Sora', sans-serif; }
    code, pre, .stCode { font-family: 'JetBrains Mono', monospace !important; }

    .main { background: #0d1117; }
    .block-container { padding-top: 2rem; }

    /* Cards */
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        text-align: center;
    }
    .metric-card .value { font-size: 2rem; font-weight: 700; }
    .metric-card .label { font-size: 0.8rem; color: #8b949e; margin-top: 4px; }

    /* Severity badges */
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-critical { background: #3d1a1a; color: #ff6b6b; border: 1px solid #ff6b6b44; }
    .badge-high     { background: #3d2a1a; color: #ffa94d; border: 1px solid #ffa94d44; }
    .badge-medium   { background: #3d3a1a; color: #ffd43b; border: 1px solid #ffd43b44; }
    .badge-low      { background: #1a2a3d; color: #74c0fc; border: 1px solid #74c0fc44; }
    .badge-info     { background: #1e2328; color: #8b949e; border: 1px solid #30363d; }
    .badge-verify   { background: #2d1f3d; color: #da77f2; border: 1px solid #da77f244; }

    /* Comment card */
    .comment-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-left: 4px solid #30363d;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
    }
    .comment-card.critical { border-left-color: #ff6b6b; }
    .comment-card.high     { border-left-color: #ffa94d; }
    .comment-card.medium   { border-left-color: #ffd43b; }
    .comment-card.low      { border-left-color: #74c0fc; }
    .comment-card.info     { border-left-color: #8b949e; }

    .comment-title { font-weight: 600; font-size: 0.95rem; margin-bottom: 0.4rem; }
    .comment-meta  { font-size: 0.78rem; color: #8b949e; margin-bottom: 0.6rem; font-family: 'JetBrains Mono', monospace; }
    .comment-body  { font-size: 0.88rem; line-height: 1.6; color: #c9d1d9; }
    .comment-suggestion { background: #0d2116; border: 1px solid #238636; border-radius: 6px; padding: 0.6rem 0.8rem; margin-top: 0.5rem; font-size: 0.85rem; color: #3fb950; }

    .confidence-bar-bg { background: #21262d; border-radius: 4px; height: 6px; width: 100%; margin-top: 4px; }
    .confidence-bar    { height: 6px; border-radius: 4px; }

    /* Verify label */
    .verify-label {
        background: #2d1f3d;
        border: 1px solid #da77f2;
        color: #da77f2;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
    }

    /* Sidebar */
    .css-1d391kg { background: #010409; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background: transparent; }
    .stTabs [data-baseweb="tab"] {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px 8px 0 0;
        color: #8b949e;
        font-family: 'Sora', sans-serif;
    }
    .stTabs [aria-selected="true"] {
        background: #1f6feb22;
        border-color: #1f6feb;
        color: #58a6ff;
    }

    /* File chip */
    .file-chip {
        display: inline-block;
        background: #21262d;
        border: 1px solid #30363d;
        border-radius: 4px;
        padding: 2px 8px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: #8b949e;
        margin: 2px;
    }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

SEVERITY_COLOR = {
    "critical": "#ff6b6b",
    "high": "#ffa94d",
    "medium": "#ffd43b",
    "low": "#74c0fc",
    "info": "#8b949e",
}

SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
    "info": "⚪",
}


def confidence_bar(confidence: int) -> str:
    color = "#3fb950" if confidence >= 70 else "#ffa94d" if confidence >= 50 else "#ff6b6b"
    return f"""
    <div class="confidence-bar-bg">
        <div class="confidence-bar" style="width:{confidence}%; background:{color};"></div>
    </div>
    """


def render_comment_card(c: ReviewComment):
    verify_html = '<span class="verify-label">⚠ VERIFY THIS</span>' if c.low_confidence else ""
    badge_class = f"badge-{c.severity}"
    st.markdown(f"""
    <div class="comment-card {c.severity}">
        <div class="comment-title">
            <span class="badge {badge_class}">{c.severity.upper()}</span>&nbsp;
            <span style="color:#e6edf3">{c.title}</span>&nbsp;{verify_html}
        </div>
        <div class="comment-meta">
            📄 {c.file} &nbsp;·&nbsp; line {c.line} &nbsp;·&nbsp;
            🏷 {c.category} &nbsp;·&nbsp; 🔷 {c.chunk_type}: <code>{c.chunk_name}</code>
        </div>
        <div class="comment-body">{c.description}</div>
        <div class="comment-suggestion">💡 {c.suggestion}</div>
        <div style="margin-top:8px; font-size:0.78rem; color:#8b949e;">
            Confidence: {c.confidence}%
            {confidence_bar(c.confidence)}
        </div>
    </div>
    """, unsafe_allow_html=True)


def metric_card(value, label, color="#58a6ff"):
    st.markdown(f"""
    <div class="metric-card">
        <div class="value" style="color:{color}">{value}</div>
        <div class="label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🔍 AI Code Reviewer")
    st.markdown("*Autonomous code review with confidence scoring*")
    st.divider()

    # API key — load from .env silently, fallback to manual input
    api_key = os.environ.get("GROQ_API_KEY", "")
    if api_key:
        st.success("✅ API key loaded", icon="🔑")
    else:
        api_key = st.text_input(
            "Groq API Key",
            type="password",
            help="Not found in .env — paste your key here. Get one free at console.groq.com",
        )

    repo_url = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/user/repo",
        help="Public GitHub repo URL to review.",
    )

    model = st.selectbox(
        "Model",
        ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        index=0,
    )

    st.divider()
    run_btn = st.button("🚀 Run Review", use_container_width=True, type="primary")
    st.divider()
    st.markdown("""
    **How it works:**
    1. Clones your repo (depth=1)
    2. Parses source files with AST
    3. Sends code chunks to Groq LLM
    4. Aggregates confidence-rated comments

    **Supported languages:**
    - 🐍 Python (.py) — AST parsing
    - 🦀 Rust (.rs) — Structural parsing

    **Confidence scoring:**
    - 🟢 ≥70% — High confidence
    - 🟡 50–69% — Needs context
    - 🔴 <60% — ⚠️ Verify this
    """)


# ── Main area ─────────────────────────────────────────────────────────────────

st.markdown("# 🔍 AI Code Review Agent")
st.markdown("Autonomous repository analysis powered by Groq · Python & Rust · Confidence scoring")
st.divider()

# Session state
if "result" not in st.session_state:
    st.session_state.result = None

# ── Run pipeline ──────────────────────────────────────────────────────────────

if run_btn:
    if not api_key:
        st.error("API key not found. Add GROQ_API_KEY to your .env file or paste it in the sidebar.")
    elif not repo_url or not repo_url.startswith("http"):
        st.error("Please enter a valid GitHub repository URL.")
    else:
        progress_text = st.empty()
        progress_bar = st.progress(0)

        def update_progress(msg: str, cur: int, tot: int):
            progress_text.markdown(f"⏳ **{msg}**")
            progress_bar.progress(min(cur / max(tot, 1), 1.0))

        with st.spinner(""):
            try:
                pipeline = Pipeline(
                    api_key=api_key,
                    model=model,
                    progress_callback=update_progress,
                )
                result = pipeline.run(repo_url)
                st.session_state.result = result
                progress_text.empty()
                progress_bar.empty()
                st.success(f"✅ Review complete! Found {len(result.all_comments)} comments across {result.total_files_analyzed} files.")
            except Exception as e:
                progress_text.empty()
                progress_bar.empty()
                st.error(f"Pipeline error: {e}")

# ── Display results ───────────────────────────────────────────────────────────

result: PipelineResult = st.session_state.result

if result is None:
    st.markdown("""
    <div style="text-align:center; padding:4rem 0; color:#8b949e;">
        <div style="font-size:3rem;">🤖</div>
        <div style="font-size:1.2rem; margin-top:1rem; color:#c9d1d9;">Enter a GitHub URL and click <strong>Run Review</strong></div>
        <div style="margin-top:0.5rem;">The agent will clone, parse, and review your Python & Rust code automatically.</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Summary metrics ───────────────────────────────────────────────────────────

cols = st.columns(5)
sev_colors = {
    "critical": "#ff6b6b",
    "high": "#ffa94d",
    "medium": "#ffd43b",
    "low": "#74c0fc",
    "info": "#8b949e",
}
sev_labels = ["critical", "high", "medium", "low", "info"]
for col, sev in zip(cols, sev_labels):
    with col:
        metric_card(
            result.by_severity.get(sev, 0),
            f"{SEVERITY_EMOJI[sev]} {sev.title()}",
            color=sev_colors[sev],
        )

st.markdown("&nbsp;")
c1, c2, c3 = st.columns(3)
with c1:
    metric_card(result.total_files_analyzed, "Files Analyzed", "#58a6ff")
with c2:
    metric_card(len(result.high_confidence), "High-Confidence Issues", "#3fb950")
with c3:
    metric_card(len(result.low_confidence), "⚠ Verify These", "#da77f2")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs([
    "📋 All Comments",
    "⚠️ Low Confidence",
    "📊 Analytics",
    "📥 Export",
])

# ── Tab 1: All Comments with filters ─────────────────────────────────────────

with tab1:
    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        sev_filter = st.multiselect(
            "Filter by Severity",
            options=["critical", "high", "medium", "low", "info"],
            default=["critical", "high", "medium", "low", "info"],
        )
    with col_f2:
        cat_options = sorted(result.by_category.keys())
        cat_filter = st.multiselect(
            "Filter by Category",
            options=cat_options,
            default=cat_options,
        )
    with col_f3:
        file_options = sorted(result.by_file.keys())
        file_filter = st.multiselect(
            "Filter by File",
            options=file_options,
            default=file_options,
        )

    filtered = [
        c for c in result.all_comments
        if c.severity in sev_filter
        and c.category in cat_filter
        and c.file in file_filter
    ]

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    filtered.sort(key=lambda c: sev_order.get(c.severity, 99))

    st.markdown(f"**Showing {len(filtered)} of {len(result.all_comments)} comments**")
    st.markdown("&nbsp;")

    if not filtered:
        st.info("No comments match the current filters.")
    else:
        for c in filtered:
            render_comment_card(c)

# ── Tab 2: Low Confidence ─────────────────────────────────────────────────────

with tab2:
    st.markdown("""
    > These comments scored **below 60% confidence**. They may be valid issues,
    > but require manual verification — context outside the visible code chunk
    > could change the picture.
    """)
    if not result.low_confidence:
        st.success("🎉 No low-confidence issues! All comments are high-confidence.")
    else:
        for c in sorted(result.low_confidence, key=lambda c: c.confidence):
            render_comment_card(c)

# ── Tab 3: Analytics ──────────────────────────────────────────────────────────

with tab3:
    a1, a2 = st.columns(2)

    with a1:
        st.markdown("#### Issues by Severity")
        sev_df = pd.DataFrame(
            [(k, v) for k, v in result.by_severity.items()],
            columns=["Severity", "Count"],
        ).sort_values("Count", ascending=False)
        st.bar_chart(sev_df.set_index("Severity"), color="#1f6feb")

    with a2:
        st.markdown("#### Issues by Category")
        cat_df = pd.DataFrame(
            [(k, v) for k, v in result.by_category.items()],
            columns=["Category", "Count"],
        ).sort_values("Count", ascending=False)
        st.bar_chart(cat_df.set_index("Category"), color="#3fb950")

    st.markdown("#### Issues by File")
    file_df = pd.DataFrame(
        [(k, v) for k, v in result.by_file.items()],
        columns=["File", "Issues"],
    ).sort_values("Issues", ascending=False)
    st.dataframe(file_df, use_container_width=True, hide_index=True)

    st.markdown("#### Confidence Distribution")
    conf_data = [c.confidence for c in result.all_comments]
    if conf_data:
        conf_df = pd.DataFrame({"Confidence": conf_data})
        st.bar_chart(conf_df["Confidence"].value_counts().sort_index())

    if result.repo_metadata:
        st.markdown("#### Repository Metadata")
        st.json(result.repo_metadata)

    if result.errors:
        st.markdown("#### Pipeline Errors")
        for err in result.errors:
            st.warning(err)

# ── Tab 4: Export ─────────────────────────────────────────────────────────────

with tab4:
    st.markdown("#### Download your review report")

    col_e1, col_e2 = st.columns(2)

    with col_e1:
        md_content = to_markdown(result)
        st.download_button(
            label="📄 Download Markdown Report",
            data=md_content,
            file_name="code_review_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.caption("Full report with all comments, summary, and metadata.")

    with col_e2:
        csv_content = to_csv(result)
        st.download_button(
            label="📊 Download CSV",
            data=csv_content,
            file_name="code_review_comments.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.caption("Tabular format — import into Excel, Notion, Jira, etc.")

    st.divider()
    st.markdown("#### Markdown Preview")
    with st.expander("Show full report"):
        st.code(md_content, language="markdown")