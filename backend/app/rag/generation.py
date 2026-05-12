import os
import json
import re
from typing import List, Dict

try:
    import google.generativeai as genai
except ImportError:
    genai = None

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
USE_GEMINI = (
    genai is not None
    and bool(GEMINI_API_KEY)
    and GEMINI_API_KEY != "your_gemini_api_key_here"
)

if USE_GEMINI:
    genai.configure(api_key=GEMINI_API_KEY)
    # Using the latest available model based on user configuration
    model = genai.GenerativeModel("gemini-3-flash-preview")


def _call_gemini(prompt: str) -> str:
    if not USE_GEMINI:
        raise RuntimeError("Gemini API is not configured or available. Please check your GEMINI_API_KEY.")

    response = model.generate_content(prompt)
    if hasattr(response, "text"):
        return response.text.strip()

    text = getattr(response, "result", None)
    if isinstance(text, str):
        return text.strip()
    if isinstance(text, dict):
        return json.dumps(text)

    return str(response).strip()


def generate_query(skills: List[str], role: str, history: List[str]) -> str:
    prompt = f"""
Based on the candidate's skills: {', '.join(skills) if skills else 'N/A'}
Role: {role}
Interview history: {history if history else 'None'}

Generate a concise semantic search query to retrieve relevant technical knowledge for interview questions.
Focus on advanced concepts for the selected role and the candidate's top skills.
"""
    return _call_gemini(prompt)


def generate_question_text(chunks: List[Dict], role: str) -> str:
    if not chunks:
        raise ValueError("Cannot generate a RAG question without retrieved context")

    context = "\n\n".join(chunk.get("text", "") for chunk in chunks[:4])
    prompt = f"""
Based on the following technical knowledge:
{context}

Generate a single grounded interview question for a {role} position.
The question must be DIRECTLY based on specific details, code patterns, or architectures mentioned in the context.
DO NOT mention the context, the source, or use phrases like "Based on the provided text" or "According to the context".
Just ask the question directly as an interviewer. Be specific—if the context mentions a specific technology or method, name it in the question.
Avoid generic "how would you apply this" questions; instead, ask about a specific trade-off, implementation detail, or edge case mentioned in the lines.
Keep it clear and appropriate for a technical interview.
"""
    return _call_gemini(prompt)


def evaluate_answer_text(answer: str) -> Dict:
    prompt = f"""
Evaluate this interview answer: "{answer}"

Classify as: weak, medium, or strong.
Provide concise feedback and a suggested difficulty adjustment: increase, maintain, or decrease.
Respond in valid JSON only.
"""

    raw = _call_gemini(prompt)
    parsed = json.loads(raw)
    return {
        "classification": parsed.get("classification", "medium"),
        "feedback": parsed.get("feedback", "Thank you for your response."),
        "adjustment": parsed.get("adjustment", "maintain"),
    }
