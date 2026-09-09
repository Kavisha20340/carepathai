# CarePathAI — Development & Contribution Guide

Thank you for contributing to CarePathAI! This guide covers local environment setup, testing, and contribution conventions.

---

## 1. Local Environment Setup

### Backend Setup (Python 3.11)
```powershell
# 1. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # On Windows PowerShell
# source .venv/bin/activate    # On Linux / macOS

# 2. Install dependencies
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt

# 3. Configure local environment variables (.env in workspace root)
# Add: GCP_PROJECT=your-gcp-project-id
# Add: PLACES_API_KEY=your-google-places-key
# Add: MEDGEMMA_API_URL=http://localhost:8080/generate

# 4. Start backend server with auto-reload
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend Setup (Node.js 20+)
```bash
# 1. Navigate into frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```

---

## 2. Running Automated Integration Tests

Execute the comprehensive test suite (`backend/test_triage_flow.py`) covering multi-turn intake, emergency red-flag triggers, specialist mapping, acoustic denoising, and Hindi translation caching:

```powershell
python backend/test_triage_flow.py
```

---

## 3. Contribution Guidelines & Standards

| Domain | Standard |
|---|---|
| **Python Code Style** | PEP 8 compliant, type hints on FastAPI handlers and Pydantic models. |
| **React / JS Style** | ESLint + React Hooks rules, functional components, Zustand store encapsulation. |
| **Commit Messages** | Conventional Commits (`feat: ...`, `fix: ...`, `docs: ...`, `refactor: ...`). |
| **Pull Requests** | Target `v2` or `main` branch with clear description and test verification outputs. |

