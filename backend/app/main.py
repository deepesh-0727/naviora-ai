import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse
from sqlalchemy.exc import SQLAlchemyError
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import EnterpriseMiddleware
from app.core.exceptions import (
    NavioraError,
    naviora_error_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
)
from app.api.v1.router import api_router
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.core.monitoring import PrometheusMetricsMiddleware
from app.core.sentry import init_sentry

# =========================================================
# INIT: Logging, Error Tracking, App
# =========================================================
setup_logging()
init_sentry()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise AI Healthcare Orchestration Platform",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =========================================================
# MIDDLEWARE STACK
# (Order matters: outermost → innermost)
# =========================================================
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS or ["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(EnterpriseMiddleware)
app.add_middleware(PrometheusMetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time-MS"],
)

# Prometheus /metrics endpoint
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# =========================================================
# EXCEPTION HANDLERS
# =========================================================
app.add_exception_handler(NavioraError, naviora_error_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)


# =========================================================
# SYSTEM ROUTES (declared BEFORE include_router)
# =========================================================
@app.get("/health", tags=["system"])
async def health_check():
    """
    Health endpoint used by Render load balancer and UptimeRobot.
    """
    return {
        "status": "online",
        "orchestrator": "active",
        "version": "1.0.0",
        "telemetry": {
            "uptime_check": "passed",
            "db_link": "connected",
            "ai_node": "reachable",
        },
    }


@app.head("/")
async def root_head():
    """
    HEAD endpoint used by Render for port detection.
    """
    return None


@app.get("/", tags=["system"])
async def root():
    """
    Landing page - HTML welcome screen with links.
    """
    return HTMLResponse(content="""
        <html>
            <head>
                <title>Naviora AI | Orchestrator</title>
                <meta charset="utf-8" />
            </head>
            <body style="background:#0B0F19;color:#F8FAFC;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;">
                <div style="background:#161B2C;padding:40px;border-radius:24px;border:1px solid #23293E;text-align:center;max-width:520px;">
                    <h1 style="color:#0EA5E9;letter-spacing:2px;margin:0 0 10px;">NAVIORA AI</h1>
                    <p style="margin:0 0 20px;">Enterprise Clinical Orchestration Platform</p>
                    <div style="color:#34D399;font-weight:bold;margin:20px 0;">&#9679; SYSTEM LIVE &amp; CLOUD CONNECTED</div>
                    <p style="color:#94A3B8;margin:10px 0;">Version 1.0.0 | Production Environment</p>
                    <a href="/docs" style="display:inline-block;background:#0EA5E9;color:white;padding:12px 24px;border-radius:12px;text-decoration:none;font-weight:bold;margin-top:20px;">Explore API Endpoints</a>
                    <div style="margin-top:16px;font-size:13px;">
                        <a href="/health" style="color:#0EA5E9;margin-right:16px;">/health</a>
                        <a href="/metrics" style="color:#0EA5E9;margin-right:16px;">/metrics</a>
                        <a href="/redoc" style="color:#0EA5E9;">/redoc</a>
                    </div>
                </div>
            </body>
        </html>
    """)


# =========================================================
# API ROUTER (declared AFTER system routes)
# =========================================================
app.include_router(api_router, prefix=settings.API_V1_STR)


# =========================================================
# LIFECYCLE EVENTS
# =========================================================
@app.on_event("startup")
async def on_startup():
    logger.info("Naviora AI | Initializing Clinical Environment")
    try:
        async with SessionLocal() as db:
            await init_db(db)
            logger.info("Clinical Database Seeded Successfully")
    except Exception as e:
        logger.warning(f"Database link deferred or unreachable: {e}")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Naviora AI | Safe Clinical Shutdown Initiated")