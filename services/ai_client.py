# services/ai_client.py
from openai import OpenAI
import os
from config import settings

# Inicializa cliente OpenAI apuntando al endpoint de OpenRouter
client = OpenAI(api_key=settings.settings.OPENROUTER_API_KEY, base_url=settings.settings.OPENROUTER_API_BASE)

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
