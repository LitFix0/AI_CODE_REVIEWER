# 🔍 AI Code Review Agent

> An autonomous agentic pipeline that clones a GitHub repository, parses Python source code using Abstract Syntax Trees (AST), submits code chunks to a Groq-powered LLM, and delivers actionable, confidence-rated review comments via a Streamlit dashboard.



---

## 📸 Preview

The agent analyzes real repositories and returns structured, filterable comments:

- **127 comments** found across 7 files in a sample run on [LitFix0/RAGBrain](https://github.com/LitFix0/RAGBrain)
- Breakdown: 0 Critical · 10 High · 39 Medium · 75 Low · 3 Info
- 107 high-confidence issues · 20 flagged for manual verification

---

## 🧠 What It Does

This is not a linter. It is a full agentic AI pipeline:

1. **Clones** any public GitHub repository using GitPython (depth=1 for speed)
2. **Parses** every Python file using Python's built-in `ast` module — extracting functions, classes, decorators, docstrings, and complexity hints
3. **Chunks** code intelligently — functions and classes are reviewed individually, not as raw line blocks
4. **Reviews** each chunk by sending it to Groq's LLaMA 3.3 70B model with a carefully engineered prompt that demands structured JSON output
5. **Scores confidence** — every comment includes a 0–100% self-rated confidence score
6. **Aggregates** all results and presents them in a filterable, downloadable dashboard

---

## 🏗️ Architecture

```
GitHub URL
    │
    ▼
┌──────────────────────┐
│   Ingestion Layer    │  GitPython — clone repo, walk .py files,
│   agent/ingestion.py │  skip large files & ignored dirs
└─────────┬────────────┘
          │ list of file dicts
          ▼
┌──────────────────────┐
│    AST Parser        │  Python ast module — extract functions,
│   agent/parser.py    │  classes, imports; chunk into slices ≤80 lines
└─────────┬────────────┘
          │ code chunks with metadata
          ▼
┌──────────────────────┐
│    LLM Reviewer      │  Groq API (LLaMA 3.3 70B) — engineered prompt
│   agent/reviewer.py  │  returns JSON: category, severity, confidence
└─────────┬────────────┘
          │ ReviewComment objects
          ▼
┌──────────────────────┐
│  Pipeline Orchestra  │  Coordinates all stages, handles errors,
│   agent/pipeline.py  │  computes aggregate stats
└─────────┬────────────┘
          │
          ▼
┌──────────────────────┐
│  Streamlit Dashboard │  Filter by severity/category/file,
│       app.py         │  download as Markdown or CSV
└──────────────────────┘
```

---

## 📁 Project Structure

```
ai_code_reviewer/
├── agent/
│   ├── __init__.py
│   ├── ingestion.py     # RepoIngestion — clone & collect Python files
│   ├── parser.py        # ASTParser — parse files & chunk for review
│   ├── reviewer.py      # LLMReviewer — Groq API calls & JSON parsing
│   └── pipeline.py      # Pipeline — orchestrate all stages end-to-end
├── utils/
│   ├── __init__.py
│   └── export.py        # to_markdown() and to_csv() report generators
├── .env                 # Your API key (never committed)
├── .gitignore
├── app.py               # Streamlit dashboard UI
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10+
- Git installed on your system
- A free [Groq API key](https://console.groq.com)

### Steps

```bash
# 1. Clone this repository
git clone https://github.com/YOUR_USERNAME/ai-code-reviewer
cd ai-code-reviewer

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\Activate.ps1

# Mac / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create a .env file in the root folder
echo GROQ_API_KEY=gsk_your_key_here > .env

# 5. Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501`

---

## 🌐 Deployment (Streamlit Cloud)

1. Push this repository to GitHub (must be public)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account → select this repo
4. Set **Main file path** to `app.py`
5. Go to **Settings → Secrets** and add:
   ```toml
   GROQ_API_KEY = "gsk_..."
   ```
6. Click **Deploy** — you'll get a shareable public URL

---

## ✨ Key Features

| Feature | Details |
|---------|---------|
| 🤖 Agentic pipeline | Fully autonomous: clone → parse → review → display |
| 🌳 AST-driven analysis | Functions and classes extracted precisely via Python's `ast` module |
| 📊 Confidence scoring | Every comment self-rated 0–100% by the LLM |
| ⚠️ Verify labels | Comments below 60% confidence flagged separately |
| 🎯 Structured output | LLM returns schema-validated JSON — no hallucinated free text |
| 🔍 Filters | Filter comments by severity, category, and file |
| 📥 Export | Download full report as Markdown or CSV |
| 🚀 Fast | Uses Groq's inference (LLaMA 3.3 70B) for sub-second LLM calls |

---

## 📊 Confidence Scoring System

Every review comment includes a confidence score rated by the LLM itself:

| Score | Label | Meaning |
|-------|-------|---------|
| 90–100% | 🟢 Certain | Clear evidence in the code — act on this |
| 70–89% | 🟢 Likely | Probable issue, minor context dependency |
| 60–69% | 🟡 Possible | Needs broader codebase context |
| < 60% | 🔴 ⚠️ Verify | Speculative — review manually before acting |

---

## 🔎 Severity Levels

| Severity | Meaning |
|----------|---------|
| 🔴 Critical | App-breaking bugs, crashes, major security holes |
| 🟠 High | Serious issues that should be fixed soon |
| 🟡 Medium | Notable problems, lower urgency |
| 🔵 Low | Minor improvements worth considering |
| ⚪ Info | Observations with no required action |

---

## ⚠️ Known Limitations

- Only **Python files** are supported (`.py`) — no JS, TypeScript, or Go
- Files **larger than 500 KB** are skipped automatically
- Maximum **30 files** and **20 chunks per file** per run (cost/speed tradeoff)
- **Private repositories** are not supported without a GitHub Personal Access Token
- No caching — unchanged files are re-reviewed on every run

---

## 🔮 What I'd Build Next

- **GitHub PR commenter** — post inline review comments directly to pull requests via GitHub API
- **JavaScript / TypeScript support** — using `tree-sitter` for multi-language AST parsing
- **Caching layer** — skip files that haven't changed since the last review
- **Diff mode** — review only the lines changed in a PR, not the full file
- **Per-repo config** — `.codereview.yml` for custom rules and ignore patterns
- **Severity thresholds** — fail CI pipeline if critical issues are found

---

## 🧪 Tested On

| Repository | Files | Comments Found |
|------------|-------|---------------|
| [LitFix0/RAGBrain](https://github.com/LitFix0/RAGBrain) | 7 | 127 |
| [pallets/flask](https://github.com/pallets/flask) | 30 | — |
| [psf/requests](https://github.com/psf/requests) | 30 | — |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Repository cloning | GitPython |
| Code parsing | Python `ast` (built-in) |
| LLM inference | Groq API — LLaMA 3.3 70B Versatile |
| Orchestration | Custom Python pipeline |
| Dashboard | Streamlit |
| Export | Markdown + CSV |
| Deployment | Streamlit Cloud |

---

## 📜 Academic Integrity & AI Use Policy

This project was built independently as part of a 3-day assignment.

- ✅ AI assistants (Claude, Copilot) were used to help write **individual code snippets**
- ✅ All **architecture decisions**, prompt design, and integration logic are original
- ✅ All code in this repository is code I understand and can explain
- ❌ AI was not used to generate the entire project end-to-end

---

## 📄 License

MIT License — free to use, modify, and distribute.
