"""
main.py  –  Application entry point (Section 11 of the guide).

Creates the FastAPI app, attaches CORS middleware, and includes every
router module with its API prefix and docs tag.

Run locally:  uvicorn app.main:app --reload
Docs page:    http://localhost:8000/docs
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import (
    auth,
    events,
    sessions,
    points,
    database_routes,
    reports,
    feedback,
    access,
    dashboard,
    courses,
    workshops,
    certificates,
)

from app.database import Base, engine
import app.models  # Ensures all models are registered

# Automatically create all database tables if they do not exist
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Notice: Database tables could not be initialized on import: {e}")

app = FastAPI(title="AICHE Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files directory for generated certificates & templates
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ── Auth & Dashboard ────────────────────────────────────────────────────────
app.include_router(auth.router,              prefix="/api/auth",               tags=["Auth"])
app.include_router(dashboard.router,         prefix="/api/dashboard",          tags=["Dashboard"])

# ── Operations & Community ──────────────────────────────────────────────────
app.include_router(events.router,            prefix="/api/events",             tags=["Events"])
app.include_router(sessions.router,          prefix="/api/sessions",           tags=["Sessions"])
app.include_router(points.router,            prefix="/api/points",             tags=["Points"])
app.include_router(database_routes.router,   prefix="/api/committees",         tags=["Database"])
app.include_router(reports.router,           prefix="/api/reports",            tags=["Reports"])
app.include_router(feedback.router,          prefix="/api/feedback",           tags=["Feedback"])
app.include_router(access.router,            prefix="/api/access-permissions", tags=["Access"])

# ── Learning Track (Courses, Workshops & Certificates) ──────────────────────
app.include_router(courses.router,           prefix="/api/courses",            tags=["Courses"])
app.include_router(workshops.router,         prefix="/api/workshops",          tags=["Workshops"])
app.include_router(certificates.router,      prefix="/api/certificates",       tags=["Certificates"])


@app.get("/")
def root():
    """Health-check endpoint — confirms the server is running."""
    return {"status": "AICHE backend is running"}
