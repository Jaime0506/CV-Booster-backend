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
from sqlalchemy import select, desc, func, and_

import asyncio
import json
import os
from pathlib import Path
import uuid
from typing import Optional
from datetime import datetime, timedelta
from utils.auth_deps import get_current_user
from models.user import User
from models.llmUsage import LLMUsage

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
    options: Optional[str] = Form(None),  # prompt personalizado del usuario
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Paso B - Generador:
    - recibe: job_id (string) que referencia el extractor_json confirmado, y cv (pdf/md)
    - opcional: confirm_keywords (coma-separadas) si la UI permite editar
    - opcional: options (string) con instrucciones personalizadas del usuario
    - realiza: ofuscación, adaptador Nivel 1 con prompt personalizado, postprocess checks
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
        adapted_md = await asyncio.to_thread(adapt_cv_strict, obf_text, extractor_json, True, options)

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
            "obfuscation_mapping": mapping,
            "custom_instructions_used": options if options and options.strip() else None
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
    offset: int = 0,
    endpoint_filter: Optional[str] = None,
    model_filter: Optional[str] = None,
    include_full_result: bool = False
):
    """
    Obtiene el historial de uso de IA del usuario actual
    
    Args:
        limit: Número máximo de registros a devolver (default: 50, max: 100)
        offset: Número de registros a saltar para paginación (default: 0)
        endpoint_filter: Filtrar por endpoint específico (opcional)
        model_filter: Filtrar por modelo específico (opcional)
        include_full_result: Si incluir el resultado completo o solo preview (default: False)
    """
    # Validaciones
    if limit <= 0 or limit > 100:
        raise HTTPException(
            status_code=400, 
            detail="El límite debe estar entre 1 y 100"
        )
    
    if offset < 0:
        raise HTTPException(
            status_code=400, 
            detail="El offset debe ser mayor o igual a 0"
        )
    
    try:
        # Construir consulta base
        conditions = [LLMUsage.user_id == current_user.id]
        
        # Aplicar filtros opcionales
        if endpoint_filter:
            conditions.append(LLMUsage.endpoint.ilike(f"%{endpoint_filter}%"))
        
        if model_filter:
            conditions.append(LLMUsage.model.ilike(f"%{model_filter}%"))
        
        # Consulta principal
        stmt = (
            select(LLMUsage)
            .where(and_(*conditions))
            .order_by(desc(LLMUsage.created_at))
            .limit(limit)
            .offset(offset)
        )
        
        # Consulta para contar total de registros
        count_stmt = (
            select(func.count(LLMUsage.id))
            .where(and_(*conditions))
        )
        
        # Ejecutar consultas
        result = await db.execute(stmt)
        usage_records = result.scalars().all()
        
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar()
        
        # Convertir a formato JSON
        history = []
        for record in usage_records:
            # Determinar qué incluir del resultado
            if include_full_result:
                result_content = record.result
            else:
                result_content = (
                    record.result[:200] + "..." 
                    if record.result and len(record.result) > 200 
                    else record.result
                )
            
            history.append({
                "id": record.id,
                "request_id": str(record.request_id) if record.request_id else None,
                "model": record.model,
                "endpoint": record.endpoint,
                "latency_ms": record.latency_ms,
                "result": result_content,
                "result_length": len(record.result) if record.result else 0,
                "created_at": record.created_at.isoformat() if record.created_at else None
            })
        
        return JSONResponse({
            "success": True,
            "data": {
                "history": history,
                "pagination": {
                    "total_records": total_count,
                    "returned_records": len(history),
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + len(history)) < total_count
                },
                "filters_applied": {
                    "endpoint_filter": endpoint_filter,
                    "model_filter": model_filter,
                    "include_full_result": include_full_result
                }
            }
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error al consultar el historial: {str(e)}"
        )


@router.get("/usage_stats")
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = 30
):
    """
    Obtiene estadísticas de uso de IA del usuario actual
    
    Args:
        days: Número de días hacia atrás para calcular estadísticas (default: 30, max: 365)
    """
    # Validaciones
    if days <= 0 or days > 365:
        raise HTTPException(
            status_code=400, 
            detail="Los días deben estar entre 1 y 365"
        )
    
    try:
        # Fecha de inicio para el filtro
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Estadísticas generales
        general_stats_stmt = (
            select(
                func.count(LLMUsage.id).label('total_requests'),
                func.avg(LLMUsage.latency_ms).label('avg_latency'),
                func.min(LLMUsage.latency_ms).label('min_latency'),
                func.max(LLMUsage.latency_ms).label('max_latency'),
                func.sum(func.length(LLMUsage.result)).label('total_chars_generated')
            )
            .where(
                and_(
                    LLMUsage.user_id == current_user.id,
                    LLMUsage.created_at >= start_date
                )
            )
        )
        
        # Estadísticas por endpoint
        endpoint_stats_stmt = (
            select(
                LLMUsage.endpoint,
                func.count(LLMUsage.id).label('count'),
                func.avg(LLMUsage.latency_ms).label('avg_latency')
            )
            .where(
                and_(
                    LLMUsage.user_id == current_user.id,
                    LLMUsage.created_at >= start_date
                )
            )
            .group_by(LLMUsage.endpoint)
            .order_by(func.count(LLMUsage.id).desc())
        )
        
        # Estadísticas por modelo
        model_stats_stmt = (
            select(
                LLMUsage.model,
                func.count(LLMUsage.id).label('count'),
                func.avg(LLMUsage.latency_ms).label('avg_latency')
            )
            .where(
                and_(
                    LLMUsage.user_id == current_user.id,
                    LLMUsage.created_at >= start_date
                )
            )
            .group_by(LLMUsage.model)
            .order_by(func.count(LLMUsage.id).desc())
        )
        
        # Estadísticas por día (últimos 7 días)
        daily_stats_stmt = (
            select(
                func.date(LLMUsage.created_at).label('date'),
                func.count(LLMUsage.id).label('count'),
                func.avg(LLMUsage.latency_ms).label('avg_latency')
            )
            .where(
                and_(
                    LLMUsage.user_id == current_user.id,
                    LLMUsage.created_at >= datetime.utcnow() - timedelta(days=7)
                )
            )
            .group_by(func.date(LLMUsage.created_at))
            .order_by(func.date(LLMUsage.created_at).desc())
        )
        
        # Ejecutar consultas
        general_result = await db.execute(general_stats_stmt)
        general_stats = general_result.first()
        
        endpoint_result = await db.execute(endpoint_stats_stmt)
        endpoint_stats = endpoint_result.all()
        
        model_result = await db.execute(model_stats_stmt)
        model_stats = model_result.all()
        
        daily_result = await db.execute(daily_stats_stmt)
        daily_stats = daily_result.all()
        
        # Procesar resultados
        stats_data = {
            "period": {
                "days": days,
                "start_date": start_date.isoformat(),
                "end_date": datetime.utcnow().isoformat()
            },
            "general": {
                "total_requests": general_stats.total_requests or 0,
                "avg_latency_ms": round(general_stats.avg_latency, 2) if general_stats.avg_latency else 0,
                "min_latency_ms": general_stats.min_latency or 0,
                "max_latency_ms": general_stats.max_latency or 0,
                "total_chars_generated": general_stats.total_chars_generated or 0
            },
            "by_endpoint": [
                {
                    "endpoint": stat.endpoint,
                    "count": stat.count,
                    "avg_latency_ms": round(stat.avg_latency, 2) if stat.avg_latency else 0
                }
                for stat in endpoint_stats
            ],
            "by_model": [
                {
                    "model": stat.model,
                    "count": stat.count,
                    "avg_latency_ms": round(stat.avg_latency, 2) if stat.avg_latency else 0
                }
                for stat in model_stats
            ],
            "daily_usage": [
                {
                    "date": stat.date.isoformat() if stat.date else None,
                    "count": stat.count,
                    "avg_latency_ms": round(stat.avg_latency, 2) if stat.avg_latency else 0
                }
                for stat in daily_stats
            ]
        }
        
        return JSONResponse({
            "success": True,
            "data": stats_data
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error al consultar las estadísticas: {str(e)}"
        )


@router.get("/usage_record/{record_id}")
async def get_usage_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene un registro específico de uso de IA por ID
    
    Args:
        record_id: ID del registro a consultar
    """
    try:
        # Consultar el registro específico del usuario
        stmt = (
            select(LLMUsage)
            .where(
                and_(
                    LLMUsage.id == record_id,
                    LLMUsage.user_id == current_user.id
                )
            )
        )
        
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        
        if not record:
            raise HTTPException(
                status_code=404, 
                detail="Registro no encontrado o no tienes permisos para acceder a él"
            )
        
        # Convertir a formato JSON
        record_data = {
            "id": record.id,
            "request_id": str(record.request_id) if record.request_id else None,
            "model": record.model,
            "endpoint": record.endpoint,
            "latency_ms": record.latency_ms,
            "result": record.result,
            "result_length": len(record.result) if record.result else 0,
            "created_at": record.created_at.isoformat() if record.created_at else None
        }
        
        return JSONResponse({
            "success": True,
            "data": record_data
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error al consultar el registro: {str(e)}"
        )

# 1. Que el login rediriga a la primera
# 2. Que el registro rediriga a la segunda
# 3. Si codigo actua se registra y con los datos que se registro va y hace de una vez la eticion de login
# pero como no funciona correctamente pues no se logea (yo vi las peticiones http)
# 4. El redireccionamiento, si intento ir a login estando logeado, funciona, pero cuando intento ir a register ahi si me deja ahi xd