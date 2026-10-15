from tests.load.health_smoke_metrics import error_rate


def test_health_smoke_error_rate_calculation_and_empty_run():
    assert error_rate(199, 1) < 0.01
    assert error_rate(99, 1) == 0.01
    assert error_rate(0, 0) == 1.0
