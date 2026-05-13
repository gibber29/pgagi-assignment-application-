import uuid
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from app.db.session import get_db_session
from app.models.interview import InterviewAnswer, InterviewQuestion, InterviewSession, RetrievedChunk
from app.rag.retrieval import retrieve_context
from app.rag.generation import generate_query, generate_question_text, evaluate_answer_text

ROLE_COLLECTION_MAP = {
    "AI/ML Engineer": "ai_ml",
    "Backend Engineer": "backend",
    "Data Scientist": "data_science",
}

SESSIONS: Dict[str, Dict[str, Any]] = {}

ROLE_EXPECTATIONS = {
    "AI/ML Engineer": [
        ("problem framing", ["business", "objective", "requirement", "scope", "user"]),
        ("data quality and preparation", ["data", "preprocess", "clean", "label", "feature"]),
        ("model or architecture choice", ["model", "llm", "transformer", "algorithm", "rag", "embedding"]),
        ("evaluation metrics", ["metric", "accuracy", "precision", "recall", "latency", "satisfaction", "evaluate"]),
        ("deployment and monitoring", ["deploy", "scale", "monitor", "drift", "pipeline", "production"]),
        ("trade-offs and risks", ["trade", "risk", "cost", "privacy", "bias", "failure"]),
    ],
    "Backend Engineer": [
        ("requirements and API contract", ["requirement", "api", "contract", "endpoint", "schema"]),
        ("data model and persistence", ["database", "data", "schema", "index", "transaction"]),
        ("scalability and reliability", ["scale", "cache", "queue", "load", "reliability", "availability"]),
        ("error handling and observability", ["error", "log", "metric", "trace", "monitor"]),
        ("security", ["auth", "permission", "security", "validation", "rate"]),
    ],
    "Data Scientist": [
        ("problem framing", ["business", "objective", "hypothesis", "target", "scope"]),
        ("data exploration and cleaning", ["data", "eda", "missing", "outlier", "clean"]),
        ("modeling approach", ["model", "baseline", "feature", "algorithm", "train"]),
        ("evaluation", ["metric", "validate", "test", "precision", "recall", "error"]),
        ("communication and deployment", ["stakeholder", "explain", "deploy", "monitor", "decision"]),
    ],
}

def create_session() -> Dict[str, Any]:
    session_id = str(uuid.uuid4())
    session = {
        "id": session_id,
        "role": None,
        "resume": None,
        "status": "awaiting_resume",
        "history": [],
        "last_question": None,
        "current_attempts": 0,
        "current_answers": [],
        "current_expected_points": [],
        "question_number": 0,
        "last_question_id": None,
        "last_retrieval_query": None,
        "last_retrieved_chunks": [],
    }
    SESSIONS[session_id] = session
    with get_db_session() as db:
        db.add(InterviewSession(id=session_id, status=session["status"]))
        db.commit()
    return session


def get_session(session_id: str) -> Dict[str, Any]:
    session = SESSIONS.get(session_id)
    if not session:
        raise ValueError(f"Interview session {session_id} not found")
    return session


def upload_resume(session_id: str, resume_data: Dict[str, Any]) -> Dict[str, Any]:
    session = get_session(session_id)
    session["resume"] = resume_data
    session["status"] = "awaiting_role"
    session["history"].append({"role": "agent", "text": "Resume received and parsed."})
    with get_db_session() as db:
        db_session = db.get(InterviewSession, session_id)
        if db_session:
            db_session.resume = resume_data
            db_session.skills = resume_data.get("skills", [])
            db_session.domains = resume_data.get("domains", [])
            db_session.frameworks = resume_data.get("frameworks", [])
            db_session.technologies = resume_data.get("technologies", [])
            db_session.project_technologies = resume_data.get("project_technologies", [])
            db_session.status = session["status"]
            db.commit()
    return session


def set_role(session_id: str, role: str) -> Dict[str, Any]:
    session = get_session(session_id)
    if not session.get("resume"):
        raise ValueError("Resume must be uploaded before selecting a role.")
    session["role"] = role
    session["status"] = "ready"
    session["history"].append({"role": "user", "text": role})
    session["history"].append({"role": "agent", "text": f"Role set to {role}. Preparing your first question."})
    with get_db_session() as db:
        db_session = db.get(InterviewSession, session_id)
        if db_session:
            db_session.role = role
            db_session.status = session["status"]
            db.commit()
    return session


def get_next_message(session_id: str) -> str:
    session = get_session(session_id)
    status = session["status"]

    if status == "awaiting_resume":
        return "Please upload your resume to begin the interview."

    if status == "awaiting_role":
        return "Resume received. Please select your target role to continue."

    if status in {"ready", "interviewing"}:
        resume = session.get("resume", {})
        role = session.get("role")
        if not role:
            raise ValueError("Interview role has not been selected.")

        skills = sorted(set(resume.get("skills", []) + resume.get("technologies", []) + resume.get("project_technologies", [])))
        history = [item["text"] for item in session["history"] if item["role"] == "user"]
        query = generate_query(skills, role, history)
        difficulty = session.get("difficulty", "medium")
        if difficulty != "medium":
            query = f"{query}\nDifficulty focus: {difficulty}."
        collection_key = ROLE_COLLECTION_MAP.get(role, "backend")

        try:
            chunks = retrieve_context(query, collection_key, skills=skills)
        except Exception as exc:
            raise RuntimeError(
                f"RAG retrieval failed for role '{role}'. Make sure the knowledge base "
                f"contains a '{collection_key}_kb' collection and the embedding model is "
                f"available locally. Details: {exc}"
            ) from exc

        if not chunks:
            raise RuntimeError(f"RAG retrieval returned no context for role '{role}'.")

        question = generate_question_text(chunks, role)

        session["status"] = "interviewing"
        session["last_question"] = question
        session["last_retrieval_query"] = query
        session["last_retrieved_chunks"] = chunks
        session["current_attempts"] = 0
        session["current_answers"] = []
        session["current_expected_points"] = ROLE_EXPECTATIONS.get(role, ROLE_EXPECTATIONS["Backend Engineer"])
        session["question_number"] += 1
        session["history"].append({"role": "agent", "text": question})

        with get_db_session() as db:
            db_session = db.get(InterviewSession, session_id)
            if db_session:
                db_session.status = session["status"]
                db_session.current_attempts = 0
                db_session.current_answers = []
                db_session.current_expected_points = [
                    {"topic": label, "keywords": keywords}
                    for label, keywords in session["current_expected_points"]
                ]
                db_session.question_number = session["question_number"]
            question_row = InterviewQuestion(
                session_id=session_id,
                question=question,
                retrieval_query=query,
                role=role,
                difficulty=session.get("difficulty", "medium"),
            )
            db.add(question_row)
            db.flush()
            session["last_question_id"] = question_row.id
            for chunk in chunks:
                metadata = chunk.get("metadata", {})
                db.add(
                    RetrievedChunk(
                        question_id=question_row.id,
                        source=metadata.get("source"),
                        role=metadata.get("role"),
                        text=chunk.get("text", ""),
                        semantic_score=chunk.get("semantic_score", 0),
                        skill_overlap=chunk.get("skill_overlap", 0),
                        role_relevance=chunk.get("role_relevance", 0),
                        final_score=chunk.get("final_score", chunk.get("score", 0)),
                        reason=chunk.get("reason"),
                        metadata_json=metadata,
                    )
                )
            db.commit()
        return question

    raise ValueError(f"Unsupported session status: {status}")




def evaluate_answer(session_id: str, answer: str) -> Dict[str, Any]:
    session = get_session(session_id)
    session["history"].append({"role": "user", "text": answer})
    session["current_attempts"] = session.get("current_attempts", 0) + 1
    session.setdefault("current_answers", []).append(answer)

    role = session.get("role") or "Backend Engineer"
    expectations = session.get("current_expected_points") or ROLE_EXPECTATIONS.get(role, ROLE_EXPECTATIONS["Backend Engineer"])
    previous_attempts = session.get("current_answers", [])[:-1] # All except the current one

    try:
        evaluation = evaluate_answer_text(
            session.get("last_question", ""), 
            answer, 
            previous_attempts
        )
    except Exception as e:
        print(f"Evaluation error: {e}")
        evaluation = {
            "classification": "medium",
            "feedback": "Thank you for your answer. Let's move to the next question.",
            "advance": True,
            "topic": "Technical Concept",
            "adjustment": "maintain"
        }

    feedback = evaluation.get("feedback", "Thank you for your answer.")
    session["history"].append({"role": "agent", "text": feedback})

    if evaluation.get("classification") == "strong":
        session["difficulty"] = "increase depth"
    elif evaluation.get("classification") == "weak":
        session["difficulty"] = "slightly reduce complexity"
    else:
        session["difficulty"] = "maintain depth"

    # We use a simple keyword check just for the DB stats, but the LLM provides the real feedback
    covered = []
    missing = []
    for label, keywords in expectations:
        if any(k.lower() in answer.lower() for k in keywords):
            covered.append(label)
        else:
            missing.append(label)
    with get_db_session() as db:
        db_session = db.get(InterviewSession, session_id)
        if db_session:
            db_session.current_attempts = session["current_attempts"]
            db_session.current_answers = session.get("current_answers", [])
            db_session.difficulty = session["difficulty"]
            db_session.strong_topics = sorted(set((db_session.strong_topics or []) + covered))
            db_session.weak_topics = sorted(set((db_session.weak_topics or []) + missing))
            db_session.covered_topics = sorted(set((db_session.covered_topics or []) + covered))
        db.add(
            InterviewAnswer(
                session_id=session_id,
                question_id=session.get("last_question_id"),
                answer=answer,
                classification=evaluation.get("classification", "medium"),
                feedback=feedback,
                adjustment=evaluation.get("adjustment", "maintain"),
                attempt_number=session["current_attempts"],
            )
        )
        db.commit()

    if evaluation.get("advance"):
        evaluation["next_question"] = get_next_message(session_id)
        evaluation["next_retrieval"] = get_last_retrieval(session_id)

    return evaluation


def get_last_retrieval(session_id: str) -> Dict[str, Any]:
    session = get_session(session_id)
    return {
        "query": session.get("last_retrieval_query"),
        "chunks": session.get("last_retrieved_chunks", []),
    }


def get_session_history(session_id: str) -> Dict[str, Any]:
    session = get_session(session_id)
    with get_db_session() as db:
        db_session = db.get(InterviewSession, session_id)
        questions = (
            db.query(InterviewQuestion)
            .filter(InterviewQuestion.session_id == session_id)
            .order_by(InterviewQuestion.created_at)
            .all()
        )
        answers = (
            db.query(InterviewAnswer)
            .filter(InterviewAnswer.session_id == session_id)
            .order_by(InterviewAnswer.created_at)
            .all()
        )
        return {
            "session": {
                "id": session_id,
                "role": db_session.role if db_session else session.get("role"),
                "status": db_session.status if db_session else session.get("status"),
                "resume": db_session.resume if db_session else session.get("resume"),
                "covered_topics": db_session.covered_topics if db_session else [],
                "weak_topics": db_session.weak_topics if db_session else [],
                "strong_topics": db_session.strong_topics if db_session else [],
            },
            "questions": [
                {
                    "id": question.id,
                    "question": question.question,
                    "retrieval_query": question.retrieval_query,
                    "role": question.role,
                    "difficulty": question.difficulty,
                }
                for question in questions
            ],
            "answers": [
                {
                    "question_id": answer.question_id,
                    "answer": answer.answer,
                    "classification": answer.classification,
                    "feedback": answer.feedback,
                    "adjustment": answer.adjustment,
                    "attempt_number": answer.attempt_number,
                }
                for answer in answers
            ],
        }


def generate_summary(session_id: str) -> Dict[str, Any]:
    history = get_session_history(session_id)
    answers = history["answers"]
    classifications = [answer["classification"] for answer in answers]
    strong_count = classifications.count("strong")
    medium_count = classifications.count("medium")
    weak_count = classifications.count("weak")
    session_data = history["session"]
    weak_topics = session_data.get("weak_topics") or []
    strong_topics = session_data.get("strong_topics") or []

    if strong_count >= max(1, weak_count):
        verdict = "Recommended to continue to the next technical round."
    elif medium_count:
        verdict = "Shows promise, with targeted follow-up recommended."
    else:
        verdict = "Needs more technical depth before moving forward."

    summary = {
        "session_id": session_id,
        "role": session_data.get("role"),
        "questions_answered": len({answer["question_id"] for answer in answers if answer["question_id"]}),
        "strong_answers": strong_count,
        "medium_answers": medium_count,
        "weak_answers": weak_count,
        "strong_topics": strong_topics[:8],
        "improvement_topics": weak_topics[:8],
        "verdict": verdict,
        "summary": (
            f"Candidate completed a {session_data.get('role')} RAG interview with "
            f"{strong_count} strong, {medium_count} medium, and {weak_count} weak evaluated responses. "
            f"Strengths: {_summarize(strong_topics[:4], 'not enough evidence yet')}. "
            f"Improve: {_summarize(weak_topics[:4], 'continue adding concrete implementation detail')}."
        ),
    }
    with get_db_session() as db:
        db_session = db.get(InterviewSession, session_id)
        if db_session:
            db_session.summary = summary["summary"]
            db_session.status = "completed"
            db.commit()
    return summary
