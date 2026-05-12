from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from app.services.interview_service import (
    create_session,
    generate_summary,
    get_last_retrieval,
    get_next_message,
    get_session_history,
    upload_resume,
    set_role,
    evaluate_answer,
)
from app.services.resume_service import parse_resume

router = APIRouter()

class StartResponse(BaseModel):
    session_id: str
    message: str

class SessionRequest(BaseModel):
    session_id: str

class RoleRequest(BaseModel):
    session_id: str
    role: str

class AnswerRequest(BaseModel):
    session_id: str
    answer: str

@router.post("/start", response_model=StartResponse)
async def start_interview_endpoint():
    try:
        session = create_session()
        return {"session_id": session["id"], "message": "Interview session created."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/resume")
async def upload_resume_endpoint(
    session_id: str = Form(...),
    file: UploadFile = File(...),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        content = await file.read()
        parsed = parse_resume(content)
        upload_resume(session_id, parsed)
        return {"parsed_resume": parsed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing resume: {str(e)}")

@router.post("/role")
async def select_role(request: RoleRequest):
    try:
        set_role(request.session_id, request.role)
        return {"message": f"Role set to {request.role}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/question")
async def get_question(request: SessionRequest):
    try:
        question = get_next_message(request.session_id)
        retrieval = get_last_retrieval(request.session_id)
        return {"question": question, "retrieval": retrieval}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/answer")
async def submit_answer(request: AnswerRequest):
    try:
        evaluation = evaluate_answer(request.session_id, request.answer)
        return evaluation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate")
async def evaluate(request: AnswerRequest):
    try:
        return evaluate_answer(request.session_id, request.answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieve")
async def retrieve_last_context(request: SessionRequest):
    try:
        return get_last_retrieval(request.session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/history")
async def history(request: SessionRequest):
    try:
        return get_session_history(request.session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summary")
async def summary(request: SessionRequest):
    try:
        return generate_summary(request.session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
