# utils/extract.py
import os
import tempfile
from fastapi import UploadFile, HTTPException
from config.settings import settings
import pdfplumber

async def extract_text_from_upload(upload_file: UploadFile) -> str:
    filename = (upload_file.filename or "").lower()
    contents = await upload_file.read()  # bytes

    # size check
    if len(contents) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande")

    # PDF
    if filename.endswith(".pdf") or upload_file.content_type == "application/pdf":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tf:
            tf.write(contents)
            tmp_path = tf.name
        try:
            text_pages = []
            with pdfplumber.open(tmp_path) as pdf:
                for p in pdf.pages:
                    text_pages.append(p.extract_text() or "")
            return "\n".join(text_pages)
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    # Markdown / plain text
    if filename.endswith(".md") or filename.endswith(".markdown") or upload_file.content_type.startswith("text"):
        try:
            return contents.decode("utf-8")
        except Exception:
            return contents.decode("latin-1", errors="ignore")

    raise HTTPException(status_code=400, detail="Formato no soportado. Envía PDF o Markdown.")
