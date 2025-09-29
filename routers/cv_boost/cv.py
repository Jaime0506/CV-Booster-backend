# cv.py (APIRouter) - flujo en 2 pasos
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from utils.extractor import extract_text_from_upload
from services.ai_client import analyze_job, adapt_cv_strict
from utils.safety import obfuscate_personal_data, postprocess_check
from utils.llm_tracker import create_tracker
from config.settings import settings
from config.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

import asyncio
import json
import os
from pathlib import Path
import uuid
from typing import Optional
from utils.auth_deps import get_current_user
from models.user import User

router = APIRouter(
    prefix="/cv-boost", 
    tags=["cv-boost"], 
    dependencies=[Depends(get_current_user)]
    )

# Aseguramos carpeta de almacenamiento temporal
TMP_JOBS_DIR = Path(settings.STORAGE_DIR) / "tmp_jobs"
TMP_JOBS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/analyze_job", status_code=status.HTTP_201_CREATED)
async def analyze_job_endpoint(
    job_description: str = Form(...),
    keywords: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Paso A - Analizador:
    - recibe: job_description (string) y opcionalmente keywords (coma-separadas)
    - devuelve: extractor_json + job_id (uuid) guardado temporalmente para confirmación
    """
    if not job_description or not job_description.strip():
        raise HTTPException(status_code=400, detail="job_description requerido")

    # Iniciar tracking de IA
    tracker = create_tracker()
    tracker.start_tracking()

    try:
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

        # Registrar uso de IA
        result_text = json.dumps(extractor_json, ensure_ascii=False, indent=2)
        await tracker.log_usage(
            db=db,
            user_id=str(current_user.id),
            model=settings.OPENROUTER_MODEL,
            endpoint="/cv-boost/analyze_job",
            result=result_text
        )

        return JSONResponse({
            "job_id": job_id,
            "extractor_json": extractor_json,
            "message": "Analisis generado. Muestra esto al usuario y pídeles confirmar/editar keywords antes de generar el CV."
        })
    
    except Exception as e:
        # Registrar error en el tracking
        await tracker.log_usage(
            db=db,
            user_id=str(current_user.id),
            model=settings.OPENROUTER_MODEL,
            endpoint="/cv-boost/analyze_job",
            result=f"ERROR: {str(e)}"
        )
        raise


@router.post("/generate_cv/strict", status_code=status.HTTP_200_OK)
async def generate_cv_endpoint(
    job_id: str = Form(...),
    cv: UploadFile = File(...),
    confirm_keywords: Optional[str] = Form(None),  # opcion: usuario pudo editar keywords en UI
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
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

    # Iniciar tracking de IA
    tracker = create_tracker()
    tracker.start_tracking()

    try:
        # Llamada al adaptador (en thread para no bloquear event-loop)
        adapted_md = await asyncio.to_thread(adapt_cv_strict, obf_text, extractor_json, True)

        # Post-process: detectar nuevas líneas/métricas que no estaban en el original
        checks = postprocess_check(original_text, adapted_md)

        # Registrar uso de IA
        await tracker.log_usage(
            db=db,
            user_id=str(current_user.id),
            model=settings.OPENROUTER_MODEL,
            endpoint="/cv-boost/generate_cv/strict",
            result=adapted_md
        )

        # (Opcional) podrías borrar el job guardado aquí o mantenerlo según política
        # os.remove(save_path)

        return JSONResponse({
            "extractor_json": extractor_json,
            "cv_markdown": adapted_md,
            "postprocess_checks": checks,
            "obfuscation_mapping": mapping
        })
    
    except Exception as e:
        # Registrar error en el tracking
        await tracker.log_usage(
            db=db,
            user_id=str(current_user.id),
            model=settings.OPENROUTER_MODEL,
            endpoint="/cv-boost/generate_cv/strict",
            result=f"ERROR: {str(e)}"
        )
        raise


@router.get("/usage_history")
async def get_usage_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """
    Obtiene el historial de uso de IA del usuario actual
    """
    from sqlalchemy import select, desc
    from models.llmUsage import LLMUsage
    
    # Consultar historial del usuario
    stmt = (
        select(LLMUsage)
        .where(LLMUsage.user_id == current_user.id)
        .order_by(desc(LLMUsage.created_at))
        .limit(limit)
        .offset(offset)
    )
    
    result = await db.execute(stmt)
    usage_records = result.scalars().all()
    
    # Convertir a formato JSON
    history = []
    for record in usage_records:
        history.append({
            "id": record.id,
            "request_id": str(record.request_id) if record.request_id else None,
            "model": record.model,
            "endpoint": record.endpoint,
            "latency_ms": record.latency_ms,
            "result_preview": record.result[:200] + "..." if record.result and len(record.result) > 200 else record.result,
            "created_at": record.created_at.isoformat() if record.created_at else None
        })
    
    return JSONResponse({
        "history": history,
        "total_returned": len(history),
        "limit": limit,
        "offset": offset
    })
