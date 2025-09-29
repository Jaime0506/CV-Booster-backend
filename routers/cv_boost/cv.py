# cv.py (APIRouter) - flujo en 2 pasos
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse
from utils.extractor import extract_text_from_upload
from services.ai_client import analyze_job, adapt_cv_strict
from utils.safety import obfuscate_personal_data, postprocess_check
from config.settings import settings

import asyncio
import json
import os
from pathlib import Path
import uuid
from typing import Optional

router = APIRouter(prefix="/cv-boost", tags=["cv-boost"])

# Aseguramos carpeta de almacenamiento temporal
TMP_JOBS_DIR = Path(settings.STORAGE_DIR) / "tmp_jobs"
TMP_JOBS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/analyze_job", status_code=status.HTTP_201_CREATED)
async def analyze_job_endpoint(
    job_description: str = Form(...),
    keywords: Optional[str] = Form(None)
):
    """
    Paso A - Analizador:
    - recibe: job_description (string) y opcionalmente keywords (coma-separadas)
    - devuelve: extractor_json + job_id (uuid) guardado temporalmente para confirmación
    """
    if not job_description or not job_description.strip():
        raise HTTPException(status_code=400, detail="job_description requerido")

    # Llamada al extractor (prompt A)
    extractor_json = analyze_job(job_description)

    # Fusionar keywords manuales si vienen
    kw_list = [k.strip() for k in (keywords or "").split(",") if k.strip()]
    if isinstance(extractor_json, dict):
        existing_kw = extractor_json.get("keywords_ats") or []
        extractor_json["keywords_ats"] = list(dict.fromkeys(kw_list + existing_kw))

    # Guardar JSON en disco con job_id
    job_id = uuid.uuid4().hex
    save_path = TMP_JOBS_DIR / f"{job_id}.json"
    try:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump({
                "job_description": job_description,
                "extractor_json": extractor_json
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo guardar job: {e}")

    return JSONResponse({
        "job_id": job_id,
        "extractor_json": extractor_json,
        "message": "Analisis generado. Muestra esto al usuario y pídeles confirmar/editar keywords antes de generar el CV."
    })


@router.post("/generate_cv/strict", status_code=status.HTTP_200_OK)
async def generate_cv_endpoint(
    job_id: str = Form(...),
    cv: UploadFile = File(...),
    confirm_keywords: Optional[str] = Form(None),  # opcion: usuario pudo editar keywords en UI
):
    """
    Paso B - Generador:
    - recibe: job_id (string) que referencia el extractor_json confirmado, y cv (pdf/md)
    - opcional: confirm_keywords (coma-separadas) si la UI permite editar
    - realiza: ofuscación, adaptador Nivel 1, postprocess checks
    - devuelve: extractor_json (final), cv_markdown, postprocess_checks, obfuscation_mapping
    """
    # Recuperar el extractor_json guardado
    save_path = TMP_JOBS_DIR / f"{job_id}.json"
    if not save_path.exists():
        raise HTTPException(status_code=404, detail="job_id no encontrado o expirado")

    try:
        with open(save_path, "r", encoding="utf-8") as f:
            stored = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo job guardado: {e}")

    extractor_json = stored.get("extractor_json")
    # Si la UI editó keywords, reemplazamos
    if confirm_keywords:
        kw_list = [k.strip() for k in confirm_keywords.split(",") if k.strip()]
        if isinstance(extractor_json, dict):
            extractor_json["keywords_ats"] = kw_list

    # Extraer texto del CV
    original_text = await extract_text_from_upload(cv)
    if not original_text or len(original_text.strip()) == 0:
        raise HTTPException(status_code=400, detail="CV vacío o no se pudo extraer texto")

    # Ofuscar datos personales antes de mandar a LLM
    obf_text, mapping = obfuscate_personal_data(original_text)

    # Llamada al adaptador (en thread para no bloquear event-loop)
    adapted_md = await asyncio.to_thread(adapt_cv_strict, obf_text, extractor_json, True)

    # Post-process: detectar nuevas líneas/métricas que no estaban en el original
    checks = postprocess_check(original_text, adapted_md)

    # (Opcional) podrías borrar el job guardado aquí o mantenerlo según política
    # os.remove(save_path)

    return JSONResponse({
        "extractor_json": extractor_json,
        "cv_markdown": adapted_md,
        "postprocess_checks": checks,
        "obfuscation_mapping": mapping
    })
