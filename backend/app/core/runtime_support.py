"""Runtime boundary for the supported release profile."""
import sys

SUPPORTED_PYTHON_MINOR = (3, 12)


def require_supported_python(version=None) -> None:
    selected = sys.version_info if version is None else version
    if tuple(selected[:2]) != SUPPORTED_PYTHON_MINOR:
        raise RuntimeError("Waaxalma requires Python 3.12; use a supported environment or the container image.")
