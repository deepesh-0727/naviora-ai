"""
Prometheus metrics middleware and endpoint for Naviora AI.

Uses the official `prometheus_client` library to export real
Prometheus-compatible metrics at /metrics for scraping by
Prometheus, Grafana, or Render's built-in monitoring.
"""
import time
import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Attempt to import prometheus_client; fall back to no-op counters if absent.
# ---------------------------------------------------------------------------
try:
    from prometheus_client import (
        Counter,
        Histogram,
        generate_latest,
        CONTENT_TYPE_LATEST,
        REGISTRY,
    )

    _HTTP_REQUESTS_TOTAL = Counter(
        "http_requests_total",
        "Total HTTP requests received",
        ["method", "endpoint", "status_code"],
    )

    _HTTP_REQUEST_DURATION_SECONDS = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "endpoint"],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )

    _HTTP_ERRORS_TOTAL = Counter(
        "http_errors_total",
        "Total HTTP 4xx/5xx error responses",
        ["method", "endpoint", "status_code"],
    )

    PROMETHEUS_AVAILABLE = True

except ImportError:  # pragma: no cover
    PROMETHEUS_AVAILABLE = False
    logger.warning(
        "prometheus_client not installed — metrics endpoint disabled. "
        "Add prometheus-client>=0.20.0 to requirements.txt."
    )

    # Lightweight no-op shims so the middleware still compiles.
    class _NoOpCounter:
        def labels(self, **_): return self
        def inc(self): pass

    class _NoOpHistogram:
        def labels(self, **_): return self
        def observe(self, _): pass

    _HTTP_REQUESTS_TOTAL = _NoOpCounter()          # type: ignore[assignment]
    _HTTP_REQUEST_DURATION_SECONDS = _NoOpHistogram()  # type: ignore[assignment]
    _HTTP_ERRORS_TOTAL = _NoOpCounter()            # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

# Paths excluded from metrics to reduce cardinality noise.
_EXCLUDED_PATHS = {"/metrics", "/api/v1/health", "/favicon.ico", "/docs", "/redoc", "/openapi.json"}


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """Record per-request Prometheus counters and latency histograms."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip excluded paths — avoids scrape loop cardinality explosion.
        if path in _EXCLUDED_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            _HTTP_ERRORS_TOTAL.labels(
                method=request.method, endpoint=path, status_code=500
            ).inc()
            raise exc
        finally:
            duration = time.perf_counter() - start
            status = response.status_code if response else 500

            _HTTP_REQUEST_DURATION_SECONDS.labels(
                method=request.method, endpoint=path
            ).observe(duration)

            _HTTP_REQUESTS_TOTAL.labels(
                method=request.method, endpoint=path, status_code=str(status)
            ).inc()

            if status >= 400:
                _HTTP_ERRORS_TOTAL.labels(
                    method=request.method, endpoint=path, status_code=str(status)
                ).inc()

            # Attach processing time header for debugging.
            if response:
                response.headers["X-Process-Time-Ms"] = f"{duration * 1000:.2f}"


# ---------------------------------------------------------------------------
# /metrics endpoint handler
# ---------------------------------------------------------------------------

async def metrics_endpoint(_request: Request) -> Response:
    """
    Expose Prometheus metrics for scraping.
    Mount this at /metrics in main.py:

        app.add_route("/metrics", metrics_endpoint)
    """
    if not PROMETHEUS_AVAILABLE:
        return Response(
            content="# prometheus_client not installed\n",
            media_type="text/plain",
            status_code=503,
        )

    data = generate_latest(REGISTRY)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------------------------
# Legacy in-process summary (still useful for the /admin/health endpoint)
# ---------------------------------------------------------------------------

def get_metrics_summary() -> dict:
    """Return a lightweight JSON-serialisable metrics snapshot."""
    if not PROMETHEUS_AVAILABLE:
        return {"prometheus_available": False}

    try:
        total_requests = int(
            sum(
                sample.value
                for metric in REGISTRY.collect()
                if metric.name == "http_requests_total"
                for sample in metric.samples
            )
        )
        total_errors = int(
            sum(
                sample.value
                for metric in REGISTRY.collect()
                if metric.name == "http_errors_total"
                for sample in metric.samples
            )
        )
    except Exception:
        total_requests = 0
        total_errors = 0

    return {
        "prometheus_available": True,
        "total_requests": total_requests,
        "total_errors": total_errors,
    }
