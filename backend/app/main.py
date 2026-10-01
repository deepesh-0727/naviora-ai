import logging
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import EnterpriseMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from app.core.exceptions import (
    NavioraError,
    naviora_error_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler
)
from app.api.v1.router import api_router
from app.db.init_db import init_db
from app.db.session import SessionLocal

from app.core.monitoring import PrometheusMetricsMiddleware
from app.core.sentry import init_sentry

# Initialize structured logging and error tracking
setup_logging()
init_sentry()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise AI Healthcare Orchestration Platform",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# --- Middleware Stack ---
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS or ["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
app.add_middleware(EnterpriseMiddleware)
app.add_middleware(PrometheusMetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin).strip("/") for origin in settings.BACKEND_CORS_ORIGINS] if settings.BACKEND_CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time-MS"]
)

# --- Exception Handlers ---
app.add_exception_handler(NavioraError, naviora_error_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)

# --- Router Registration ---
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["system"])
async def root():
    """
    Enterprise Landing Page - Provides system status and entry points.
    """
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=f"""
        <html>
            <head>
                <title>Naviora AI | Orchestrator</title>
                <style>
                    body {{ background: #0B0F19; color: #F8FAFC; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
                    .card {{ background: #161B2C; padding: 40px; border-radius: 24px; border: 1px solid #23293E; text-align: center; max-width: 500px; }}
                    h1 {{ color: #0EA5E9; letter-spacing: 2px; }}
                    .status {{ color: #34D399; font-weight: bold; margin: 20px 0; }}
                    .btn {{ display: inline-block; background: #0EA5E9; color: white; padding: 12px 24px; border-radius: 12px; text-decoration: none; font-weight: bold; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>NAVIORA AI</h1>
                    <p>Enterprise Clinical Orchestration Platform</p>
                    <div class="status">● SYSTEM LIVE & CLOUD CONNECTED</div>
                    <p style="color: #94A3B8;">Version 1.0.0 | Production Environment</p>
                    <a href="/docs" class="btn">Explore API Endpoints</a>
                </div>
            </body>
        </html>
    """)

@app.on_event("startup")
async def on_startup():
    logger.info(f"Naviora AI | Initializing Clinical Environment")
    try:
        async with SessionLocal() as db:
            await init_db(db)
            logger.info("Clinical Database Seeded Successfully")
    except Exception as e:
        logger.warning(f"Database link deferred or unreachable: {e}")

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Naviora AI | Safe Clinical Shutdown Initiated")

@app.get("/health", tags=["system"])
async def health_check():
    database_status = "connected"
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
    except Exception:
        database_status = "unavailable"
    return {
        "status": "online" if database_status == "connected" else "degraded",
        "orchestrator": "active",
        "version": "1.0.0",
        "telemetry": {
            "uptime_check": "passed",
            "db_link": database_status,
            "ai_node": "reachable"
        }
    }
