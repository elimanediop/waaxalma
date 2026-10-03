# v1.0.0 Slice 5 — Stable Release Acceptance

Overlay for the already integrated and validated v1.0.0 Slices 1–4.
Copy all included paths into the project root, including .github/workflows.
Preserve your .env, virtual environments and data volume. No dist directory
is delivered: wheels and images must be rebuilt from the accepted source.

Versions are aligned to 1.0.0. The changelog is docs/CHANGELOG.md; books are
docs/Architecture_Vision_Book_v1.0.0.md and
docs/book/Waaxalma_Architecture_Vision_Book_v1.0.0_EN.docx.

Follow docs/release-v1.0.0.md for local checks, clean dist build, all CI jobs,
container and three-mode browser acceptance, upgrade backup and final tag.
Local checks: 472 passed, 4 optional OTel SDK skips, one existing warning;
syntax, snapshots, runtime/release checks and fresh wheel installation passed.
Windows/container/browser and UI render checks remain final acceptance.
No tag or public release is created by copying this overlay.
