import os
import sys


def in_test_environment() -> bool:
    return (
        "pytest" in sys.argv[0]
        or "vscode" in sys.argv[0]
        or os.environ.get("SENTRY_IN_TEST_ENVIRONMENT") in {"1", "true"}
        or "PYTEST_XDIST_WORKER" in os.environ
    )
