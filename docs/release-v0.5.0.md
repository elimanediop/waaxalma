# Release governance — v0.5.0

The six slices form the release candidate: persistence, identity/owner boundaries, typed configuration/packaging, CI quality gates, observability and lifecycle/governance. The distribution does not create a Git tag, publish a GitHub Release or deploy a cloud environment.

## Before the final tag

1. Review the merged diff and tracked files. Preserve local .env/data and verify no keys/databases entered Git history. A targeted automated check complements this review; it does not certify the absence of secrets.
2. Require static checks, backend Windows/Linux tests, separate UI Windows/Linux installs, optional SDK tests, wheel verification, container build, HTTP smoke and clean-exit/restart persistence smoke.
3. Perform the browser checks on Standard, Direct and Enhanced with your actual provider configuration. Experimental inbound/full-duplex remains experimental and must not be advertised as release-certified.
4. Review SECURITY.md, operations, environment variables, retention defaults and Architecture & Vision Book. Decide the deployment boundary and any additional dependency vulnerability scan appropriate for deployment.
5. Record the commit SHA, runner outcomes, image digests, wheel and image archive SHA256SUMS. Store a reviewed backup and identify a prior compatible rollback image.

Branch protections are repository settings: configure them yourself to require all quality workflow jobs. The workflow uses minimal contents:read permission and no cloud deployment secrets. It runs on pull_request, main/master pushes, manual dispatch and the final v0.5.0 tag. No privileged pull_request_target workflow is added. Major-version action references remain an explicit governance limitation; use reviewed immutable SHAs if that is your repository policy. Dependency locks and the container base digest are pinned.

## Tag after checks pass

From the reviewed clean checkout, after the PR checks have passed:

```powershell
git status --short
git rev-parse HEAD
git tag -a v0.5.0 -m "Waaxalma v0.5.0 — Product Readiness"
git push origin v0.5.0
```

These are operator instructions, not actions already performed. Verify that the tag points to the reviewed commit. The tag triggers the same quality workflow; its downloadable artifact is not automatically promoted to a public release. Create the release manually after that workflow passes, using the wheel, tested image archive and checksums. CI artifacts currently expire after 14 days: preserve final assets through your chosen release channel.

## Remaining limitations

X-Client-Id is not authentication; static audio is not owner-authorized; default metrics are single-process; usage/cost is partial; no active-session expiry/file retention, cloud deployment, vulnerability certification or exactly-once lifecycle/billing ledger is implemented. Optional exporter shutdown has a logical wait budget rather than forced thread termination. These are intentional release scope boundaries documented for operators.
