from typing import Any, Dict, Optional, List
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

class NavioraError(Exception):
    """Base exception for all Naviora AI application errors."""
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class ClinicalDataError(NavioraError):
    """Raised when there is an issue with medical or patient data integrity."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CLINICAL_DATA_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )

class AIInferenceError(NavioraError):
    """Raised when the AI model layer fails or returns invalid results."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AI_INFERENCE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )

class UnauthorizedAccessError(NavioraError):
    """Raised for RBAC or credential violations."""
    def __init__(self, message: str = "Unauthorized access"):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

# --- Global Exception Handlers ---

async def naviora_error_handler(request: Request, exc: NavioraError):
    """Handler for custom application errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "code": exc.code,
                "request_id": getattr(request.state, "request_id", "unknown"),
                "details": exc.details
            }
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler for Pydantic validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "message": "Data validation failed",
                "code": "VALIDATION_ERROR",
                "request_id": getattr(request.state, "request_id", "unknown"),
                "details": exc.errors()
            }
        }
    )

async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handler for Database errors (prevents leaking table details)."""
    logger.error(f"Database Error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "A database error occurred. Please try again later.",
                "code": "DATABASE_ERROR",
                "request_id": getattr(request.state, "request_id", "unknown")
            }
        }
    )
