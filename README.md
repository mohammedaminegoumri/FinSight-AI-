# 📊 FinSight AI

> Upload any financial dataset → Get instant KPIs, trend charts & an executive report powered by Claude AI.

Built by **Mohammed Amine Goumri** · Data Scientist & Business Analyst

---

## What it does

| Step | Action |
|------|--------|
| ① Upload | CSV, Excel, JSON or PDF financial data |
| ② Analyze | Claude AI extracts KPIs, detects anomalies & top findings |
| ③ Visualize | Auto-generated Plotly charts (trends, distributions, comparisons) |
| ④ Report | Executive summary ready to hand to your manager |

---

## Tech Stack

- **Frontend**: Streamlit
- **AI Engine**: Claude (Anthropic API) — `claude-sonnet-4-20250514`
- **Charts**: Plotly Express
- **Data**: Pandas · pdfplumber · openpyxl
- **Deployment**: Streamlit Cloud / local

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/finsight-ai.git
cd finsight-ai

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...

# 4. Run
streamlit run app.py
```

---

## Supported File Types

| Format | Notes |
|--------|-------|
| `.csv` | Standard comma-separated values |
| `.xlsx` / `.xls` | Excel workbooks (first sheet) |
| `.json` | Arrays of objects or nested dict with array |
| `.pdf` | Text extraction + table parsing (first 8 pages) |

---

## Example Use Cases

- **Portfolio performance** — upload your fund returns CSV and get Sharpe ratio, drawdown, trend charts
- **Sales report** — upload monthly Excel data and get revenue KPIs + anomaly flags
- **Bank statement** — upload transaction PDF and get spending analysis + summary
- **Financial model** — upload JSON output and get instant commentary

---

## Project Structure

```
finsight-ai/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
└── README.md
```

---

## Author

**Mohammed Amine Goumri**  
MSc Data Science & Business Analytics — Université Internationale de Rabat  
Former Data Scientist @ Bank Al-Maghrib  
[LinkedIn](https://linkedin.com) · mohammedaminegoumri@proton.me

---

## License

MIT — free to use, fork and build on.
