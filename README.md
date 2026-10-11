# SmartHire AI — AI-Powered Recruitment & Candidate Intelligence Platform

> **Status:** 🚧 Under active development

SmartHire AI is a full-stack, AI/ML-powered recruitment platform that connects candidates and recruiters through intelligent workflows — resume parsing, semantic job matching, skill gap analysis, personalized learning roadmaps, and AI-driven mock interviews.

---

## Features (Overview)

| Feature | Description |
|---------|-------------|
| Resume Parsing | PDF upload → NLP skill extraction |
| AI Job Matching | TF-IDF + Sentence Embeddings + weighted score |
| Skill Gap Analysis | Required vs. candidate skills comparison |
| ML Candidate Ranking | XGBoost/RF with SHAP explainability |
| Learning Roadmap | LLM-generated week-by-week plan |
| RAG Career Assistant | Vector search + LLM Q&A with citations |
| AI Mock Interview | LLM question generation + answer evaluation |
| Dashboards | Candidate, Recruiter, Admin with charts |

---

## Technology Stack

**Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL, JWT  
**Frontend:** React, Vite, Tailwind CSS, Recharts  
**ML/NLP:** Scikit-learn, spaCy, Sentence Transformers, XGBoost, SHAP  
**GenAI/RAG:** LLM API, LangChain, FAISS/Chroma, Embeddings  

> Docker is NOT used. Runs locally with Python + Node.js + PostgreSQL.

---

## Quick Start

See [Installation](#installation) below.

---

## Project Structure

```
SmartHire-AI/
├── backend/          # FastAPI backend
├── frontend/         # React frontend
├── ml/               # ML training pipeline
├── rag/              # RAG document pipeline
├── tests/            # Pytest test suite
├── data/             # Sample / seed data
└── README.md
```

---

## Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
# copy .env.example to .env and fill in values
python -m uvicorn app.main:app --reload
```

Backend runs at: http://127.0.0.1:8000  
Swagger docs: http://127.0.0.1:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:5173

---

## Environment Variables

See `backend/.env.example` for all required variables.

---

## Testing

```bash
cd backend
pytest tests/ -v
```

---

## Limitations

- Match scores are internal heuristics, not guaranteed hiring probabilities.
- ML ranking is a decision-support tool — no autonomous hiring decisions.
- LLM-generated content (roadmaps, interview feedback) should be reviewed critically.
- Initial ML pipeline uses a synthetic demo dataset.

---

## License

For portfolio/educational use.
