"""Application-level Prometheus metrics for healthcare workflows."""

import hmac
import ipaddress

from prometheus_client import Counter, Gauge, Histogram

WS_ACTIVE_CONNECTIONS = Gauge(
    "naviora_ws_active_connections",
    "Active WebSocket connections served by this backend process.",
)
VOICE_REQUESTS_TOTAL = Counter(
    "naviora_voice_requests_total",
    "Voice and speech requests received by the backend.",
)
EMERGENCY_TRIGGERS_TOTAL = Counter(
    "naviora_emergency_triggers_total",
    "Emergency SOS requests successfully recorded.",
)
QUEUE_POSITION_LATENCY_SECONDS = Histogram(
    "naviora_queue_position_latency_seconds",
    "Time spent retrieving and calculating queue positions.",
)


def metrics_access_allowed(environment: str, metrics_token: str, client_host: str | None, supplied_token: str | None) -> bool:
    """Allow development scraping; in production require loopback or the shared token."""
    if environment.lower() != "prod":
        return True

    try:
        is_loopback = client_host is not None and ipaddress.ip_address(client_host).is_loopback
    except ValueError:
        is_loopback = False

    if is_loopback:
        return True
    return bool(metrics_token and supplied_token and hmac.compare_digest(metrics_token, supplied_token))
