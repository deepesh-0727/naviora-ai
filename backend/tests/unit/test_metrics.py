from app.core.metrics import (
    EMERGENCY_TRIGGERS_TOTAL,
    QUEUE_POSITION_LATENCY_SECONDS,
    VOICE_REQUESTS_TOTAL,
    WS_ACTIVE_CONNECTIONS,
    metrics_access_allowed,
)


def test_custom_metrics_are_registered_and_mutable():
    before_voice = VOICE_REQUESTS_TOTAL._value.get()
    before_emergency = EMERGENCY_TRIGGERS_TOTAL._value.get()
    before_ws = WS_ACTIVE_CONNECTIONS._value.get()
    before_observations = QUEUE_POSITION_LATENCY_SECONDS._sum.get()

    VOICE_REQUESTS_TOTAL.inc()
    EMERGENCY_TRIGGERS_TOTAL.inc()
    WS_ACTIVE_CONNECTIONS.set(before_ws + 1)
    QUEUE_POSITION_LATENCY_SECONDS.observe(0.25)

    assert VOICE_REQUESTS_TOTAL._value.get() == before_voice + 1
    assert EMERGENCY_TRIGGERS_TOTAL._value.get() == before_emergency + 1
    assert WS_ACTIVE_CONNECTIONS._value.get() == before_ws + 1
    assert QUEUE_POSITION_LATENCY_SECONDS._sum.get() == before_observations + 0.25


def test_metrics_are_open_outside_production():
    assert metrics_access_allowed("dev", "", "203.0.113.10", None)


def test_production_metrics_require_loopback_or_shared_token():
    assert metrics_access_allowed("prod", "", "127.0.0.1", None)
    assert metrics_access_allowed("prod", "shared-secret", "203.0.113.10", "shared-secret")
    assert not metrics_access_allowed("prod", "shared-secret", "203.0.113.10", "wrong")
    assert not metrics_access_allowed("prod", "", "203.0.113.10", None)


def test_metrics_endpoint_exports_custom_metrics(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "# HELP naviora_voice_requests_total" in response.text
    assert "naviora_voice_requests_total" in response.text
    assert "naviora_emergency_triggers_total" in response.text
    assert "naviora_ws_active_connections" in response.text
    assert "naviora_queue_position_latency_seconds" in response.text
