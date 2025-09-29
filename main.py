# main.py
import asyncio
from fastapi import FastAPI

# Routers
from routers.cv_boost.cv import router as cv_boost_router
from routers.auth.auth import router as auth_router

app = FastAPI(title="CV ATS optimizer")

app.include_router(cv_boost_router)
app.include_router(auth_router)

@app.get("/")
async def root():
    return {"message": "CV ATS optimizer"}