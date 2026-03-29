import streamlit as st
import pandas as pd
import json
import io
import anthropic
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pdfplumber
import re

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinSight AI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&family=DM+Mono&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.block-container { padding: 2rem 3rem 3rem; max-width: 1400px; }

h1, h2, h3 { font-family: 'DM Serif Display', serif !important; letter-spacing: -0.02em; }

.hero-title {
    font-family: 'DM Serif Display', serif;
    font-size: 3.2rem;
    line-height: 1.1;
    letter-spacing: -0.03em;
    margin: 0;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.hero-sub {
    font-size: 1.05rem;
    color: #64748b;
    margin-top: 0.5rem;
    font-weight: 300;
    letter-spacing: 0.01em;
}

.kpi-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s;
    position: relative;
    overflow: hidden;
}

.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
}

.kpi-label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94a3b8;
    margin-bottom: 0.4rem;
}

.kpi-value {
    font-family: 'DM Mono', monospace;
    font-size: 1.8rem;
    font-weight: 400;
    color: #0f172a;
    line-height: 1;
    margin-bottom: 0.3rem;
}

.kpi-change {
    font-size: 0.8rem;
    font-weight: 500;
}

.kpi-change.positive { color: #10b981; }
.kpi-change.negative { color: #ef4444; }
.kpi-change.neutral  { color: #94a3b8; }

.section-label {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #94a3b8;
    margin-bottom: 0.6rem;
}

.report-box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #6366f1;
    border-radius: 0 12px 12px 0;
    padding: 1.6rem 1.8rem;
    font-size: 0.95rem;
    line-height: 1.8;
    color: #334155;
    white-space: pre-wrap;
    font-family: 'DM Sans', sans-serif;
}

.anomaly-badge {
    display: inline-block;
    background: #fef3c7;
    color: #92400e;
    border: 1px solid #fcd34d;
    border-radius: 6px;
    padding: 0.15rem 0.5rem;
    font-size: 0.75rem;
    font-weight: 600;
    margin-right: 0.4rem;
    margin-bottom: 0.4rem;
}

.upload-zone {
    border: 2px dashed #c7d2fe;
    border-radius: 16px;
    padding: 2.5rem;
    text-align: center;
    background: #f5f3ff08;
}

.stButton > button {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0.65rem 1.8rem;
    font-weight: 500;
    font-size: 0.95rem;
    font-family: 'DM Sans', sans-serif;
    letter-spacing: 0.01em;
    cursor: pointer;
    width: 100%;
    transition: opacity 0.2s;
}

.stButton > button:hover { opacity: 0.88; }

.divider {
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 1.8rem 0;
}

[data-testid="stFileUploader"] {
    border: 2px dashed #c7d2fe;
    border-radius: 12px;
    padding: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_uploaded_file(uploaded_file) -> tuple[pd.DataFrame | None, str]:
    """Parse any uploaded file into a DataFrame + raw text preview."""
    name = uploaded_file.name.lower()
    raw_text = ""
    df = None

    try:
        if name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            raw_text = df.to_string(max_rows=80)

        elif name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded_file)
            raw_text = df.to_string(max_rows=80)

        elif name.endswith(".json"):
            data = json.load(uploaded_file)
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                # Try to find a list value to flatten
                for v in data.values():
                    if isinstance(v, list):
                        df = pd.DataFrame(v)
                        break
                if df is None:
                    df = pd.DataFrame([data])
            raw_text = df.to_string(max_rows=80) if df is not None else json.dumps(data, indent=2)[:3000]

        elif name.endswith(".pdf"):
            with pdfplumber.open(uploaded_file) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages[:8]]
            raw_text = "\n".join(pages)[:5000]
            # Try to extract tables
            with pdfplumber.open(uploaded_file) as pdf:
                tables = []
                for page in pdf.pages[:5]:
                    for t in (page.extract_tables() or []):
                        tables.append(t)
            if tables:
                headers = tables[0][0]
                rows = [r for t in tables for r in t[1:] if r]
                try:
                    df = pd.DataFrame(rows, columns=headers)
                    df = df.apply(pd.to_numeric, errors="ignore")
                except Exception:
                    df = None
        else:
            raw_text = uploaded_file.read().decode("utf-8", errors="ignore")[:3000]

    except Exception as e:
        return None, f"[Parse error: {e}]"

    return df, raw_text


def numeric_summary(df: pd.DataFrame) -> str:
    """Return a compact statistical summary of numeric columns."""
    num = df.select_dtypes(include="number")
    if num.empty:
        return "No numeric columns detected."
    return num.describe().to_string()


def call_claude(prompt: str, system: str) -> str:
    """Call Claude API and return the text response."""
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def extract_json_block(text: str) -> dict | list | None:
    """Pull the first JSON block out of a response."""
    match = re.search(r"```json\s*([\s\S]+?)\s*```", text)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    try:
        return json.loads(text)
    except Exception:
        return None


def get_kpis(raw_text: str, stats: str) -> dict:
    system = (
        "You are a senior financial analyst. "
        "Return ONLY a JSON object with this exact shape — no markdown, no explanation:\n"
        '{"kpis": [{"label": str, "value": str, "change": str, "direction": "positive"|"negative"|"neutral", "insight": str}], '
        '"anomalies": ["..."], "top_finding": "..."}\n'
        "Extract 4–6 meaningful financial KPIs. "
        "Format values with currency/%, magnitude (K/M). "
        "Anomalies: flag unusual values, outliers, or missing patterns."
    )
    prompt = f"DATA PREVIEW:\n{raw_text[:3000]}\n\nSTATISTICAL SUMMARY:\n{stats}"
    raw = call_claude(prompt, system)
    parsed = extract_json_block(raw)
    if parsed is None:
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"kpis": [], "anomalies": ["Could not parse response"], "top_finding": raw[:300]}
    return parsed


def get_chart_config(raw_text: str, columns: list[str]) -> dict:
    system = (
        "You are a data visualization expert. "
        "Given financial data, decide the best charts to build. "
        "Return ONLY a JSON array — no markdown, no preamble:\n"
        '[{"title": str, "type": "bar"|"line"|"pie"|"scatter"|"histogram", "x": str|null, "y": str|null, "color": str|null, "rationale": str}]\n'
        "Pick 2–4 charts that reveal trends, distributions, or comparisons. "
        "Only use column names from the provided list."
    )
    prompt = f"Columns available: {columns}\n\nDATA PREVIEW:\n{raw_text[:2000]}"
    raw = call_claude(prompt, system)
    parsed = extract_json_block(raw)
    if not isinstance(parsed, list):
        parsed = []
    return parsed


def get_report(raw_text: str, stats: str, kpi_data: dict) -> str:
    system = (
        "You are a financial analyst writing an executive summary report. "
        "Write a clear, professional 3–4 paragraph report in French or English (match the data language). "
        "Structure: 1) Overview & context, 2) Key findings & KPIs, 3) Risks & anomalies, 4) Recommendations. "
        "Be specific, use numbers. This report will be handed directly to a senior manager."
    )
    kpi_summary = json.dumps(kpi_data, ensure_ascii=False, indent=2)
    prompt = (
        f"DATA PREVIEW:\n{raw_text[:2500]}\n\n"
        f"STATISTICS:\n{stats}\n\n"
        f"EXTRACTED KPIs & ANOMALIES:\n{kpi_summary}"
    )
    return call_claude(prompt, system)


def build_chart(cfg: dict, df: pd.DataFrame):
    """Build a Plotly figure from chart config + dataframe."""
    ctype = cfg.get("type", "bar")
    x = cfg.get("x")
    y = cfg.get("y")
    color = cfg.get("color")
    title = cfg.get("title", "Chart")

    # Validate columns exist
    cols = df.columns.tolist()
    x = x if x in cols else None
    y = y if y in cols else None
    color = color if color in cols else None

    colors = ["#6366f1", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444"]

    try:
        if ctype == "line":
            fig = px.line(df, x=x, y=y, color=color, title=title,
                          color_discrete_sequence=colors)
        elif ctype == "pie":
            fig = px.pie(df, names=x, values=y, title=title,
                         color_discrete_sequence=colors)
        elif ctype == "scatter":
            fig = px.scatter(df, x=x, y=y, color=color, title=title,
                             color_discrete_sequence=colors)
        elif ctype == "histogram":
            fig = px.histogram(df, x=x or y, color=color, title=title,
                               color_discrete_sequence=colors)
        else:  # bar
            fig = px.bar(df, x=x, y=y, color=color, title=title,
                         color_discrete_sequence=colors)

        fig.update_layout(
            font_family="DM Sans",
            title_font_family="DM Serif Display",
            title_font_size=16,
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=20, r=20, t=48, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig.update_xaxes(showgrid=False, linecolor="#e2e8f0")
        fig.update_yaxes(showgrid=True, gridcolor="#f1f5f9", linecolor="#e2e8f0")
        return fig
    except Exception as e:
        return None


# ── App ───────────────────────────────────────────────────────────────────────

# Header
col_title, col_badge = st.columns([4, 1])
with col_title:
    st.markdown('<h1 class="hero-title">FinSight AI</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-sub">Upload any financial dataset · Get instant KPIs, charts & an executive report</p>',
        unsafe_allow_html=True,
    )
with col_badge:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div style="text-align:right;color:#94a3b8;font-size:0.75rem;font-family:DM Mono,monospace;margin-top:1rem">'
        'Powered by Claude AI<br>by Mohammed Amine Goumri</div>',
        unsafe_allow_html=True,
    )

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# Upload
st.markdown('<div class="section-label">① Upload your financial data</div>', unsafe_allow_html=True)
uploaded = st.file_uploader(
    "Drag & drop or browse",
    type=["csv", "xlsx", "xls", "json", "pdf"],
    label_visibility="collapsed",
)

if uploaded is None:
    st.markdown("""
    <div style="margin-top:2rem;padding:2rem;background:#f8fafc;border-radius:16px;border:1px solid #e2e8f0;text-align:center;color:#94a3b8">
        <div style="font-size:2.5rem;margin-bottom:0.5rem">📂</div>
        <div style="font-family:'DM Serif Display',serif;font-size:1.1rem;color:#64748b;margin-bottom:0.3rem">No file uploaded yet</div>
        <div style="font-size:0.85rem">Supports CSV · Excel · JSON · PDF</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Parse file
with st.spinner("Reading your file..."):
    df, raw_text = parse_uploaded_file(uploaded)

st.success(f"✓  **{uploaded.name}** loaded successfully")

# Show data preview
if df is not None:
    with st.expander("📋 Data preview", expanded=False):
        st.dataframe(df.head(20), use_container_width=True)
        st.caption(f"{len(df):,} rows · {len(df.columns)} columns")

# Analyze button
st.markdown("<br>", unsafe_allow_html=True)
run = st.button("🔍  Analyze with AI", use_container_width=False)

if not run:
    st.stop()

# ── Analysis ──────────────────────────────────────────────────────────────────
stats = numeric_summary(df) if df is not None else "No tabular data."

# KPIs
st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown('<div class="section-label">② Key Performance Indicators</div>', unsafe_allow_html=True)

with st.spinner("Extracting KPIs & anomalies..."):
    kpi_data = get_kpis(raw_text, stats)

kpis = kpi_data.get("kpis", [])
if kpis:
    cols = st.columns(min(len(kpis), 3))
    for i, kpi in enumerate(kpis):
        direction = kpi.get("direction", "neutral")
        arrow = "↑" if direction == "positive" else ("↓" if direction == "negative" else "→")
        with cols[i % 3]:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">{kpi.get('label','')}</div>
                <div class="kpi-value">{kpi.get('value','—')}</div>
                <div class="kpi-change {direction}">{arrow} {kpi.get('change','')}</div>
                <div style="font-size:0.78rem;color:#94a3b8;margin-top:0.5rem">{kpi.get('insight','')}</div>
            </div>
            """, unsafe_allow_html=True)

# Top finding banner
top = kpi_data.get("top_finding", "")
if top:
    st.markdown(f"""
    <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:12px;padding:1rem 1.4rem;margin-top:0.5rem">
        <span style="font-size:0.7rem;font-weight:600;letter-spacing:0.08em;color:#3b82f6;text-transform:uppercase">Top finding</span><br>
        <span style="color:#1e40af;font-size:0.95rem">{top}</span>
    </div>
    """, unsafe_allow_html=True)

# Anomalies
anomalies = kpi_data.get("anomalies", [])
if anomalies:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-label">⚠ Anomalies detected</div>', unsafe_allow_html=True)
    badges = "".join(f'<span class="anomaly-badge">{a}</span>' for a in anomalies)
    st.markdown(f'<div style="margin-top:0.4rem">{badges}</div>', unsafe_allow_html=True)

# ── Charts ────────────────────────────────────────────────────────────────────
if df is not None and not df.empty:
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">③ Trend & Distribution Charts</div>', unsafe_allow_html=True)

    with st.spinner("Generating chart recommendations..."):
        chart_cfgs = get_chart_config(raw_text, df.columns.tolist())

    if chart_cfgs:
        chart_cols = st.columns(2)
        for i, cfg in enumerate(chart_cfgs[:4]):
            fig = build_chart(cfg, df)
            if fig:
                with chart_cols[i % 2]:
                    st.plotly_chart(fig, use_container_width=True)
                    if cfg.get("rationale"):
                        st.caption(f"💡 {cfg['rationale']}")
    else:
        st.info("Not enough structured data to generate charts automatically.")

# ── Executive Report ──────────────────────────────────────────────────────────
st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown('<div class="section-label">④ Executive Report</div>', unsafe_allow_html=True)
st.markdown(
    '<p style="color:#64748b;font-size:0.88rem;margin-bottom:1rem">'
    'AI-generated analysis ready to share with your manager.</p>',
    unsafe_allow_html=True,
)

with st.spinner("Writing executive report..."):
    report_text = get_report(raw_text, stats, kpi_data)

st.markdown(f'<div class="report-box">{report_text}</div>', unsafe_allow_html=True)

# Download button
st.markdown("<br>", unsafe_allow_html=True)
report_bytes = report_text.encode("utf-8")
st.download_button(
    label="⬇ Download report (.txt)",
    data=report_bytes,
    file_name=f"finsight_report_{uploaded.name.split('.')[0]}.txt",
    mime="text/plain",
)

st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown(
    '<div style="text-align:center;color:#cbd5e1;font-size:0.78rem;font-family:DM Mono,monospace">'
    'FinSight AI · Built by Mohammed Amine Goumri · Powered by Claude</div>',
    unsafe_allow_html=True,
)
