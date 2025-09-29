# services/ai_client.py
from openai import OpenAI
import os
from config import settings
import logging
import json

# Inicializa cliente OpenAI apuntando al endpoint de OpenRouter
client = OpenAI(api_key=settings.settings.OPENROUTER_API_KEY, base_url=settings.settings.OPENROUTER_API_BASE)

# Prompt A (Extractor) - devuelve JSON con estructura conocida
PROMPT_A_SYSTEM = """
Eres un analizador de ofertas de empleo. Extrae de manera precisa y estructurada (JSON) la información clave de la oferta:
- rol_detectado (string)
- seniority (one of: junior, mid, senior, lead, unknown)
- tecnologias (lista de objetos {name, confidence})
- skills_duras (lista de strings)
- skills_blandas (lista de strings)
- requisitos_imprescindibles (lista)
- requisitos_deseables (lista)
- keywords_ats (lista priorizada de palabras/short phrases)
- suggested_sections (lista de secciones sugeridas)
- confidence_score (float 0-1)

DEVUELVE SOLO JSON VÁLIDO. Si algo no se puede inferir, usa "unknown" o confidence baja.
"""

# Prompt B (Adaptador) - Nivel 1: estrictamente NO INVENTAR
PROMPT_B_SYSTEM = """
Eres un redactor experto en CVs optimizados para ATS. Genera SOLO la versión del CV en MARKDOWN.
Reglas (Nivel 1 — estrictas):
1) No inventes proyectos, logros, métricas, empresas, ni periodos. Si no aparece en el CV original, NO lo agregues.
2) Puedes reformular texto existente para mejorar claridad y convertir responsabilidades en logros solo si están justificadas en el texto original.
3) Integra las keywords de 'keywords_ats' de forma natural. Si una tecnología aparece en la oferta pero no en el CV original, NO la añadas como "usada"; en su lugar añade al final una sección opcional "[Formación sugerida para cerrar gaps]".
4) Si hay incertidumbre sobre una afirmación, añade [VERIFICAR] al lado.
5) Salida: SOLO markdown del CV. Nada más.
"""

def _call_chat(messages: list[dict[str,str]], temperature=0.0) -> str:
    """
    Llamada centralizada al cliente OpenAI/OpenRouter.
    """
    resp = client.chat.completions.create(
        model=settings.settings.OPENROUTER_MODEL,
        messages=messages,
        temperature=temperature,
    )

    # Extraemos el contenido del primer choice
    content = resp.choices[0].message.get("content") or resp.choices[0].message.get("text") or ""
    return content

def analyze_job(job_text: str) -> dict:
    """
    Llama al Prompt A y devuelve dict (parseado). Si falla el parseo, tratamos de 'sanear' respuesta.
    """
    messages = [
        {"role": "system", "content": PROMPT_A_SYSTEM},
        {"role": "user", "content": f"Aquí está la oferta:\n\n{job_text}"}
    ]
    raw = _call_chat(messages, temperature=0.0)
    # Intentar parsear JSON. El modelo debe devolver JSON puro según instrucción.
    try:
        parsed = json.loads(raw)
    except Exception:
        # Si no es JSON válido, intentamos extraer la primera ocurrencia de un bloque JSON
        import re
        m = re.search(r"(\{[\s\S]*\})", raw)
        if m:
            try:
                parsed = json.loads(m.group(1))
            except Exception as e:
                logging.exception("Failed to parse extractor JSON after regex.")
                parsed = {"error": "parse_error", "raw": raw}
        else:
            parsed = {"error": "parse_error", "raw": raw}
    return parsed

def adapt_cv_strict(cv_text: str, extractor_json: dict, obfuscated: bool = True) -> str:
    """
    Llama al Prompt B (Nivel 1). Devuelve markdown del CV.
    `obfuscated` indica si el cv_text ya vino ofuscado; si no, la función no lo hace aquí.
    """
    extract_json_str = json.dumps(extractor_json, ensure_ascii=False, indent=2)
    messages = [
        {"role": "system", "content": PROMPT_B_SYSTEM},
        {"role": "user", "content": f"CV_ORIGINAL:\n{cv_text}\n\nEXTRACTOR_JSON:\n{extract_json_str}"}
    ]
    md = _call_chat(messages, temperature=0.05)
    return md

def build_prompt(cv_text: str, job_text: str, keywords: list[str]) -> str:
    kw_line = ", ".join(keywords) if keywords else "Ninguna"
    prompt = f"""
Eres un asistente experto en optimizar CVs para sistemas ATS.
Recibirás: 1) CV (texto plano) 2) Oferta de trabajo (texto).
Objetivo: Generar un CV en MARKDOWN optimizado para la oferta, usando keywords relevantes.
Instrucciones:
- Mantén la veracidad: no inventes métricas o empresas.
- Usa secciones claras: Contacto, Perfil, Experiencia (logros cuantificados), Educación, Habilidades (bullets).
- Asegura que las palabras claves aparezcan de forma natural en experiencia y habilidades.
- Salida: SOLO el CV en formato Markdown.
CV_ORIGINAL:
{cv_text}

OFERTA:
{job_text}

KEYWORDS:
{kw_line}

Genera el CV optimizado en markdown.
"""
    return prompt

def generate_cv_markdown(cv_text: str, job_text: str, keywords: list[str]) -> str:
    prompt = build_prompt(cv_text, job_text, keywords)
    # Llamada al endpoint de chat completions compatible OpenAI (vía OpenRouter)
    completion = client.chat.completions.create(
        model=settings.settings.OPENROUTER_MODEL,  # AutoRouter selecciona un modelo adecuado
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.2
    )
    # el contenido suele estar en completion.choices[0].message.content
    return completion.choices[0].message.content
