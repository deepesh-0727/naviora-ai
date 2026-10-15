"""Read-only 10-user liveness smoke check; see docs/load-testing.md."""

from locust import HttpUser, between, events, task
from health_smoke_metrics import error_rate


class HealthSmokeUser(HttpUser):
    wait_time = between(0.05, 0.15)

    @task
    def check_liveness(self) -> None:
        with self.client.get("/health", name="GET /health", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"/health returned HTTP {response.status_code}")
                return
            try:
                body = response.json()
            except ValueError:
                response.failure("/health response was not valid JSON")
                return
            if body != {"status": "ok"}:
                response.failure("/health response body did not match the liveness contract")


@events.quitting.add_listener
def require_smoke_error_rate_below_one_percent(environment, **_kwargs) -> None:
    stats = environment.stats.total
    rate = error_rate(stats.num_requests, stats.num_failures)
    print(
        f"Health smoke results: successes={stats.num_requests}, failures={stats.num_failures}, "
        f"error_rate={rate:.2%}"
    )
    if stats.num_requests + stats.num_failures == 0 or rate >= 0.01:
        environment.process_exit_code = 1
