# Architecture

## Process model

Tauri owns a WebView2 window and a bundled PyInstaller backend sidecar. The sidecar contains Python and dependencies and binds only to 127.0.0.1:8787. It serves local HTML/CSS/JavaScript and FastAPI routes. Closing the app stops its backend, unless optional tray mode keeps the app running.

The desktop shell holds an ephemeral control token passed through the sidecar environment. Only that token can pause monitoring, retrieve native notifications, or stop the backend through private desktop routes. No API keys pass through Tauri IPC. External X/OAuth/help links open in the system browser.

## Modules

- `paths.py`: version and per-user writable paths, separate from packaged resources.
- `secrets.py`: per-user Windows DPAPI or OS keychain, no plaintext fallback.
- `preferences.py`, `settings_routes.py`: validated nonsecret settings and masked secret operations.
- `database.py`: transactional schema migrations using SQLite user_version.
- `providers.py`: AIProvider interface and Gemini/OpenAI/compatible/Ollama adapters.
- `x_api.py`: preserved OAuth PKCE/token refresh and official reads/writes.
- `search.py`: recent-search mode selection, counts, daily cap, billing block and fallback.
- `discovery.py`: account/topic polling, last-seen deduplication, backoff and manual alternatives.
- `workspace.py`: generation, exact-content approval, safety checks and serialized publishing.
- `workers.py`: independent scheduling and monitoring tasks.
- `backup.py`: portable export and validated restore into the application's schema.
- `workspace_routes.py`: feed, drafts, approvals, scheduler, watchlist, topics and local analytics.
- `static/`: responsive workspace and six-step onboarding; untrusted content is escaped.
- `desktop_control.py`, `desktop_entry.py`: private native controls and runtime lifecycle.
- `src-tauri/`: Windows shell, tray, notifications and installer metadata.

## Approval state machine

Draft ? approved ? explicit publish ? sending ? published.

The approval fingerprint covers kind, target post and exact text. An edit removes approval and cancels its pending schedule. Draft generation has no publishing side effects. A scheduler only accepts original posts that retain the exact approved fingerprint.

Sending is persisted before an external request. Ambiguous failures become uncertain; partially published threads become partial. Neither is automatically retried. API access failures are visible and require a human to review before another attempt.

Scheduled originals: approved ? scheduled ? sending ? published. Missed startup deadlines become missed; interrupted sends become uncertain. A restored backup cannot restore publishing approval.

## Limits and request protection

Writes are serialized locally and recheck daily/hourly, duplicate, similar-text and repeated-author limits immediately before sending. Search has its own persisted daily budget and 402/access block. Monitoring is opt-in with a minimum 15-minute per-source interval. 429 responses respect reset/backoff metadata.

Browser mutations require a session CSRF token and matching Origin when present. Responses disable caching and apply a Content Security Policy. Localhost host validation mitigates DNS rebinding. The app is not intended for remote hosting.

## Analytics

Only observed local events count. Manual composer opening is not treated as a successful reply. AI relevance is a model suggestion, not a predicted engagement outcome. X metrics are displayed only when supplied by an official response.
