"""Release hygiene on tracked files; reports paths only, never matched secrets."""
from pathlib import Path
import re
import subprocess
import sys
import tomllib

root = Path(__file__).resolve().parents[1]
try:
    names = subprocess.check_output(['git','ls-files','-z'],cwd=root,stderr=subprocess.DEVNULL).decode().split('\0')
    files = [root/name for name in names if name]
except subprocess.CalledProcessError:
    # Authoring bundle validation without Git; deployment uses git-tracked files.
    files = [p for p in root.rglob('*') if p.is_file() and not any(x in {'__pycache__','.pytest_cache','build','dist','data','tmp'} or x.startswith('.venv') or x.endswith('.egg-info') for x in p.relative_to(root).parts)]

problems = []
patterns = [rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}', rb'AKIA[A-Z0-9]{16}', rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
for path in files:
    rel = path.relative_to(root)
    if path.name.startswith('.env') and path.name != '.env.example':
        problems.append(str(rel)+': environment file tracked')
    if any(part in {'data','tmp','dist','build','__pycache__'} or part.startswith('.venv') for part in rel.parts):
        problems.append(str(rel)+': generated/private data tracked')
    if path.is_file() and path.stat().st_size < 2_000_000:
        if any(re.search(pattern,path.read_bytes()) for pattern in patterns):
            problems.append(str(rel)+': possible credential/private key')

metadata = tomllib.loads((root/'backend/pyproject.toml').read_text())
version = metadata['project']['version']
namespace = {}
exec((root/'backend/app/version.py').read_text(),namespace)
if version != namespace['__version__'] or version != '0.5.0':
    problems.append('Backend version mismatch')
for document in ['README.md','SECURITY.md','docs/operations.md','docs/release-v0.5.0.md','docs/Architecture_Vision_Book_v0.5.0.md']:
    if not (root/document).is_file():
        problems.append(document+': missing release documentation')
if problems:
    print('\n'.join(problems),file=sys.stderr)
    raise SystemExit(1)
print('Release versions, required documentation and targeted credential hygiene: OK')
