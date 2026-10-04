"""Syntax gates without importing applications or requiring provider credentials."""
import ast
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
count = 0
for directory in ("backend/app", "backend/scripts", "backend/tests", "streamlit", "ci"):
    for path in (root / directory).rglob("*.py"):
        if any(part.startswith(".") or part == "__pycache__" for part in path.relative_to(root).parts):
            continue
        ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        count += 1
for path in (root / "streamlit").rglob("*.js"):
    subprocess.run(["node", "--check", str(path)], check=True)
with tempfile.TemporaryDirectory() as directory:
    for path in (root / "streamlit").rglob("*.html"):
        for index, script in enumerate(re.findall(r"<script\b[^>]*>(.*?)</script>", path.read_text(encoding="utf-8"), re.S | re.I)):
            if not script.strip():
                continue
            target = Path(directory) / f"{path.stem}-{index}.js"
            target.write_text(script, encoding="utf-8")
            subprocess.run(["node", "--check", str(target)], check=True)
print(f"Python syntax: {count} files; JavaScript syntax: OK")
