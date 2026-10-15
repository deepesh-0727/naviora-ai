# Monitoring and alerting

## Prometheus metrics

The FastAPI service exposes Prometheus text format at `GET /metrics`. In production, requests must come from loopback or include the shared `X-Metrics-Token` header. Set a unique `METRICS_TOKEN` in Render's environment and keep the same value in the collector's secret environment. Do not put it in this repository or in a dashboard URL. The app compares the token in constant time. Outside production the endpoint is open for local development.

The endpoint exports application and HTTP instrumentation, including:

- `naviora_ws_active_connections` — active WebSocket connections in this process.
- `naviora_voice_requests_total` — voice and speech requests.
- `naviora_emergency_triggers_total` — successfully recorded emergency triggers.
- `naviora_queue_position_latency_seconds` — queue position latency histogram.

These are process-local metrics. If the service runs multiple instances, Prometheus scrapes each instance independently; avoid treating a gauge from one instance as a fleet-wide value without aggregation.

### Grafana Cloud with Grafana Alloy

Create a Grafana Cloud Prometheus metrics endpoint and access policy, then run Grafana Alloy somewhere that can reach the Render service. Supply these values through the Alloy service's protected environment or secret manager:

- `GRAFANA_CLOUD_PROMETHEUS_URL` — the remote-write URL shown by Grafana Cloud.
- `GRAFANA_CLOUD_PROMETHEUS_USER` — the metrics instance username.
- `GRAFANA_CLOUD_API_TOKEN` — a write-scoped Grafana Cloud access token.
- `NAVIORA_METRICS_TOKEN` — the same secret configured as Render's `METRICS_TOKEN`.

Example Alloy configuration (replace the host if the service URL changes):

```alloy
prometheus.scrape "naviora" {
  targets = [{ "__address__" = "naviora-backend-s6je.onrender.com" }]
  scheme = "https"
  metrics_path = "/metrics"
  scrape_interval = "60s"
  http_headers = {
    "X-Metrics-Token" = [sys.env("NAVIORA_METRICS_TOKEN")]
  }
  forward_to = [prometheus.remote_write.grafana.receiver]
}

prometheus.remote_write "grafana" {
  endpoint {
    url = sys.env("GRAFANA_CLOUD_PROMETHEUS_URL")
    basic_auth {
      username = sys.env("GRAFANA_CLOUD_PROMETHEUS_USER")
      password = sys.env("GRAFANA_CLOUD_API_TOKEN")
    }
  }
}
```

Confirm Alloy reports the scrape target healthy and that `up{job="prometheus.scrape.naviora"}` is `1` in Grafana Explore. Search for `naviora_voice_requests_total` to confirm application metrics arrive. Grafana Alloy supports custom scrape headers and environment-backed secret values; see the [scrape component reference](https://grafana.com/docs/alloy/latest/reference/components/prometheus/prometheus.scrape/) and [environment access guidance](https://grafana.com/docs/alloy/latest/access_permissions/).

### Metric token behavior

`METRICS_TOKEN` is optional for local development. In production, the middleware allows `/metrics` only when the request is loopback or the supplied `X-Metrics-Token` matches the configured token. If production has no token configured, external scrapes receive `403`; configure the token in Render and the collector before enabling remote scraping. The `GET /health` liveness check does not expose dependency state and does not require this token.

## Sentry error tracking

Set `SENTRY_DSN` in Render to enable Sentry. With an empty DSN, startup logs `SENTRY_DSN not set — error tracking disabled`; the app does not claim that errors are being delivered. After configuring the DSN, an administrator can request `GET /debug/sentry` to generate an intentional test error. It returns `500` while sending the event. With Sentry disabled or uninitialized, it returns `503`. Do not use this endpoint for uptime checks or repeated load tests.

## Uptime monitoring

Configure UptimeRobot or Better Stack to make an HTTPS `GET` request to `/health` every 5 minutes. Treat only `200` with `{"status":"ok"}` as healthy. `/health` checks that the process responds; `/health/detailed` is public, rate-limited to 10 requests per minute per source IP, and reports uptime, application version, and real Postgres, Redis, and configured AI-provider reachability. Use `/ready` when you only need Postgres and Redis dependency readiness; it returns `503` when either dependency is unavailable. Keep the provider's alert destination and credentials in its dashboard, not in the repository. The scheduled GitHub workflow in `.github/workflows/uptime.yml` checks `/health` every 15 minutes, retries three times, and opens a deduplicated GitHub issue after three consecutive failed requests. This workflow is an additional check, not a substitute for an independent monitor.

References: [UptimeRobot HTTP monitors](https://uptimerobot.com/), [Better Stack uptime monitoring](https://betterstack.com/uptime).
