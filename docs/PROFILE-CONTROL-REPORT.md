# Profile save fix and expanded application controls

## Root cause and complete save flow

`app/static/accounts.js` rendered My Profile and Brand Voice with `id="memory-form"`. `app/static/terminal.js` used the same ID for individual writing preferences. `app/static/forms.js` dispatched that ID to `terminalSubmit()` before it checked social Settings forms. That sent the entire Title Case profile object to `memory.savePreference` through `/api/terminal/request`.

The tool accepts exactly `{key, value}` with unknown fields forbidden. `key` must be one of `tone`, `reply_length`, `favorite_topics`, `blocked_topics`, `platform_preferences`; `value` is a nonempty string up to 1,000 characters. The eight profile fields satisfy none of that schema, so command validation correctly returned HTTP 400. The profile handler in `social-actions.js` was unreachable.

The fixed flow is:

`structured-profile-form` -> `submit()` -> `msSubmit()` -> `PUT /api/profile` -> strict `ProfilePatch` -> `save_profile()` -> existing SQLite settings record `my_profile`.

`GET /api/profile` loads the saved record when Settings opens. Canonical fields are `name`, `role`, `bio`, `industry`, `expertise`, `products`, `audience`, `goals`. Earlier Title Case records remain readable. Partial updates preserve omitted fields, optional null/empty values become empty text, and invalid types/unknown or oversized fields return useful HTTP 422 validation errors without overwriting the record. Name allows 160 characters; role/industry 240; other fields 4,000. Successful UI saves say **Profile saved**. Brand Voice has its own save path; the individual preference form is `writing-preference-form`.

No database migration is required: the app already stores structured JSON records in SQLite. No credentials were moved into the database. Development validation logging (`XEA_DEBUG_VALIDATION=1`) includes only schema/field/error-code metadata, not input values, tokens, keys or secrets.

## Shared terminal controls

The registry now contains 85 typed application tools. Added controls cover profile, non-secret Settings and safety limits, writing/product context, local feed state, topics, watchlist edits, draft creation/editing/deletion/attachments, media metadata/transforms/assistance, idea editing, exports, brief/market/plan inspection and AI connection tests. Existing discovery, X paid search, manual fallback, publishing, approvals and scheduling tools remain available.

All settings changes, destructive operations, attachments and external actions have exact approval previews. Plain `yes` confirms only the selected preview; it cannot grant blanket authority. Changed settings/profile/records invalidate old previews. Partial profile updates retain their original supplied-field set through approval serialization. Local draft deletion cancels schedules and pending previews and retains a tombstone so an old ID cannot refer to a newly created draft. Activity and duplicate protection are preserved.

`show limits` explains local caps versus external quotas; `check draft 12` checks local limits and duplicate content without publishing. Explicit commands do not consume AI quota. Natural-language routing uses the same strict registry and approval engine. AI health tests call the same service as the Settings button. Settings reload current values so changes made in the terminal appear in the GUI.

Secrets, arbitrary SQL/shell access, disabling approval protections and bypassing API quotas are not exposed. Public-post deletion is not implemented; use the original platform. File upload, credential entry/reveal, database restoration and complete workspace erasure remain explicit GUI workflows reachable through Settings/Media navigation, not model-controlled filesystem access.

## AI providers

Added Grok/xAI Responses, Claude native Messages, Kimi OpenAI-compatible and DeepSeek OpenAI-compatible adapters. Settings provides official console links, model fields, masked/retrievable OS-protected per-provider API keys and Claude's optional workspace ID. No new Python dependency was needed. No consumer-account OAuth or subscription authorization is fabricated. API billing is separate; selection is explicit and there is no silent fallback. ChatGPT, Gemini, OpenAI, custom endpoints and Ollama remain available.

Provider payloads, health checks, empty responses, credential isolation, masking and HTTP 401/402/403/429 handling were tested with mocked network calls. No live keys for the four new providers were supplied, so live inference/sign-in is not claimed. Pasted recognizable xAI keys are redacted/rejected before terminal history.

Official references: [xAI](https://docs.x.ai/developers/quickstart), [Claude authentication](https://platform.claude.com/docs/en/manage-claude/authentication), [Kimi](https://platform.kimi.ai/docs/overview), [DeepSeek](https://api-docs.deepseek.com/).

## Verification

- Full suite: 115 tests passed; subsequent focused tests passed for cancelled deletion previews and rejecting unconfigured xAI keys (one additional test).
- All four JavaScript checks passed, including actual Settings submit dispatch, profile/Brand Voice separation, exact success text, saved field rendering and failure propagation. No browser automation was used.
- Profile tests cover all fields, partial fields, empty optional values, malformed payloads, persistence, legacy records and sanitized development diagnostics.
- The packaged FastAPI executable launched, loaded the dashboard, accepted a structured profile, processed a terminal profile-name edit with explicit confirmation, and retained the saved record across an actual process restart. Social write count remained zero.
- Production installer and updater signature were built and independently cryptographically verified. The final 31.13 MiB installer was installed locally, and the installed backend hash matches the tested artifact. Existing profile data and encrypted credential files were unchanged; a private SQLite backup was created before installation. The installed dashboard, profile API and new provider Settings loaded, with zero social writes.
- Tracked-file and Git-history secret-pattern audits passed; this is pattern-based detection, not proof that every possible secret format is recognizable.
- Native-window launch and dark dashboard rendering were verified using an isolated workspace and a window screenshot; closing the app stopped its backend. A manual click-through of the Settings form has not been performed; renderer-dispatch and HTTP tests are the verified coverage.

Developer commands:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
npm run check:ui
.\.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8787 --no-access-log
```

See [BUILD.md](BUILD.md) for developer prerequisites, unsigned builds and signed Windows installer generation. End users install the compiled executable and configure the app in Settings.

## Exact changed files in this release checkpoint

This includes the earlier pending release-update/email work as well as the profile/control/provider changes.


### Modified

- `.github/workflows/windows.yml`
- `README.md`
- `app/command_bus.py`
- `app/command_tools.py`
- `app/main.py`
- `app/paths.py`
- `app/preferences.py`
- `app/providers.py`
- `app/social/content_routes.py`
- `app/static/accounts.js`
- `app/static/app.js`
- `app/static/forms.js`
- `app/static/settings.js`
- `app/static/social-actions.js`
- `app/static/social.js`
- `app/static/terminal.js`
- `app/templates/desktop.html`
- `app/terminal_feedback.py`
- `app/workers.py`
- `app/workspace.py`
- `app/workspace_routes.py`
- `docs/BUILD.md`
- `docs/DEPENDENCIES.json`
- `docs/IMPLEMENTATION-REPORT.md`
- `docs/THIRD_PARTY_NOTICES.txt`
- `package-lock.json`
- `package.json`
- `scripts/check_ui.cjs`
- `scripts/secret_scan.py`
- `scripts/smoke_backend.py`
- `scripts/smoke_desktop.py`
- `src-tauri/Cargo.lock`
- `src-tauri/Cargo.toml`
- `src-tauri/src/main.rs`
- `src-tauri/tauri.conf.json`

### Created

- `app/local_controls.py`
- `app/profile.py`
- `app/static/updates.js`
- `app/updates.py`
- `app/validation.py`
- `docs/PROFILE-CONTROL-REPORT.md`
- `docs/RELEASE-NOTES.md`
- `docs/UPDATES.md`
- `scripts/build_signed.ps1`
- `scripts/build_signed.py`
- `scripts/check_profile_ui.cjs`
- `scripts/package_release.py`
- `scripts/publish_release.py`
- `scripts/setup_update_key.py`
- `src-tauri/src/updates.rs`
- `src-tauri/tauri.ci.conf.json`
- `tests/test_extended_control.py`
- `tests/test_extra_providers.py`
- `tests/test_profile.py`
- `tests/test_updates.py`
