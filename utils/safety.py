# utils/safety.py
import re
from typing import Tuple, List

EMAIL_RE = re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")
PHONE_RE = re.compile(r"(\+?\d{7,15})")
# Para detectar porcentajes / números con % o "x%" o "xx %"
PERCENT_RE = re.compile(r"\b\d{1,3}\s?%")
NUMBER_RE = re.compile(r"\b\d{2,4}\b")  # años, cifras (simple heur)

def obfuscate_personal_data(text: str) -> Tuple[str, dict]:
    """
    Reemplaza emails y teléfonos por placeholders antes de enviar al LLM.
    Devuelve (text_ofuscado, mapping_originales)
    """
    mapping = {"emails": [], "phones": []}

    def _email_sub(m):
        mapping["emails"].append(m.group(0))
        return "[EMAIL_REDACTED]"

    def _phone_sub(m):
        mapping["phones"].append(m.group(0))
        return "[PHONE_REDACTED]"

    t = EMAIL_RE.sub(_email_sub, text)
    t = PHONE_RE.sub(_phone_sub, t)
    return t, mapping

def postprocess_check(original_text: str, generated_md: str) -> dict:
    """
    Heurística simple para detectar líneas nuevas y presencia de métricas / porcentajes que no existían.
    Devuelve dict con:
      - new_lines: lista de líneas en generated_md que no aparecen en original_text
      - suspicious_metrics: lista de fragmentos con % o números nuevos
    """
    orig_lines = {l.strip() for l in original_text.splitlines() if l.strip()}
    gen_lines = [l.strip() for l in generated_md.splitlines() if l.strip()]

    new_lines = [l for l in gen_lines if l not in orig_lines]
    # Filtrar las new_lines para mostrar solo las que parecen "afirmaciones" (no headers)
    new_lines_filtered = [l for l in new_lines if not l.startswith("#") and len(l) > 10]

    # Detect metrics in generated that are not in original
    orig_metrics = set(PERCENT_RE.findall(original_text) + NUMBER_RE.findall(original_text))
    gen_metrics = set(PERCENT_RE.findall(generated_md) + NUMBER_RE.findall(generated_md))
    suspicious_metrics = [m for m in gen_metrics if m not in orig_metrics]

    return {
        "new_lines": new_lines_filtered,
        "suspicious_metrics": suspicious_metrics
    }
