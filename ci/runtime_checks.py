"""Keep runtime policy, packaging, Docker and CI matrix in agreement."""
import ast
import json
from pathlib import Path
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def assignment(path, name):
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"Missing {name} in {path.name}")


def main():
    matrix = json.loads((ROOT / "ci/runtime_matrix.json").read_text(encoding="utf-8"))
    assert f"{sys.version_info.major}.{sys.version_info.minor}" == matrix["python_minor"], "Use the supported Python minor"
    metadata = tomllib.loads((ROOT / "backend/pyproject.toml").read_text(encoding="utf-8"))
    assert metadata["project"]["requires-python"] == matrix["requires_python"]
    assert assignment(ROOT / "backend/app/core/runtime_support.py", "SUPPORTED_PYTHON_MINOR") == tuple(map(int, matrix["python_minor"].split(".")))
    assert assignment(ROOT / "backend/app/sessions/database_tools.py", "SESSION_SCHEMA_VERSION") == matrix["sqlite_schema_version"]
    assert matrix["backend_workers"] == 1 and matrix["container_os"] == "linux" and matrix["container_architecture"] == "amd64"
    cli = (ROOT / "backend/app/cli.py").read_text(encoding="utf-8")
    assert "workers=1" in cli and "require_supported_python()" in cli
    workflow = (ROOT / ".github/workflows/quality.yml").read_text(encoding="utf-8")
    assert set(re.findall(r"python-version:\s*'([^']+)'", workflow)) == {matrix["python_minor"]}
    assert set(re.findall(r"node-version:\s*'([^']+)'", workflow)) == {matrix["node_major"]}
    for job, key in (("backend-tests", "backend_ci_os"), ("ui-install", "ui_ci_os")):
        section = re.split(r"\n  [a-zA-Z][\w-]*:\n", workflow.split(f"\n  {job}:\n", 1)[1], maxsplit=1)[0]
        match = re.search(r"os:\s*\[([^\]]+)\]", section)
        assert match and [v.strip() for v in match.group(1).split(",")] == matrix[key], f"{job} matrix drift"
    for directory in ("backend", "streamlit"):
        docker = (ROOT / directory / "Dockerfile").read_text(encoding="utf-8")
        versions = re.findall(r"^FROM python:([0-9]+\.[0-9]+)\.[0-9]+-slim-bookworm@sha256:[0-9a-f]{64}", docker, flags=re.M)
        assert versions and set(versions) == {matrix["python_minor"]}, f"{directory} Docker runtime drift"
    print("Runtime policy, package, CI and Docker profile: OK")


if __name__ == "__main__":
    main()
