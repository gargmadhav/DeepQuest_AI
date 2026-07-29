# 🚀 Hermes Autonomous AI Research Assistant (LangGraph Powered)

Hermes is an end-to-end **Autonomous AI Agent Platform** designed for deep technical research, web synthesis, and automated report generation. Powered by **LangGraph StateGraph orchestration** and **Groq LPU acceleration** (`llama-3.3-70b-versatile` & `llama-3.1-8b-instant`), Hermes receives high-level goals, breaks them down into executable multi-step plans, executes tools, self-evaluates report quality via a reflection loop, caches findings in local vector memory, and streams real-time execution logs to an interactive web dashboard.

---

## 🌟 Key Features

- **🤖 LangGraph StateGraph Architecture**: Compiled state machine (`Memory ➔ Planner ➔ Executor ➔ Reflection ➔ Correction / Indexing`).
- **🧰 10+ Integrated Agent Tools**:
  1. `search_web`: Live DuckDuckGo web search with fallback lookup.
  2. `summarize_text`: Groq LPU text summarization.
  3. `write_file`: Markdown research report file generator.
  4. `read_file`: Document & report file reader.
  5. `list_files`: Reports folder directory index.
  6. `query_memory`: Vector memory lookup (`memory.db`).
  7. `python_calculator`: Safe mathematical expression evaluator.
  8. `extract_citations`: URL citation parser and reference builder.
  9. `markdown_table_formatter`: Structured Markdown table generator.
  10. `text_sentiment_analyzer`: Tone, sentiment, and credibility analyzer.
- **⚡ Groq LPU Acceleration**: High-speed LLaMA-3 inference for reasoning, planning, and report synthesis.
- **🧠 Vector Memory System**: Local TF-IDF cosine similarity memory (`memory.db`) that recalls past research insights to guide future plans.
- **📡 Real-Time WebSocket Streaming**: Non-blocking async event loop streaming live step status and console output directly to the browser.
- **📦 Chat Archiving & Report Management**: Built-in support to archive chats into workspace folders and delete reports.
- **☀️/🌙 Theme Switcher**: Interactive Light/Dark theme switching.

---

## 📁 Repository Structure

```text
├── agent/
│   ├── orchestrator.py    # Compiled LangGraph StateGraph engine
│   ├── planner.py         # Multi-tool LLM plan generator
│   ├── executor.py        # 10-Tool execution logic & report synthesizer
│   ├── memory.py          # VectorMemory TF/Cosine similarity store
│   └── tools.py           # 10 Tool implementations & Groq client
├── backend/
│   ├── main.py            # FastAPI REST (/history, /report, /archive) & WebSockets (/ws/chat)
│   ├── database.py        # SQLAlchemy TaskRecord models & DB helpers
│   └── static/            # Frontend dashboard (index.html, index.css)
├── frontend/              # React UI source code (App.jsx, index.css, package.json)
├── reports/               # Output directory for generated Markdown research reports
├── test_agent.py          # Integration test script verifying LangGraph execution
├── .env                   # Environment config (GROQ_API_KEY)
└── backend/requirements.txt # Python dependencies (langgraph, langchain-core, groq, etc.)
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python 3.10+** installed.
- A free **Groq API Key** from [console.groq.com](https://console.groq.com/).

### 2. Environment Setup

Clone or open the repository directory in PowerShell / Terminal:

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Windows CMD:
.\.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Configure API Key

Create or update the `.env` file in the root project directory:

```env
GROQ_API_KEY=gsk_YourActualGroqApiKeyHere
```

---

## 🏃 Running the Application

### Option A: Web Application Mode (Recommended)
Start the FastAPI server (which hosts both the REST/WebSocket API and the web UI):

```bash
python -m uvicorn backend.main:app --port 8000 --reload
```

Open your browser and navigate to:  
👉 **`http://localhost:8000/`**

---

### Option B: Terminal CLI Test Mode
Run an autonomous research task directly from your terminal to verify LangGraph execution:

```bash
python test_agent.py
```

---

## 📡 API Reference

| Endpoint | Protocol | Description |
| :--- | :--- | :--- |
| `GET /` | HTTP | Serves the interactive web UI dashboard. |
| `GET /history` | HTTP | Returns a list of past research tasks ordered by date. |
| `GET /report/{id}` | HTTP | Returns detailed execution steps and full report text for a task ID. |
| `POST /archive/{id}` | HTTP | Archives a task chat and moves it into `ARCHIVED TASKS`. |
| `DELETE /report/{id}` | HTTP | Permanently deletes a report and task record from the database. |
| `WS /ws/chat` | WebSocket | Establishes a real-time connection to stream LangGraph execution logs and step status. |

---

## 🛠️ Technology Stack

- **Orchestration**: LangGraph (`langgraph`), LangChain Core (`langchain-core`)
- **Framework**: FastAPI, Uvicorn, WebSockets
- **Agent Intelligence**: Groq SDK (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`)
- **Database & Storage**: SQLite, SQLAlchemy, Custom TF-IDF Cosine Vector Store
- **Search Integration**: DuckDuckGo Search (`ddgs` / `duckduckgo-search`)
- **Frontend UI**: React 18, Lucide React, Vanilla CSS3 (Custom Dark & Light Theme Design System)
