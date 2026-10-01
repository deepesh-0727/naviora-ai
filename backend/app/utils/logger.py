import logging
import sys
from typing import Any, Dict
from app.core.config import settings

def get_enterprise_logger(name: str):
    """
    Returns a structured logger that formats output for ELK/CloudWatch.
    Includes request context if available.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] [%(process)d] %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

class AuditLogger:
    """
    Dedicated logger for clinical and security events.
    Logs to a specific audit stream for compliance.
    """
    def __init__(self):
        self.logger = get_enterprise_logger("naviora.audit")

    def log_event(self, action: str, user_id: str, resource: str, status: str = "success", details: Dict[str, Any] = None):
        msg = f"AUDIT: action={action} user={user_id} resource={resource} status={status} details={details or {}}"
        self.logger.info(msg)

audit_logger = AuditLogger()
