import os
from pathlib import Path
import tempfile

os.environ.setdefault("APP_ENV", "test")
# Test suites never inherit destructive automatic maintenance from a deployment.
os.environ["SESSION_CLEANUP_ENABLED"] = "false"
_test_data = tempfile.TemporaryDirectory(prefix="waaxalma-tests-")
os.environ.setdefault("DATA_DIR", str(Path(_test_data.name)/"data"))
os.environ.setdefault("STATIC_DIR", str(Path(_test_data.name)/"static"))
os.environ.setdefault("UPLOAD_DIR", str(Path(_test_data.name)/"uploads"))
