# Settings saves and terminal completion receipts

## Root causes

- `settings.context` exposed an arbitrary string map to the AI, while persistence accepted a different fixed set of field names. Brand Voice uses display-case keys. Invalid arguments reached an approval preview and failed only on confirmation.
- The command router did not receive the saved structured profile/context or valid field names. It sometimes updated only My Profile when multiple sections were requested.
- Model prose with no executable actions was displayed as a completed operation. Historical conversation context repeated these unverified claims.
- The visible-preference textarea had no required/length validation, while `memory.savePreference` required 1-1000 characters. The form and backend now agree on trimmed, nonempty text up to 4000 characters.
- The streaming UI did not call its existing tool-result handler, preventing immediate state updates. Failed multi-action commands also omitted completed tool results from history.

## Changes

Canonical context validation is shared by Settings and the terminal. Display-case and snake-case field aliases normalize to the keys rendered by the GUI. Unknown keys are rejected before approval.

`settings.updateContext` prepares a single exact approval for My Profile, Brand Voice, Writing Voice, and My Product. Omitted fields survive. SQLite saves are transactional. The service reads back the saved sections before reporting success. Stale previews are rejected if those sections change before confirmation.

The router receives the current non-secret profile/context and schema fields. Instructions prohibit inventing facts, credentials, or changing safety/provider settings as part of filling personal fields. Pending previews explicitly say they are not saved. No-action model replies do not produce a Completed receipt. Successful results replace model promises in history, and partial failures retain completed results.

The UI uses tool results to refresh its local settings state. Preference validation now explains empty or overlong inputs before a request. Unknown forms cannot claim a successful save.

## Verification

- Full backend regression suite: see `artifacts/settings-final-tests.log` for the final run.
- Eight targeted settings tests cover four-section persistence, aliases, invalid fields, stale approvals, no-op model claims, read-back failures, partial failures, and writing preferences.
- `npm run check:ui`: all four suites passed. Includes 12 Settings tabs and ordinary profile, brand, voice, product, appearance, safety, discovery, X, and AI save handlers. Empty and overlong preferences are rejected before HTTP; valid long preferences use the right payload.
- Packaged backend: dashboard, credentials abstraction, approval, settings, URL parsing, and persistence across a real process restart passed in an isolated workspace.
- Live installed workspace: 24 read endpoints, 15 explicit terminal read commands, four profile/context save flows, and writing-preference persistence passed. Existing values were retained. Public writes remained zero.
- Native window: Home, Updates, and My Profile were visually inspected; the saved name and role rendered correctly.
- Live ChatGPT inference was attempted after explicit provider selection. The service returned `subscription_sharing_usage_limit_exceeded`. No AI-provider fallback was used by the test. ChatGPT-generated profile filling is therefore NOT verified.
- The live workspace subsequently contained all 32 profile/context fields and selected Gemini following concurrent app activity. Those changes were preserved; they are not attributed to the blocked ChatGPT test.

This is not a claim that every button was clicked against live external services. Publishing, deleting user data, disconnecting accounts, credential changes, and scheduler execution were exercised through isolated tests/mocks. Providers without credentials/access cannot be verified live. No live post, reply, comment, or deletion was performed by this audit.

## Files

Created:
- `app/context_settings.py`
- `tests/test_settings_receipts.py`
- `scripts/verify_live_settings.py`
- `docs/SETTINGS-VERIFICATION-REPORT.md`

Modified:
- `app/command_bus.py`
- `app/command_tools.py`
- `app/local_controls.py`
- `app/preferences.py`
- `app/profile.py`
- `app/terminal_feedback.py`
- `app/terminal_routes.py`
- `app/static/forms.js`
- `app/static/terminal.js`
- `scripts/check_profile_ui.cjs`

No database migration or dependency was added. X OAuth, social adapters, paid X search, scheduler rules and secret storage were not changed. Private audit backups and screenshots are outside tracked source. The backend was rebuilt for the existing Windows installation; this work does not publish a new GitHub release.

## Repeatable checks

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
npm run check:ui
.venv\Scripts\python.exe -B scripts/build_backend.py
.venv\Scripts\python.exe -B scripts/smoke_backend.py dist/xea-backend.exe
```

The live script is opt-in. `propose` uses the selected provider and writes a private preview; inspect it before `apply`. `controls` re-saves existing personal settings and saves a visible tone preference without generating content or changing social accounts. It must not be run concurrently with someone editing those settings.
