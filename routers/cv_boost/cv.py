from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from utils.extractor import extract_text_from_upload
from services.ai_client import generate_cv_markdown
import asyncio

router = APIRouter(prefix="/cv-boost", tags=["cv-boost"])

@router.post("/process_cv")
async def process_cv(
    cv: UploadFile = File(...),
    job_description: str = Form(...),
    keywords: str | None = Form(None)
):
    """
    Recibe: multipart:
     - cv: archivo PDF o Markdown
     - job_description: texto de la oferta
     - keywords: (opcional) lista separada por comas
    Retorna: JSON { "cv_markdown": "..." }
    """
    original_text = await extract_text_from_upload(cv)
    kw_list = [k.strip() for k in (keywords or "").split(",") if k.strip()]

    # Ejecutar la llamada al LLM en un hilo para no bloquear el event-loop
    new_md = await asyncio.to_thread(generate_cv_markdown, original_text, job_description, kw_list)

    return JSONResponse({"cv_markdown": new_md})
