import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "filename": record.filename,
            "line_no": record.lineno,
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        # Include extra attributes if any
        if hasattr(record, "extra_attrs"):
            log_data.update(record.extra_attrs) # type: ignore
            
        return json.dumps(log_data)

def setup_logging() -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clean up default handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    handler = sys.stdout
    stream_handler = logging.StreamHandler(handler)
    stream_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(stream_handler)
    
    # Adjust third party logging levels
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
