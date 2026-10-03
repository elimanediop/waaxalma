"""Validate distributable metadata and emit SHA256 sums for release candidates."""
import hashlib
from email.parser import BytesParser
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
wheels = list((root / "dist").glob("waaxalma_backend-*.whl"))
assert len(wheels) == 1, wheels
with zipfile.ZipFile(wheels[0]) as archive:
    names = archive.namelist()
    metadata = BytesParser().parsebytes(archive.read(next(n for n in names if n.endswith(".dist-info/METADATA"))))
    assert metadata["Name"] == "waaxalma-backend"
    assert metadata["Version"] == "0.5.0"
    assert "app/main.py" in names and "app/core/settings.py" in names
    assert "app/framework/__init__.py" in names
    assert "app/framework/testing.py" in names
    assert not any(n.endswith(".env") or n.endswith(".db") for n in names)
files = sorted(p for p in (root / "dist").iterdir() if p.is_file() and p.name != "SHA256SUMS")
(root / "dist/SHA256SUMS").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files))
print("Wheel metadata and artifact checksums: OK")
