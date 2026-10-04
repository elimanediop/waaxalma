import subprocess
import sys
from pathlib import Path
import pytest

from app.core.runtime_support import require_supported_python


@pytest.mark.parametrize("version", [(3, 10, 0), (3, 11, 9), (3, 13, 0), (3, 14, 0), (4, 0, 0)])
def test_unsupported_minors_fail_explicitly(version):
    with pytest.raises(RuntimeError, match="Python 3.12"):
        require_supported_python(version)


@pytest.mark.parametrize("version", [(3, 12, 0), (3, 12, 2), (3, 12, 14)])
def test_supported_minor_is_accepted(version):
    require_supported_python(version)


def test_cli_checks_runtime_before_loading_server(monkeypatch):
    import app.cli as cli
    import app.core.runtime_support as runtime
    def rejected():
        raise RuntimeError("unsupported runtime")
    monkeypatch.setattr(runtime, "require_supported_python", rejected)
    with pytest.raises(RuntimeError, match="unsupported runtime"):
        cli.main()


def test_declared_runtime_profile_is_consistent():
    root = Path(__file__).resolve().parents[3]
    subprocess.run([sys.executable, str(root / "ci/runtime_checks.py")], check=True, timeout=10)
