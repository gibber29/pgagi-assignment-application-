import chromadb
import os
import re
from typing import Dict, List

# Initialize ChromaDB client
client = chromadb.PersistentClient(path=os.getenv("CHROMADB_PATH", "./knowledge_base"))

_model = None


def _get_model():
    """
    Load the embedding model only when retrieval is needed.

    This keeps FastAPI startup and lightweight endpoints like /interview/start
    from failing when the model is not cached locally or the network is down.
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        try:
            _model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
        except TypeError:
            _model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as exc:
            raise RuntimeError(
                "Embedding model 'sentence-transformers/all-MiniLM-L6-v2' is not available "
                "locally. Download it once or run ingestion before starting the interview."
            ) from exc
    return _model


def _tokenize(values: List[str] | str) -> set:
    if isinstance(values, list):
        values = " ".join(values)
    return {token for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]+", values.lower()) if len(token) > 2}


def _skill_overlap(text: str, skills: List[str]) -> float:
    skill_tokens = _tokenize(skills)
    if not skill_tokens:
        return 0.0
    text_tokens = _tokenize(text)
    return len(skill_tokens & text_tokens) / len(skill_tokens)


def _role_relevance(text: str, role: str, metadata: Dict) -> float:
    role_key = role.lower().replace("_", " ")
    haystack = f"{text} {metadata}".lower()
    if role_key in haystack:
        return 1.0
    role_terms = _tokenize(role_key)
    if not role_terms:
        return 0.0
    text_terms = _tokenize(haystack)
    return len(role_terms & text_terms) / len(role_terms)


def _reason_for_chunk(chunk: Dict, skills: List[str], role: str) -> str:
    reasons = []
    if chunk["skill_overlap"] > 0:
        matched = sorted(_tokenize(skills) & _tokenize(chunk["text"]))
        reasons.append(f"overlaps with resume skills: {', '.join(matched[:4])}")
    if chunk["role_relevance"] > 0:
        reasons.append(f"matches the {role} retrieval focus")
    if chunk["semantic_score"] > 0:
        reasons.append("semantically similar to the generated query")
    return "; ".join(reasons) or "selected by semantic similarity"


def retrieve_context(query: str, role: str, top_k: int = 5, skills: List[str] | None = None) -> List[Dict]:
    """
    Retrieve relevant chunks from the role-specific knowledge base.
    """
    skills = skills or []
    collection_name = f"{role}_kb"
    try:
        collection = client.get_collection(collection_name)
    except Exception:
        raise Exception(f"Knowledge base for role '{role}' not found")

    query_embedding = _get_model().encode([query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=max(top_k * 3, top_k),
        include=["documents", "metadatas", "distances"],
    )

    chunks: List[Dict] = []
    docs = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for i, text in enumerate(docs):
        metadata = metadatas[i] if i < len(metadatas) else {}
        distance = distances[i] if i < len(distances) else 1
        semantic_score = max(0.0, 1 - float(distance))
        skill_score = _skill_overlap(text, skills)
        role_score = _role_relevance(text, role, metadata)
        final_score = semantic_score * 0.7 + skill_score * 0.2 + role_score * 0.1
        chunk = {
            "text": text,
            "metadata": metadata,
            "score": final_score,
            "semantic_score": semantic_score,
            "skill_overlap": skill_score,
            "role_relevance": role_score,
            "final_score": final_score,
        }
        chunk["reason"] = _reason_for_chunk(chunk, skills, role)
        chunks.append(
            chunk
        )

    return sorted(chunks, key=lambda item: item["final_score"], reverse=True)[:top_k]
