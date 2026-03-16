# LLM Voice Agent Test Harness + API Validator

Mini platform to simulate healthcare-style patient calls, run an LLM-style agent, and validate whether tool/API calls are correct.

## Stack
- Backend: FastAPI + Pydantic + SQLite
- Frontend: React + TypeScript (Vite)
- Tests: pytest
- CI: GitHub Actions (tests + lint + frontend build)

## Core Features
- `/scenarios` endpoints to create/list/update scenarios.
- `/runs` endpoint to run scenario batches and score outcomes.
- Tool endpoints:
  - `POST /tools/book_appointment`
  - `POST /tools/refill_medication`
  - `POST /tools/get_office_hours`
- Strict request/response validation with Pydantic.
- Structured run traces stored in SQLite (`backend/runs.db`).
- Evaluator metrics:
  - tool-call accuracy
  - schema validation pass rate
  - conversation success rate

## Run locally
### Backend
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## API quickstart
1. Create scenario:
```bash
curl -X POST http://127.0.0.1:8000/scenarios \
  -H "content-type: application/json" \
  -d '{"name":"Refill no DOB","transcript":"I am John. Need refill for lisinopril","goal":"refill_medication","expected":{}}'
```
2. Run scenarios:
```bash
curl -X POST http://127.0.0.1:8000/runs -H "content-type: application/json" -d '{}'
```

## Notes
- Synthetic data only.
- Includes edge-case handling for missing DOB, unsupported medications, and invalid appointment dates.
