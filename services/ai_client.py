# services/ai_client.py
import time
from openai import OpenAI
import os
from config.settings import settings
import logging
import json

# Inicializa cliente OpenAI apuntando al endpoint de OpenRouter
client = OpenAI(api_key=settings.OPENROUTER_API_KEY, base_url=settings.OPENROUTER_API_BASE)

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

# Prompt B (Adaptador) - Nivel 3: Adaptación ultra-agresiva e inteligente
# MEJORADO: Permite inferir y añadir tecnologías lógicamente consistentes
# sin inventar proyectos/empresas, maximizando la relevancia para la oferta específica
PROMPT_B_SYSTEM = """
Eres un redactor experto en CVs optimizados para ATS. Genera SOLO la versión del CV en MARKDOWN.

REGLAS FUNDAMENTALES (NO NEGOCIABLES):
1) NUNCA inventes proyectos, empresas, periodos de trabajo, o métricas específicas que no estén en el CV original.

ADAPTACIÓN INTELIGENTE Y AGRESIVA DE TECNOLOGÍAS (PERMITIDO Y RECOMENDADO):
2) INFERENCIA LÓGICA DE TECNOLOGÍAS: Puedes añadir tecnologías que no estén explícitamente mencionadas en el CV, SIEMPRE Y CUANDO:
   - Sea lógicamente consistente con el proyecto descrito
   - Sea una tecnología estándar/obvia para ese tipo de proyecto
   - Tenga sentido en el contexto de la oferta de trabajo
   
   EJEMPLOS DE INFERENCIA VÁLIDA:
   - Si el CV dice "Desarrollé una aplicación web" → puedes añadir "HTML, CSS, JavaScript" (tecnologías obvias)
   - Si el CV dice "Sistema de gestión de datos" → puedes añadir "SQL, bases de datos relacionales"
   - Si el CV dice "API REST" → puedes añadir "HTTP, JSON, endpoints"
   - Si el CV dice "Aplicación móvil" → puedes añadir "iOS/Android, frameworks móviles"
   - Si el CV dice "Machine Learning" → puedes añadir "Python, pandas, scikit-learn"
   - Si el CV dice "DevOps" → puedes añadir "CI/CD, Docker, automatización"

3) MAPEO Y ADAPTACIÓN DE TECNOLOGÍAS: Puedes adaptar y expandir las tecnologías mencionadas:
   - Si el CV menciona "JavaScript" y la oferta busca "React", puedes reformular como "JavaScript (incluyendo React, Node.js)"
   - Si el CV menciona "Python" y la oferta busca "Django", puedes reformular como "Python (Django, Flask, FastAPI)"
   - Si el CV menciona "Base de datos" y la oferta busca "PostgreSQL", puedes reformular como "Bases de datos (PostgreSQL, MySQL, MongoDB)"
   - Si el CV menciona "Cloud" y la oferta busca "AWS", puedes reformular como "Cloud computing (AWS, Azure, GCP)"

4) ADAPTACIÓN ULTRA-AGRESIVA DE EXPERIENCIA LABORAL: Puedes transformar completamente la experiencia laboral para que sea más atractiva y relevante:
   - CAMBIAR RESPONSABILIDADES: Adaptar las responsabilidades del cargo original para que se alineen con el puesto objetivo
   - HACER RESPONSABILIDADES MÁS ATRACTIVAS: Reformular responsabilidades básicas para que suenen más estratégicas y valiosas
   - AJUSTAR NIVEL DE SENIORITY: Adaptar el nivel de responsabilidad según el cargo al que se postula
   - CAMBIAR ENFOQUE TÉCNICO: Modificar el enfoque técnico de las responsabilidades para que coincida con la oferta
   
   EJEMPLOS DE TRANSFORMACIÓN DE EXPERIENCIA:
   - Si el CV dice "Desarrollador Junior" y la oferta busca "Senior Developer" → transformar a "Desarrollador con responsabilidades de liderazgo técnico"
   - Si el CV dice "Mantenimiento de código" y la oferta busca "Arquitectura" → transformar a "Diseño y arquitectura de soluciones"
   - Si el CV dice "Testing manual" y la oferta busca "QA Automation" → transformar a "Automatización de pruebas y CI/CD"
   - Si el CV dice "Soporte técnico" y la oferta busca "DevOps" → transformar a "Gestión de infraestructura y automatización"

5) REFORMULACIÓN ULTRA-ATRACTIVA DE RESPONSABILIDADES: Puedes hacer las responsabilidades mucho más atractivas y relevantes:
   - CONVERTIR TAREAS BÁSICAS EN LOGROS ESTRATÉGICOS:
     * "Escribir código" → "Desarrollar soluciones escalables y optimizadas"
     * "Corregir bugs" → "Optimizar rendimiento y mejorar la experiencia del usuario"
     * "Reuniones con clientes" → "Liderar consultoría técnica y definición de requerimientos"
     * "Documentar código" → "Establecer estándares de documentación y mejores prácticas"
   
   - ADAPTAR RESPONSABILIDADES AL CARGO OBJETIVO:
     * Si la oferta busca "Team Lead" → enfatizar liderazgo, mentoring, coordinación
     * Si la oferta busca "Full Stack" → destacar tanto frontend como backend
     * Si la oferta busca "DevOps" → enfatizar automatización, CI/CD, infraestructura
     * Si la oferta busca "Data Engineer" → destacar procesamiento, pipelines, optimización

6) REFORMULACIÓN DE PROYECTOS: Puedes adaptar la descripción de proyectos existentes para destacar aspectos relevantes para la oferta:
   - Cambiar el enfoque de un proyecto para destacar tecnologías relevantes
   - Reformular responsabilidades para que suenen más relevantes para el puesto
   - Añadir contexto sobre el impacto del proyecto si está implícito en el original
   - Expandir descripciones técnicas cuando sea lógicamente consistente

7) OPTIMIZACIÓN DE SECCIONES: Puedes reorganizar y optimizar secciones existentes:
   - Cambiar el orden de tecnologías para priorizar las relevantes para la oferta
   - Reformular descripciones de experiencia para destacar aspectos relevantes
   - Convertir responsabilidades en logros cuantificados cuando sea apropiado
   - Añadir tecnologías relacionadas que sean obvias para el contexto

8) INTEGRACIÓN DE KEYWORDS: Integra las keywords de 'keywords_ats' de forma natural en el contenido existente.

9) GAPS DE TECNOLOGÍA: Si hay tecnologías importantes en la oferta que no aparecen en el CV, añade al final una sección "[Formación sugerida para cerrar gaps]" con las tecnologías faltantes.

10) VERIFICACIÓN: Si hay incertidumbre sobre una afirmación, añade [VERIFICAR] al lado.

OBJETIVO: Crear un CV que maximice las coincidencias con la oferta sin inventar contenido, haciendo que el candidato parezca más relevante para el puesto específico.

Salida: SOLO markdown del CV. Nada más.
"""

def _call_chat(messages: list[dict[str,str]], max_tokens=1500, temperature=0.0) -> str:
    """
    Llamada central al cliente OpenAI/OpenRouter. Extrae el contenido de la respuesta
    de forma robusta para las distintas representaciones que la SDK puede devolver.
    Retorna: string con el texto del assistant (o string vacío en error).
    """
    # reintentos simples en caso de fallo transitorio
    for attempt in range(1, 3):
        try:
            resp = client.chat.completions.create(
                model=settings.OPENROUTER_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            break
        except Exception as e:
            error_msg = str(e)
            # Detectar errores específicos de modelo no encontrado
            if "404" in error_msg or "No endpoints found" in error_msg or "not found" in error_msg.lower():
                logging.error(
                    "Modelo no encontrado en OpenRouter: %s. "
                    "Verifica que el modelo esté disponible. "
                    "Modelos alternativos sugeridos: "
                    "x-ai/grok-beta, openai/gpt-3.5-turbo, google/gemini-flash-1.5, meta-llama/llama-3.2-3b-instruct:free",
                    settings.OPENROUTER_MODEL
                )
                raise ValueError(
                    f"Modelo '{settings.OPENROUTER_MODEL}' no está disponible en OpenRouter. "
                    f"Error: {error_msg}. "
                    f"Por favor, actualiza OPENROUTER_MODEL en tu archivo .env con un modelo válido. "
                    f"Modelos sugeridos: x-ai/grok-beta, openai/gpt-3.5-turbo, google/gemini-flash-1.5, "
                    f"meta-llama/llama-3.2-3b-instruct:free"
                ) from e
            logging.exception("Error llamando al LLM (intento %s): %s", attempt, e)
            if attempt < 2:
                time.sleep(0.8)
            else:
                raise

    # Ahora extraer contenido de forma robusta
    try:
        choice0 = resp.choices[0]
    except Exception:
        logging.error("Respuesta sin choices: %s", resp)
        return ""

    # 1) Forma esperada (objeto con .message y .content)
    try:
        # choice0.message puede ser un objeto con atributo content
        msg_obj = getattr(choice0, "message", None)
        if msg_obj is not None:
            # Algunos SDKs permiten acceder así:
            content = getattr(msg_obj, "content", None)
            if content:
                return content
            # en algunos casos msg_obj puede ser dict-like
            if isinstance(msg_obj, dict):
                cand = msg_obj.get("content") or msg_obj.get("text")
                if cand:
                    return cand
    except Exception:
        logging.debug("No se obtuvo content desde choice0.message (objeto).", exc_info=True)

    # 2) Forma alternativa: choice0.message.content (por si message es otro wrapper)
    try:
        if hasattr(choice0, "message") and hasattr(choice0.message, "content"):
            return choice0.message.content
    except Exception:
        pass

    # 3) Forma antigua: choice0.text
    try:
        text_attr = getattr(choice0, "text", None)
        if text_attr:
            return text_attr
    except Exception:
        pass

    # 4) Si es dict-like entero (por seguridad)
    try:
        if isinstance(resp, dict):
            # intentar obtener first choice -> message -> content
            c0 = resp.get("choices", [{}])[0]
            msg = c0.get("message", {})
            if isinstance(msg, dict):
                return msg.get("content") or msg.get("text") or ""
            return c0.get("text") or ""
    except Exception:
        pass

    # 5) Fallback: log completo y devolver str(resp)
    logging.error("No se pudo extraer contenido del LLM. Resp raw: %s", resp)
    try:
        return str(resp)
    except Exception:
        return ""

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

def _generate_technology_mapping_guidance(extractor_json: dict) -> str:
    """
    Genera guías específicas de mapeo de tecnologías basadas en el análisis de la oferta.
    """
    guidance = []
    
    # Extraer tecnologías de la oferta
    tecnologias = extractor_json.get('tecnologias', [])
    keywords_ats = extractor_json.get('keywords_ats', [])
    
    if tecnologias:
        guidance.append("TECNOLOGÍAS PRIORITARIAS EN LA OFERTA:")
        for tech in tecnologias[:5]:  # Top 5 tecnologías
            if isinstance(tech, dict):
                name = tech.get('name', '')
                confidence = tech.get('confidence', 0)
                if name and confidence > 0.3:
                    guidance.append(f"- {name} (relevancia: {confidence:.1f})")
            elif isinstance(tech, str):
                guidance.append(f"- {tech}")
    
    if keywords_ats:
        guidance.append("\nKEYWORDS ATS A INTEGRAR:")
        for keyword in keywords_ats[:10]:  # Top 10 keywords
            guidance.append(f"- {keyword}")
    
    # Sugerencias de mapeo e inferencia agresiva
    guidance.append("\nSUGERENCIAS DE MAPEO E INFERENCIA AGRESIVA:")
    guidance.append("- Si el CV menciona 'JavaScript' → enfatizar frameworks como React, Vue, Angular, Node.js")
    guidance.append("- Si el CV menciona 'Python' → destacar frameworks web, data science, automation, pandas, numpy")
    guidance.append("- Si el CV menciona 'Base de datos' → especificar PostgreSQL, MySQL, MongoDB, SQL")
    guidance.append("- Si el CV menciona 'Cloud' → especificar AWS, Azure, GCP, Docker, Kubernetes")
    guidance.append("- Si el CV menciona 'DevOps' → destacar CI/CD, Docker, Kubernetes, Jenkins, GitLab")
    guidance.append("- Si el CV menciona 'aplicación web' → inferir HTML, CSS, JavaScript, HTTP, APIs")
    guidance.append("- Si el CV menciona 'API' → inferir REST, JSON, HTTP, endpoints, microservicios")
    guidance.append("- Si el CV menciona 'móvil' → inferir iOS, Android, React Native, Flutter")
    guidance.append("- Si el CV menciona 'ML/AI' → inferir Python, pandas, scikit-learn, TensorFlow, PyTorch")
    guidance.append("- Si el CV menciona 'análisis de datos' → inferir SQL, Python, pandas, visualización")
    
    # Sugerencias específicas para transformación de experiencia laboral
    guidance.append("\nTRANSFORMACIÓN DE EXPERIENCIA LABORAL:")
    guidance.append("ADAPTACIÓN DE RESPONSABILIDADES:")
    guidance.append("- 'Desarrollador Junior' → 'Desarrollador con responsabilidades de liderazgo técnico'")
    guidance.append("- 'Mantenimiento de código' → 'Diseño y arquitectura de soluciones'")
    guidance.append("- 'Testing manual' → 'Automatización de pruebas y CI/CD'")
    guidance.append("- 'Soporte técnico' → 'Gestión de infraestructura y automatización'")
    guidance.append("- 'Escribir código' → 'Desarrollar soluciones escalables y optimizadas'")
    guidance.append("- 'Corregir bugs' → 'Optimizar rendimiento y mejorar experiencia del usuario'")
    guidance.append("- 'Reuniones con clientes' → 'Liderar consultoría técnica y definición de requerimientos'")
    guidance.append("- 'Documentar código' → 'Establecer estándares de documentación y mejores prácticas'")
    
    # Adaptación según el tipo de cargo objetivo
    rol_detectado = extractor_json.get('rol_detectado', '').lower()
    if 'lead' in rol_detectado or 'manager' in rol_detectado:
        guidance.append("\nADAPTACIÓN PARA LIDERAZGO:")
        guidance.append("- Enfatizar: liderazgo de equipo, mentoring, coordinación, toma de decisiones")
        guidance.append("- Transformar: 'Desarrollo individual' → 'Liderazgo de equipo de desarrollo'")
        guidance.append("- Añadir: 'Mentoring de desarrolladores junior', 'Coordinación de proyectos'")
    elif 'devops' in rol_detectado or 'sre' in rol_detectado:
        guidance.append("\nADAPTACIÓN PARA DEVOPS:")
        guidance.append("- Enfatizar: automatización, CI/CD, infraestructura, monitoreo")
        guidance.append("- Transformar: 'Despliegue manual' → 'Automatización de despliegues'")
        guidance.append("- Añadir: 'Gestión de infraestructura', 'Monitoreo y alertas'")
    elif 'full stack' in rol_detectado:
        guidance.append("\nADAPTACIÓN PARA FULL STACK:")
        guidance.append("- Enfatizar: frontend y backend, arquitectura completa")
        guidance.append("- Transformar: 'Desarrollo frontend' → 'Desarrollo full stack con arquitectura completa'")
        guidance.append("- Añadir: 'Integración frontend-backend', 'Arquitectura de microservicios'")
    
    return "\n".join(guidance)

def adapt_cv_strict(cv_text: str, extractor_json: dict, obfuscated: bool = True, custom_instructions: str = None) -> str:
    """
    Llama al Prompt B (Nivel 2). Devuelve markdown del CV.
    `obfuscated` indica si el cv_text ya vino ofuscado; si no, la función no lo hace aquí.
    `custom_instructions` son instrucciones adicionales del usuario que se combinan con el prompt base.
    """
    # Construir el prompt del sistema combinando el base con las instrucciones personalizadas
    system_prompt = PROMPT_B_SYSTEM
    if custom_instructions and custom_instructions.strip():
        system_prompt += f"\n\nINSTRUCCIONES PERSONALIZADAS DEL USUARIO:\n{custom_instructions.strip()}"
    
    # Añadir guías específicas de mapeo de tecnologías
    tech_guidance = _generate_technology_mapping_guidance(extractor_json)
    if tech_guidance:
        system_prompt += f"\n\nGUÍAS ESPECÍFICAS PARA ESTA OFERTA:\n{tech_guidance}"
    
    extract_json_str = json.dumps(extractor_json, ensure_ascii=False, indent=2)
    messages = [
        {"role": "system", "content": system_prompt},
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
        model=settings.OPENROUTER_MODEL,  # AutoRouter selecciona un modelo adecuado
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.2
    )
    # el contenido suele estar en completion.choices[0].message.content
    return completion.choices[0].message.content
