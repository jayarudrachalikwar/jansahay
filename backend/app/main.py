import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.admin import router as admin_router
from app.api.routes.admin_schemes import router as admin_schemes_router
from app.api.routes.applications import applications_router, scheme_application_router
from app.api.routes.auth import router as auth_router
from app.api.routes.assistant import router as assistant_router
from app.api.routes.farmers import router as farmers_router
from app.api.routes.health import router as health_router
from app.api.routes.profile import router as profile_router
from app.api.routes.rag import router as rag_router
from app.api.routes.recommendations import router as recommendations_router
from app.api.routes.saved_schemes import router as saved_schemes_router
from app.api.routes.schemes import router as schemes_router
from app.api.routes.voice import router as voice_router

app = FastAPI(
    title="JanSahay AI",
    description="AI-powered government welfare scheme discovery platform",
    version="0.1.0",
)

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(profile_router, prefix="/api")
app.include_router(schemes_router, prefix="/api")
app.include_router(scheme_application_router, prefix="/api")
app.include_router(saved_schemes_router, prefix="/api")
app.include_router(recommendations_router, prefix="/api")
app.include_router(applications_router, prefix="/api")
app.include_router(assistant_router, prefix="/api")
app.include_router(voice_router, prefix="/api")
app.include_router(rag_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(admin_schemes_router, prefix="/api")
app.include_router(farmers_router, prefix="/api")
