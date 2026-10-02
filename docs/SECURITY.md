# Secure configuration

API keys must be retrieved to authenticate requests, so they are encrypted, not hashed.

Windows secrets are encrypted with user-scoped DPAPI and written as ciphertext under the application-data directory. Other operating systems require a supported system keychain (macOS Keychain, Secret Service or KWallet). Unsupported/plaintext backends are rejected.

SQLite contains settings metadata, content and activity only. OAuth access/refresh tokens and the session signing secret use the secret store. AI keys are stored separately per provider. Secret routes expose masked values by default; reveal is an explicit POST, and the UI clears it after 15 seconds or when hidden. Revealing cannot protect against someone who already controls your OS account or screen.

Exports never read the secret store. Database restore imports validated rows into our schema, never runs imported triggers, and clears approval/pending scheduling authority. Restoring does not replace credentials.

Development `.env` import is optional and disabled in bundled builds. If you use it, keep that private file off Git and backups. `.env.example` contains placeholders only.

## Commit protection

Enable the included pre-commit hook with `git config core.hooksPath .githooks`. CI also runs `scripts/secret_scan.py`. It rejects common credential/database files, known token patterns, and locally configured credential values when available. No detector can recognize every possible secret; review diffs before publishing.

If a real secret is ever committed, deleting it in a later commit is not sufficient. Revoke/rotate it at the provider, then coordinate history cleanup. Do not put the secret value in an issue or log.

## Platform boundary

The app does not scrape X, collect cookies, evade platform limits, or automate mass replies. API reading and publishing use official endpoints. Approval protections are enforced by the backend, not merely by hiding UI buttons.

It is a local single-user app. Do not expose its port to a network or deploy it as a public service.

## ChatGPT connection and terminal

ChatGPT OAuth tokens, refresh tokens and retained ID tokens have no renderer reveal route. They remain in the existing OS vault. A temporary loopback listener processes browser callbacks in the backend. The UI receives account metadata and permission state only.

The terminal is an application command interface, with no operating-system shell. Tools validate model-provided arguments. External/destructive requests require a separate human confirmation; social posts cannot grant permissions. See AI-TERMINAL.md for the implemented boundaries.
