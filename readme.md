# Resume-Aware RAG Interview System

An AI-powered technical interview system that demonstrates role-aware Retrieval-Augmented Generation, grounded question generation, adaptive interview flow, and explainable retrieval evidence.

## Architecture

```text
frontend/ Next.js + React + TypeScript + Tailwind + shadcn/ui
backend/  FastAPI + SQLAlchemy + ChromaDB + Sentence Transformers + Gemini
```

Backend structure:

```text
backend/app
  api/        FastAPI routers
  services/   resume parsing and interview orchestration
  rag/        ingestion, retrieval, reranking, generation
  models/     SQLAlchemy persistence models
  db/         database session and initialization
  schemas/    reserved for typed API schemas
  utils/      reserved shared helpers
```

## RAG Pipeline

The interview flow is:

```text
Resume upload
Resume parsing
Skill/domain extraction
Role selection
Gemini retrieval-query generation
SentenceTransformer embedding
ChromaDB cosine retrieval
Lightweight reranking
Context selection
Grounded question generation
Answer evaluation
Adaptive difficulty update
Repeat
Final summary
```

## Knowledge Base Ingestion

PDF parsing uses only PyMuPDF. Chunking uses `RecursiveCharacterTextSplitter` with:

- chunk size: `800`
- overlap: `175`

Embeddings use `sentence-transformers/all-MiniLM-L6-v2`.

Vector storage uses ChromaDB collections:

- `ai_ml_kb`
- `backend_kb`
- `data_science_kb`

Collections are created with cosine similarity metadata.

Run ingestion:

```powershell
cd backend
.\venv\Scripts\python.exe app\rag\ingestion.py
```

Current ingested collection counts:

```text
ai_ml_kb: 6307
backend_kb: 15
data_science_kb: 2878
```

## Retrieval and Reranking

Initial retrieval pulls candidate chunks from the selected role collection using semantic similarity.

Reranking is simple and explainable:

```text
final_score =
  semantic_similarity * 0.7
  + skill_overlap * 0.2
  + role_relevance * 0.1
```

Each retrieved chunk includes:

- source document
- semantic score
- skill overlap score
- role relevance score
- final score
- retrieval reason

The frontend displays this RAG evidence during the interview.

## Resume Parsing

Resume upload accepts PDF files. The backend uses PyMuPDF to extract text and lightweight section/keyword detection to return:

- skills
- frameworks
- technologies
- domains
- project technologies

The parsed summary is shown before role selection.

## Adaptive Interview Flow

The system maintains continuity per session:

- current question
- attempts for current question
- combined answers
- covered topics
- weak topics
- strong topics
- difficulty direction

The interviewer asks targeted follow-ups for 2-3 attempts. Once the answer is sufficient, it summarizes missing pieces and advances to the next RAG-generated question.

## Persistence

SQLAlchemy models store:

- interview sessions
- resume metadata
- extracted skills/domains/technologies
- generated questions
- answers
- retrieved chunks
- similarity/reranking scores
- evaluations
- final summaries

`DATABASE_URL` can point to PostgreSQL. If the placeholder URL is still present, local development falls back to SQLite so the project can run immediately.

## API Documentation

Base URL:

```text
http://127.0.0.1:8000
```

Endpoints:

```text
POST /api/interview/start
POST /api/interview/resume
POST /api/interview/role
POST /api/interview/question
POST /api/interview/retrieve
POST /api/interview/answer
POST /api/interview/evaluate
POST /api/interview/history
POST /api/interview/summary
POST /api/resume/upload
```

Question responses include:

```json
{
  "question": "...",
  "retrieval": {
    "query": "...",
    "chunks": [
      {
        "text": "...",
        "metadata": { "source": "...", "role": "ai_ml" },
        "semantic_score": 0.82,
        "skill_overlap": 0.25,
        "role_relevance": 1.0,
        "final_score": 0.73,
        "reason": "overlaps with resume skills; matches role focus"
      }
    ]
  }
}
```

## Setup

Start both backend and frontend:

```powershell
.\dev.ps1
```

Or manually:

```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
npm run dev
```

## Environment

Backend `.env`:

```text
DATABASE_URL=postgresql://username:password@localhost:5432/interview_db
GEMINI_API_KEY=your_gemini_api_key_here
CHROMADB_PATH=./knowledge_base
DEBUG=True
```

Use a real Gemini key for LLM-generated queries, questions, and evaluations. Without a real key, deterministic fallbacks still use retrieved RAG context for question generation.

## Verification

```powershell
.\backend\venv\Scripts\python.exe -m py_compile backend\app\main.py backend\app\services\interview_service.py backend\app\services\resume_service.py backend\app\rag\generation.py backend\app\rag\retrieval.py backend\app\rag\ingestion.py backend\app\api\interview.py backend\app\api\resume.py
npm --prefix frontend run build
```
