"""Pure helpers for evaluating the health smoke run."""


def error_rate(successes: int, failures: int) -> float:
    total = successes + failures
    return failures / total if total else 1.0
