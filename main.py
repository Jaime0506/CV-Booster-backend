# main.py
import asyncio
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from utils.extractor import extract_text_from_upload
from services.ai_client import generate_cv_markdown

# Routers
from routers.cv_boost.cv import router as cv_boost_router

app = FastAPI(title="CV ATS optimizer")
app.include_router(cv_boost_router)

@app.get("/")
async def root():
    return {"message": "CV ATS optimizer"}