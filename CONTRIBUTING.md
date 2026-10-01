# Contributing

Use the development and build steps in README. Keep changes small and runnable.

Run:
```
python -B -m unittest discover -s tests -v
node scripts/check_ui.cjs
python -B scripts/secret_scan.py
```

Enable `.githooks` with `git config core.hooksPath .githooks`.

Tests must mock X/AI requests and use isolated storage. Never publish a real post to test a code path. Do not add browser scraping or private endpoints.

Preserve exact-content approval, no scheduled replies, no automatic replay of uncertain sends, OS-protected secrets, and manual alternatives when read access is unavailable.

Add a versioned database migration for schema changes. A backup restore must not import credentials or resurrect approved schedules.

The interface uses local HTML/CSS/JavaScript; all source content and AI output must be escaped before rendering. Keep provider errors user-readable without including keys or raw response bodies.
