# Contributing

Extend the existing FastAPI/Tauri app incrementally. Preserve paid X search, web fallback, OAuth, manual import, provider configuration, and approval-first publishing.

Read [architecture](docs/ARCHITECTURE.md), [build instructions](docs/BUILD.md), [AI Terminal](docs/AI-TERMINAL.md), and [social adapters](docs/SOCIAL-PROVIDERS.md).

    py -3.13 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
    npm ci
    .\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
    npm run check:ui

Tests use temporary databases and a test vault; unmocked async network calls fail. Never test real social publishing, replies, comments, likes, follows, DMs, or media uploads.

The optional .env.example is for contributors. Never commit secrets, local databases, private media, or ChatGPT installation records.

Register tools with typed schemas. Never expose a shell, credentials, or model self-approval. Document dependencies and regenerate third-party notices before distribution.
