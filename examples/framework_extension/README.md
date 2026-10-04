# External framework extension

This offline example imports only `app.framework` for runtime contracts and
`app.framework.testing` for its checks. It does not import application bootstrap,
settings, routers or concrete providers. The demo provider prefixes a language
code; it does not perform real translation. Nothing is auto-registered globally.

The extension explicitly creates three registries and composes a provider,
a pipeline stage and an agent. Supported input is `operation="translate"` with
`payload={"text": "bonjour"}`. Unsupported operations and invalid payloads return
failed `AgentResult` values with demo-specific error codes.

After installing the backend wheel and its locked runtime dependencies, run:

```powershell
python examples/framework_extension/check_extension.py
```

Expected output:

```text
External agent/provider/stage: conformance and composition OK
```

The interpreter must have the wheel installed; running from a checkout alone
does not make `backend/app` importable. Packaging CI copies this example outside
the checkout and runs it against the installed wheel in a clean environment.

Use this composition in your own tests. Integrating extensions into the running
service still requires explicit application wiring; this example does not add
a plugin discovery system or HTTP route.
