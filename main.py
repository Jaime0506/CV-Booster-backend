# main.py
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers
from routers.cv_boost.cv import router as cv_boost_router
from routers.auth.auth import router as auth_router

app = FastAPI(title="CV Booster")
# chame es gay
# Ajusta estos valores a tu entorno (dominios del frontend)
origins = [
    "https://cv-booster-omega.vercel.app",
    "http://localhost:3000",  # para desarrollo
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # o ["*"] para pruebas
    allow_credentials=True,
    allow_methods=["*"],          # permite OPTIONS, POST, GET, etc.
    allow_headers=["*"],          # o lista concreta: ["Authorization", "Content-Type"]
    expose_headers=["*"],
)

# registrar routers después de middleware
app.include_router(cv_boost_router)
app.include_router(auth_router)

@app.get("/")
async def root():
    return {"message": "CV ATS optimizer"}