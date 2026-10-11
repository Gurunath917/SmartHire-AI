# SmartHire AI — Frontend

React + Vite + Tailwind CSS

## Prerequisites
- Node.js 18+
- Backend running on http://127.0.0.1:8000

## Start (development)

```bash
cd frontend
npm install
npm run dev
```

Runs at: http://localhost:5173

## Build (production)

```bash
npm run build
```

Output: `dist/`

## Environment

`.env` file:
```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Pages built

| Route | Component | Status |
|-------|-----------|--------|
| `/login` | Login | ✅ |
| `/register` | Register | ✅ |
| `/candidate/dashboard` | CandidateDashboard | ✅ |
| `/candidate/resume` | Resume upload + parsing | ✅ |
| `/candidate/jobs` | Job browsing + matching | ✅ |
| `/candidate/assistant` | AI RAG chat | ✅ |
| `/recruiter/dashboard` | RecruiterDashboard | ✅ |
| All other pages | ComingSoon placeholder | 🚧 |
