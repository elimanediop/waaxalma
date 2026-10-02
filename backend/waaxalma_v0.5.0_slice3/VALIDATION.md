# Slice 3 validation

- 297 backend tests passed in Python 3.12.14 using the backend dependency lock,
  including 270 Slice 2 tests and 27 new configuration/health tests.
- One upstream Starlette/AnyIO deprecation warning; no failed tests.
- Hash-verified installs completed for backend runtime, test/build, and UI locks.
- Backend wheel built and installed in a fresh runtime-only virtual environment.
- Installed console command launched from a temporary directory outside source.
- /health, /health/live, /health/ready returned 200; SQLite session creation/read
  with waaxalma-for-elimane preserved owner_id. No remote provider calls.
- Two wheel builds using SOURCE_DATE_EPOCH=1760000000 were byte-identical.
- UI typed environment config, internal/public URL distinction and client ID
  injection verified across Direct/Enhanced/conference clients.
- Generated embedded JavaScript (9 scripts) passed node --check.
- Standard/Direct/Enhanced Streamlit UI rendered without exceptions in AppTest
  with Streamlit 1.64.0. Existing iframe API is supported by the locked version.
- Compose YAML parsed and service contexts, health dependency, volume, non-root
  USER declarations and base digests checked structurally.
- Python base manifest digest verified against Docker Hub.

## Execution limits

No Docker executable/daemon is available in this environment. Docker image builds,
container USER/volume permissions and docker compose up were not executed. The
provided Dockerfiles declare UID/GID 10001, and Compose declares writable runtime
storage; those behaviors still need a Docker smoke run on the target host. Native
non-root switching was also unavailable in this execution environment.

Microphone/virtual cable routing and live OpenAI translation were not tested here.
The preceding Slice 2 UI was confirmed working by the user; Slice 3 rendering and
configuration checks preserve its client identity.

## Windows lock correction

The original Linux-only locks omitted Windows conditional dependencies. All
four locks were regenerated with universal Python 3.12 resolution. A separate
Windows-targeted resolution agrees with the universal dev lock (36 pinned
packages, including colorama==0.4.6). Linux hash-verified installation and all
297 tests pass with the corrected dev lock. Windows execution remains to be
confirmed on the user's workstation.

## SQLite connection lifecycle correction

SQLite transaction context managers do not close connections. Repository
operations now commit/roll back and close in a finally block. Readiness uses
contextlib.closing; the legacy owner command also closes its connection. Test
fixtures explicitly close their SQLite handles. Three new tests retain strong
references and prove handles are closed after successful operations, failed
writes, and readiness probes. Full suite: 300 passed under Linux. Windows
execution of the corrected code remains to be confirmed on the user host.
The wheel was rebuilt with this correction.
