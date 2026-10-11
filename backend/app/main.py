"""
SmartHire AI — FastAPI application entry point.

Start the server:
    python -m uvicorn app.main:app --reload

Swagger UI:  http://127.0.0.1:8000/docs
ReDoc:       http://127.0.0.1:8000/redoc
"""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.utils.logger import logger, setup_logging
from app.database.connection import engine
from app.database.init_db import init_db


# ── Lifespan (startup / shutdown) ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once on startup (before yielding) and once on shutdown (after yielding).
    """
    # Startup
    setup_logging(debug=settings.DEBUG)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # Create all DB tables if they don't exist yet
    # Wrapped in try/except so a DB issue doesn't prevent the server from starting
    try:
        init_db()
    except Exception as e:
        logger.warning(
            "DB init failed on startup (server will still start): {}. "
            "Check your DATABASE_URL in .env and ensure PostgreSQL is running.",
            e
        )

    # Pre-load ML ranking model on startup (non-critical)
    try:
        from app.ml.ranking_service import warmup_model
        warmup_model()
    except Exception as e:
        logger.warning("ML model warmup failed (non-critical): {}", e)

    # Pre-build RAG vector store on startup (non-critical)
    try:
        from app.rag.ingestion import warmup_rag
        warmup_rag()
    except Exception as e:
        logger.warning("RAG warmup failed (non-critical): {}", e)

    logger.info("Backend ready.")
    yield
    logger.info("Shutting down SmartHire AI backend.")
    engine.dispose()


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-Powered Recruitment & Candidate Intelligence Platform. "
        "Provides resume parsing, semantic job matching, ML candidate ranking, "
        "skill gap analysis, personalized learning roadmaps, and AI mock interviews."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every incoming request and its response time."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} ({duration_ms:.1f}ms)"
    )
    return response


# ── Global exception handlers ─────────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return a clean validation error — never expose internal stack traces."""
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Request validation failed",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all — log the full error server-side, return a safe message to client."""
    import traceback
    tb = traceback.format_exc()
    logger.error("Unhandled error on {}: {}\n{}", request.url.path, repr(exc), tb)
    # In DEBUG mode, return the actual error to help development
    if settings.DEBUG:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": repr(exc), "traceback": tb},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


# ── Routes ────────────────────────────────────────────────────────────────────

# Root health check
@app.get("/", tags=["Health"])
async def root():
    """Root health check endpoint."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check — verifies DB connectivity."""
    from sqlalchemy import text
    from app.database.connection import SessionLocal

    db_status = "ok"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        logger.error("Health check DB failure: {}", e)
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "version": settings.APP_VERSION,
    }


# ── Register API routers (added as phases are built) ─────────────────────────
# Phase 2 — Auth
from app.api.auth import router as auth_router
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])

# Phase 3 — Candidates & Resumes
from app.api.candidates import router as candidates_router
from app.api.resumes import router as resumes_router
app.include_router(candidates_router, prefix="/api/candidates", tags=["Candidates"])
app.include_router(resumes_router, prefix="/api/resumes", tags=["Resumes"])

# Phase 5 — Jobs & Recruiters
from app.api.jobs import router as jobs_router
from app.api.recruiters import router as recruiters_router
app.include_router(jobs_router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(recruiters_router, prefix="/api/recruiters", tags=["Recruiters"])

# Phase 6 — Matching & Skill Gap
from app.api.matching import router as matching_router
app.include_router(matching_router, prefix="/api/matching", tags=["Matching"])

# Phase 8 — Learning Roadmap
from app.api.roadmap import router as roadmap_router
app.include_router(roadmap_router, prefix="/api/roadmap", tags=["Roadmap"])

# Phase 9 — RAG Career Assistant
from app.api.assistant import router as assistant_router
app.include_router(assistant_router, prefix="/api/assistant", tags=["Assistant"])

# Phase 10 — AI Mock Interviews
from app.api.interviews import router as interviews_router
app.include_router(interviews_router, prefix="/api/interviews", tags=["Interviews"])

# Phase 11 — Analytics Dashboards
from app.api.analytics import router as analytics_router
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])

# Applications + Saved Jobs (supporting Phase 11 dashboard data)
from app.api.applications import router as applications_router
from app.api.saved_jobs import router as saved_jobs_router
app.include_router(applications_router, prefix="/api/applications", tags=["Applications"])
app.include_router(saved_jobs_router, prefix="/api/saved-jobs", tags=["Saved Jobs"])

# Phase 3 — Candidates / Resumes
# from app.api.candidates import router as candidates_router
# from app.api.resumes import router as resumes_router
# app.include_router(candidates_router, prefix="/api/candidates", tags=["Candidates"])
# app.include_router(resumes_router, prefix="/api/resumes", tags=["Resumes"])

# Phase 5 — Jobs
# from app.api.jobs import router as jobs_router
# app.include_router(jobs_router, prefix="/api/jobs", tags=["Jobs"])

# Phase 6 — Matching & Skill Gap
# from app.api.matching import router as matching_router
# app.include_router(matching_router, prefix="/api/matching", tags=["Matching"])

# Phase 8 — Roadmap
# from app.api.roadmap import router as roadmap_router
# app.include_router(roadmap_router, prefix="/api/roadmap", tags=["Roadmap"])

# Phase 9 — RAG Assistant
# from app.api.assistant import router as assistant_router
# app.include_router(assistant_router, prefix="/api/assistant", tags=["Assistant"])

# Phase 10 — Interviews
# from app.api.interviews import router as interviews_router
# app.include_router(interviews_router, prefix="/api/interviews", tags=["Interviews"])

# Phase 12 — Analytics
# from app.api.analytics import router as analytics_router
# app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])
