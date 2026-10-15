import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse
from fastapi import Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.metrics import metrics_access_allowed
from app.core.logging import setup_logging
from app.core.middleware import EnterpriseMiddleware
from app.core.exceptions import (
    NavioraError,
    naviora_error_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
)
from app.api.v1.router import api_router
from app.api.v1.endpoints.health import router as health_router
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.user import User
from app.core.monitoring import PrometheusMetricsMiddleware
from app.core.sentry import init_sentry
from app.middleware.audit import AuditMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.core.logging import user_id_context
from app.core.rate_limiter import limiter
from app.services.ws_manager import ws_manager

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
app.state.rbac_session_factory = SessionLocal
app.state.audit_session_factory = SessionLocal
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


async def redis_unavailable_handler(request: Request, exc: RedisError) -> JSONResponse:
    logger.exception("Redis request dependency failed", exc_info=exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Redis-backed service is unavailable."},
    )


app.add_exception_handler(RedisError, redis_unavailable_handler)


@app.middleware("http")
async def protect_metrics_endpoint(request: Request, call_next):
    if request.url.path == "/metrics" and not metrics_access_allowed(
        settings.ENVIRONMENT,
        settings.METRICS_TOKEN,
        request.client.host if request.client else None,
        request.headers.get("X-Metrics-Token"),
    ):
        return JSONResponse(status_code=403, content={"detail": "Metrics access denied."})
    return await call_next(request)

PUBLIC_API_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/otp/generate",
    "/api/v1/auth/otp/verify",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/departments",
    "/api/v1/navigation/departments",
}
PUBLIC_API_PREFIXES = (
    "/api/v1/departments/",
    "/api/v1/navigation/departments/",
)
STAFF_ROLES = {"doctor", "nurse", "front_desk", "pharmacy", "facilities", "emergency", "staff"}
ADMIN_ROLES = {"admin", "super_admin"}


@app.middleware("http")
async def enforce_api_identity_and_role_boundaries(request: Request, call_next):
    """Require an access token on API routes and enforce staff/admin namespaces."""
    path = request.url.path.rstrip("/") or "/"
    if (
        not path.startswith("/api/v1/")
        or path in PUBLIC_API_PATHS
        or path.startswith(PUBLIC_API_PREFIXES)
        or path == "/api/v1/health"
        or request.method == "OPTIONS"
    ):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return JSONResponse(status_code=401, content={"detail": "Authentication required."})

    try:
        claims = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        return JSONResponse(status_code=401, content={"detail": "Invalid or expired access token."})

    role = claims.get("role")
    subject = claims.get("sub")
    if claims.get("type") != "access" or not isinstance(role, str) or not subject:
        return JSONResponse(status_code=401, content={"detail": "Access token role is missing."})

    try:
        async with request.app.state.rbac_session_factory() as db:
            result = await db.execute(select(User).where(User.id == int(subject)))
            user = result.scalar_one_or_none()
    except (ValueError, TypeError):
        return JSONResponse(status_code=401, content={"detail": "Invalid access token subject."})
    except Exception:
        logger.exception("Unable to verify API account status")
        return JSONResponse(status_code=503, content={"detail": "Authentication service unavailable."})

    if user is None or not user.is_active:
        return JSONResponse(status_code=401, content={"detail": "Account is unavailable."})
    if user.role != role:
        return JSONResponse(status_code=403, content={"detail": "Token role no longer matches the account."})

    request.state.auth_claims = claims
    user_id_context.set(str(subject))
    if path.startswith("/api/v1/admin") and role not in ADMIN_ROLES:
        return JSONResponse(status_code=403, content={"detail": "Administrator role required."})
    if path.startswith("/api/v1/staff") and role not in STAFF_ROLES | ADMIN_ROLES:
        return JSONResponse(status_code=403, content={"detail": "Staff role required."})

    return await call_next(request)

# =========================================================
# MIDDLEWARE STACK
# (Order matters: outermost → innermost)
# =========================================================
def get_cors_allowed_origins() -> list[str]:
    configured = settings.BACKEND_CORS_ORIGINS + settings.ALLOWED_ORIGINS
    return list(dict.fromkeys(configured)) or ["*"]


app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS or ["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(EnterpriseMiddleware)
app.add_middleware(PrometheusMetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time-MS"],
)
app.add_middleware(AuditMiddleware)
app.add_middleware(RequestIDMiddleware)

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
app.include_router(health_router)


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
                    <div style="color:#94A3B8;font-weight:bold;margin:20px 0;">API documentation and service health</div>
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
    await ws_manager.start()
    try:
        async with SessionLocal() as db:
            await init_db(db)
            logger.info("Clinical Database Connection Verified")
    except Exception as e:
        logger.warning(f"Database link deferred or unreachable: {e}")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Naviora AI | Safe Clinical Shutdown Initiated")
    await ws_manager.shutdown()
