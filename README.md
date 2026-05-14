# 🤖 AutoApply — AI Job Application Swarm

> Powered by [PraisonAI](https://github.com/MervinPraison/PraisonAI) — A production-ready multi-agent swarm that finds, scores, and auto-applies to jobs on Naukri.

---

## 🚀 Features

| Feature | Status |
|---|---|
| Resume parsing (PDF/DOCX) | ✅ |
| Naukri job search scraper | ✅ |
| AI job-resume scoring (0–100) | ✅ |
| Auto-apply for score > 70 | ✅ |
| Cover letter generator | ✅ |
| Application tracker (SQLite) | ✅ |
| Daily email digest | ✅ |
| Scheduler (cron) | ✅ |
| Docker support | ✅ |
| REST API (FastAPI) | ✅ |

---

## 🏗️ Architecture — Agent Swarm

```
┌──────────────────────────────────────────────────┐
│                  Orchestrator Agent               │
│         (coordinates the full pipeline)           │
└──────────┬──────────────────────────┬────────────┘
           │                          │
    ┌──────▼──────┐           ┌───────▼──────┐
    │ Resume      │           │  Job Search  │
    │ Parser      │           │  Agent       │
    │ Agent       │           │  (Naukri)    │
    └──────┬──────┘           └───────┬──────┘
           │                          │
    ┌──────▼──────────────────────────▼──────┐
    │           Job Scorer Agent              │
    │    (LLM-based resume ↔ JD matching)     │
    └──────────────────┬─────────────────────┘
                       │
    ┌──────────────────▼─────────────────────┐
    │         Application Agent              │
    │  (auto-fills & submits for score > 70) │
    └──────────────────┬─────────────────────┘
                       │
    ┌──────────────────▼─────────────────────┐
    │       Cover Letter Generator Agent     │
    └──────────────────┬─────────────────────┘
                       │
    ┌──────────────────▼─────────────────────┐
    │     Notification & Tracker Agent       │
    └────────────────────────────────────────┘
```

---

## ⚙️ Quick Start

### 1. Clone & Setup
```bash
git clone https://github.com/Bhushan-Khachane/autoapply.git
cd autoapply
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment
```bash
cp .env.example .env
# Fill in your credentials in .env
```

### 3. Add Your Resume
```bash
cp your_resume.pdf data/resume.pdf
```

### 4. Run the Swarm
```bash
python main.py
```

### 5. Or run via API
```bash
uvicorn api.main:app --reload
# POST http://localhost:8000/apply
```

### 6. Or via Docker
```bash
docker-compose up --build
```

---

## 📁 Project Structure

```
autoapply/
├── agents/
│   ├── orchestrator.py       # Master coordinator agent
│   ├── resume_parser.py      # PDF/DOCX resume extraction
│   ├── job_search.py         # Naukri scraper agent
│   ├── job_scorer.py         # LLM-based scoring agent
│   ├── applicator.py         # Browser automation agent
│   ├── cover_letter.py       # Cover letter generation agent
│   └── notifier.py           # Email + DB tracker agent
├── api/
│   └── main.py               # FastAPI REST interface
├── config/
│   └── settings.py           # All configuration
├── data/
│   └── resume.pdf            # Your resume (gitignored)
├── db/
│   └── tracker.py            # SQLite application tracker
├── scheduler/
│   └── cron.py               # APScheduler daily runs
├── tests/
│   ├── test_scorer.py
│   └── test_parser.py
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── main.py                   # Entry point
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔮 Roadmap

- [ ] LinkedIn integration
- [ ] Indeed / Monster support
- [ ] WhatsApp notifications via Twilio
- [ ] Multi-resume profile management
- [ ] Interview preparation agent
- [ ] Salary negotiation coach agent
- [ ] Browser extension for one-click apply
- [ ] Dashboard UI (Streamlit/React)

---

## 📄 License
MIT
