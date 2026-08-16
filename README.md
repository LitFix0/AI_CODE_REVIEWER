# 🔍 AI Code Review Agent

> An autonomous agentic pipeline that clones a GitHub repository, parses source code structurally using language-specific parsers, submits code chunks to a Groq-powered LLM, and delivers actionable, confidence-rated review comments via a Streamlit dashboard.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red?style=flat-square&logo=streamlit)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-orange?style=flat-square)
![Languages](https://img.shields.io/badge/Languages-Python_|_Rust_|_JavaScript-green?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## 🚀 Live Demo

> **[👉 Click here to try the live app](https://aicodereviewer-cgd6nbbjdkq8dbttnihrjo.streamlit.app/)**

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
2. **Detects** supported source files (`.py`, `.rs`, `.js`, `.ts`, `.jsx`, `.tsx`) automatically
3. **Parses** each file using a language-specific parser — AST for Python, regex-based structural extraction for Rust and JavaScript/TypeScript
4. **Chunks** code intelligently — functions and classes are reviewed individually, not as raw line blocks
5. **Reviews** each chunk by sending it to Groq's LLaMA 3.3 70B model with a carefully engineered prompt that demands structured JSON output
6. **Scores confidence** — every comment includes a 0–100% self-rated confidence score
7. **Aggregates** all results and presents them in a filterable, downloadable dashboard

---

## 🌐 Supported Languages

| Language | Extensions | Parser Method |
|----------|-----------|---------------|
| 🐍 Python | `.py` | Python built-in `ast` module — full syntax-aware parsing |
| 🦀 Rust | `.rs` | Regex-based structural extraction — fn, struct, enum, impl, trait, mod |
| 🟨 JavaScript | `.js`, `.jsx` | Regex-based structural extraction — functions, classes, arrow functions |
| 🔷 TypeScript | `.ts`, `.tsx` | Same as JS parser with interface and type alias support |

---

## 🏗️ Architecture

```
GitHub URL
    │
    ▼
┌──────────────────────┐
│   Ingestion Layer    │  GitPython — clone repo, auto-detect supported files
│   agent/ingestion.py │  by querying PARSER_REGISTRY for extensions
└─────────┬────────────┘
          │ list of file dicts
          ▼
┌──────────────────────┐
│  Parser Dispatcher   │  Routes each file to the correct language parser
│   agent/parser.py    │  by file extension — never needs editing
└─────────┬────────────┘
          │
    ┌─────┴──────────────────────────┐
    │   agent/parsers/               │
    │   ├── base.py (interface)      │  Abstract base class all parsers implement
    │   ├── python_parser.py         │  AST-based — precise structural extraction
    │   ├── rust_parser.py           │  Regex-based — fn, struct, impl, trait, enum
    │   └── js_parser.py             │  Regex-based — function, class, arrow fn, TS types
    └─────┬──────────────────────────┘
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
│   ├── ingestion.py          # RepoIngestion — clone & collect files dynamically
│   ├── parser.py             # Dispatcher — routes files to correct parser
│   ├── parsers/
│   │   ├── __init__.py       # PARSER_REGISTRY — register languages here
│   │   ├── base.py           # BaseParser — interface all parsers implement
│   │   ├── python_parser.py  # Python AST parser
│   │   ├── rust_parser.py    # Rust structural parser
│   │   ├── js_parser.py      # JavaScript/TypeScript structural parser
│   │   └── go_parser.py      # Go parser (placeholder — future)
│   ├── reviewer.py           # LLMReviewer — Groq API + JSON parsing
│   └── pipeline.py           # Pipeline — orchestrate all stages end-to-end
├── utils/
│   ├── __init__.py
│   └── export.py             # to_markdown() and to_csv() report generators
├── .env                      # Your API key (never committed)
├── .gitignore
├── app.py                    # Streamlit dashboard UI
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
git clone https://github.com/LitFix0/ai-code-reviewer
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
| 🌍 Multi-language | Python (AST), Rust, JavaScript, TypeScript all supported |
| 🔌 Extensible architecture | Add a new language by creating one file + one registry entry |
| 🌳 Structural parsing | Functions and classes extracted precisely, not by line count |
| 📊 Confidence scoring | Every comment self-rated 0–100% by the LLM |
| ⚠️ Verify labels | Comments below 60% confidence flagged separately |
| 🎯 Structured output | LLM returns schema-validated JSON — no hallucinated free text |
| 🔍 Filters | Filter comments by severity, category, and file |
| 📥 Export | Download full report as Markdown or CSV |
| 🚀 Fast inference | Groq LLaMA 3.3 70B — sub-second LLM calls |

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

## 🔌 Adding a New Language

The architecture is designed so adding a new language requires exactly **2 steps**:

**Step 1** — Create `agent/parsers/go_parser.py`:
```python
from agent.parsers.base import BaseParser, ParsedFile

class GoParser(BaseParser):
    LANGUAGE   = "go"
    EXTENSIONS = [".go"]

    def parse_and_chunk(self, file_info, max_lines=None):
        # your parsing logic here
        return parsed_file, chunks
```

**Step 2** — Register in `agent/parsers/__init__.py`:
```python
from agent.parsers.go_parser import GoParser

for _parser in [PythonParser(), RustParser(), JavaScriptParser(), GoParser()]:
    ...
```

That's it — ingestion, dispatcher, reviewer, and app all update automatically.

---

## ⚠️ Known Limitations

- Files **larger than 500 KB** are skipped automatically
- Maximum **30 files** and **20 chunks per file** per run (cost/speed tradeoff)
- **Private repositories** are not supported without a GitHub Personal Access Token
- JavaScript/TypeScript parser is regex-based — complex nested patterns may not parse perfectly
- No caching — unchanged files are re-reviewed on every run
- Groq free tier: 100,000 tokens/day for LLaMA 3.3 70B (resets at midnight UTC / 5:30 AM IST)

---

## 🔮 What I'd Build Next

- **GitHub PR commenter** — post inline review comments directly to pull requests via GitHub API
- **Go language support** — complete the Go parser placeholder
- **Caching layer** — skip files that haven't changed since the last review
- **Diff mode** — review only lines changed in a PR, not the full file
- **Per-repo config** — `.codereview.yml` for custom rules and ignore patterns
- **CI/CD integration** — GitHub Action that fails the pipeline on critical issues

---

## 🧪 Tested On

| Repository | Language | Files | Comments Found |
|------------|----------|-------|---------------|
| [LitFix0/RAGBrain](https://github.com/LitFix0/RAGBrain) | Python | 7 | 127 |
| [ManuSharma0702/ocr-service](https://github.com/ManuSharma0702/ocr-service) | Rust | 9 | — |
| [pallets/flask](https://github.com/pallets/flask) | Python | 30 | — |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Repository cloning | GitPython |
| Python parsing | Python `ast` (built-in) |
| Rust parsing | Regex-based structural extraction |
| JS/TS parsing | Regex-based structural extraction |
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

## 🧪 Data Sources Used for Testing

- [LitFix0/RAGBrain](https://github.com/LitFix0/RAGBrain) — Python RAG application
- [ManuSharma0702/ocr-service](https://github.com/ManuSharma0702/ocr-service) — Rust OCR service
- [pallets/flask](https://github.com/pallets/flask) — Python web framework
- [psf/requests](https://github.com/psf/requests) — Python HTTP library

---

## 📄 License

MIT License — free to use, modify, and distribute.