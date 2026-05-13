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


def evaluate_answer_text(question: str, current_answer: str, previous_attempts: List[str] = None) -> Dict:
    history_text = "\n".join([f"Attempt {i+1}: {a}" for i, a in enumerate(previous_attempts)]) if previous_attempts else "None"
    
    prompt = f"""
    Context:
    Question asked: "{question}"
    Previous attempts (if any):
    {history_text}
    
    Current attempt to evaluate: "{current_answer}"

    Evaluate if the candidate has sufficiently answered the question based on all their attempts.
    
    Guidelines:
    1. "classification": Classify the cumulative answer as "weak", "medium", or "strong".
    2. "feedback": Provide specific, technical feedback. If they are missing something, explain exactly what concept is missing. If they are moving on, summarize what they did well and what they could have added.
    3. "advance": A boolean. Set to true if the candidate has given a "strong" answer OR if they have had 2+ attempts and further follow-up is unlikely to yield more depth.
    4. "topic": 2-3 word summary of the concept.
    5. "adjustment": "increase", "maintain", or "decrease" difficulty for the next question.

    Respond in valid JSON format:
    {{
        "classification": "...",
        "feedback": "...",
        "advance": true/false,
        "topic": "...",
        "adjustment": "..."
    }}
    """

    raw = _call_gemini(prompt)
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        raw = match.group(0)
    
    try:
        parsed = json.loads(raw)
        return {
            "classification": parsed.get("classification", "medium"),
            "feedback": parsed.get("feedback", "Thank you for your response."),
            "advance": bool(parsed.get("advance", False)),
            "topic": parsed.get("topic", "Technical Concept"),
            "adjustment": parsed.get("adjustment", "maintain"),
        }
    except Exception:
        return {
            "classification": "medium",
            "feedback": "Thank you for your response.",
            "advance": True,
            "topic": "Technical Concept",
            "adjustment": "maintain",
        }
