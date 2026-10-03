# Provider, Trend Radar, Video and Desktop implementation report

Verified: 2026-10-03

## Result

Extended the existing FastAPI + SQLite + vanilla JavaScript + Tauri application. Kept the existing X OAuth, paid recent search, manual fallback, approvals, scheduler and social adapters. No social action or paid AI generation was performed during this work. Existing user settings and installed application data were not replaced.

### AI providers

Provider-neutral BYOK settings support simultaneous provider configurations, OS-backed keys, official setup links, dynamic model discovery, capability metadata, normalized errors, streaming adapters, optional per-feature models and explicit transient-error fallback. Native adapters cover Anthropic Claude, Cohere, DeepSeek, Gemini, Groq, Kimi, LM Studio, Mistral, Ollama, OpenAI, OpenRouter, Together and xAI, plus custom OpenAI-compatible endpoints. Existing optional ChatGPT integration remains separate. Consumer subscriptions are not presented as API credentials. Official documentation research is in [ai-providers](ai-providers/README.md).

Local AI Only blocks cloud generation and fallback. Context selection and a data preview control what writing/profile/product context may be sent. Requests log metadata by default; prompt history is opt-in. OpenRouter supports its official PKCE flow as well as BYOK. New provider credentials, OAuth and paid inference have mocked coverage; they were not validated with real paid accounts.

### Trend Radar

Adds Mastodon, DEV/Forem and PeerTube open-source platform APIs and the official public Hacker News API. Fixed public sources, explicit refresh, daily caps, caching, rate-limit backoff and independent source failures. Interests, exclusions, saved/ignored state and media filters persist locally. Preview audio/video/images only on request; unsupported media uses Open Original. AI can turn selected source material into reviewable posts, threads, video scripts and audio outlines. Source content is untrusted data, not agent instructions. Scores are local relevance measures, not virality predictions; no fabricated growth metrics or automatic transcription.

Live unauthenticated checks retrieved 30 PeerTube videos and 20 Hacker News stories. Mastodon timed out and DEV returned a connection error in this environment; those two live integrations remain unverified. Mocked contracts and graceful-failure paths passed. See [Trend Radar](TREND-RADAR.md).

### Video Generation

Added Settings > Video Generation separately from image generation and text providers. Gemini Veo and xAI adapters discover video models, use dedicated secure keys and submit only after explicit potentially-paid confirmation. Media includes a text-to-video prompt, persistent jobs, bounded status polling and saving ready MP4s into the local Media Library. Idempotency prevents automatic resubmission after uncertain responses. Signed output links stay in the OS vault, and download redirects never forward keys to storage hosts. Local AI Only blocks cloud video operations. No social upload or publishing occurs during generation/download.

Only text-to-video is implemented. Video editing, image-to-video, Gemini Omni, automatic transcription and provider cancellation are not implemented. Sora Videos API is excluded because the current official reference states its September 24, 2026 shutdown. No paid video job was submitted; adapters and job safety were tested with mocks. See [Video Generation](VIDEO-GENERATION.md).

### Desktop distribution

Windows NSIS build includes Python/backend runtime. Added native macOS Apple Silicon/Intel .app/.dmg and Linux x64 .deb/.AppImage configuration, native CI build jobs, icons, checksums, OS keychain handling and platform-aware update selection. macOS/Linux installers have NOT been built or executed on this Windows machine. Native CI results, macOS signing/notarization and Linux distribution compatibility must be verified before public release. No release was published. Windows local test installer is not an Authenticode-signed public release and updater artifact generation is disabled for this build.

## Storage and dependencies

SQLite migrations 8, 9 and 10 add AI connections/model cache/request metadata, Trend Radar records/source state, and video jobs. The database makes a private pre-migration backup. Credentials are separate from SQLite: DPAPI on Windows; approved OS keychain backends on macOS/Linux, with no plaintext fallback. Legacy AI configuration is migrated without deleting its original source. No new Python or npm dependencies were added. Version remains 0.3.1.

## Verification

- Full regression suite: 147 tests passed before the final metadata/cache adjustments.
- After those adjustments: 14 BYOK tests and 20 workflow tests passed. One workflow fixture was corrected to provide real string provider/model metadata rather than a MagicMock.
- Five video tests passed, covering secure setup, confirmation, duplicate submission, restart, local-only mode, wire contracts, polling, signed-link secrecy and download credential boundaries.
- Five Node VM UI suites passed. These test handlers, rendering, escaping and confirmation; they are not a manual visual browser audit. No Selenium, Playwright or browser automation was used.
- Python syntax checks passed; git diff whitespace checks passed.
- Working-tree secret scan passed; audit of 327 historical blobs found no common secret-pattern matches. Pattern scanning cannot prove absence of every possible secret.
- Final packaged backend smoke passed: launch, dashboard/assets, terminal/status, neutral AI setup, onboarding/settings, secure credential roundtrip, URL parsing, automation storage and zero social writes. Structured profile persisted across a real packaged-process restart.
- PyInstaller backend build passed. Final Windows Tauri/NSIS build passed (31.23 MiB). Local installer: `artifacts/Social-Engagement-Command-Center-Setup.exe`. SHA256: `8a36603ff2c1d8805ff9022572192d0e3c1fc66ddd05d9d53e7943eab611debe`. No installation or release publishing was performed.

## Developer commands

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
npm run check:ui
.venv\Scripts\python.exe -B scripts/secret_scan.py --working-tree
.venv\Scripts\python.exe -B scripts/build_backend.py
.venv\Scripts\python.exe -B scripts/smoke_backend.py dist/xea-backend.exe
npm run desktop:build -- --config src-tauri/tauri.ci.conf.json
.venv\Scripts\python.exe scripts/package_checksums.py
```

For web development: `.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8787 --no-access-log`. Desktop development: `npm run desktop:dev` after building the sidecar. End users run the installer and configure providers in the UI. Native macOS/Linux commands, signing and prerequisites: [Desktop platforms](DESKTOP-PLATFORMS.md).

## Exact file inventory

The working tree already contained profile/settings/terminal fixes before this task. They were retained. Overlapping shared-file changes were extended in place rather than reverted.

### Created in this task

- `.github/workflows/unix-desktop.yml`
- `app/ai_adapters.py`
- `app/ai_base.py`
- `app/ai_catalog.json`
- `app/ai_connections.py`
- `app/ai_registry.py`
- `app/ai_routes.py`
- `app/openrouter_auth.py`
- `app/static/ai-providers.js`
- `app/static/trends.js`
- `app/static/video.js`
- `app/trend_radar.py`
- `app/video_providers.py`
- `docs/DESKTOP-PLATFORMS.md`
- `docs/PROVIDER-RADAR-VIDEO-REPORT.md`
- `docs/TREND-RADAR.md`
- `docs/VIDEO-GENERATION.md`
- `docs/ai-providers/README.md`
- `docs/ai-providers/anthropic.md`
- `docs/ai-providers/cohere.md`
- `docs/ai-providers/deepseek.md`
- `docs/ai-providers/gemini.md`
- `docs/ai-providers/groq.md`
- `docs/ai-providers/kimi.md`
- `docs/ai-providers/lmstudio.md`
- `docs/ai-providers/mistral.md`
- `docs/ai-providers/ollama.md`
- `docs/ai-providers/openai.md`
- `docs/ai-providers/openrouter.md`
- `docs/ai-providers/together.md`
- `docs/ai-providers/xai.md`
- `scripts/check_radar_video_ui.cjs`
- `scripts/package_checksums.py`
- `src-tauri/entitlements.plist`
- `src-tauri/icons/icon.icns`
- `src-tauri/tauri.linux.conf.json`
- `src-tauri/tauri.macos.conf.json`
- `tests/test_byok.py`
- `tests/test_trend_radar.py`
- `tests/test_video.py`

### Modified in this task

- `README.md`
- `SECURITY.md`
- `app/command_bus.py`
- `app/command_tools.py`
- `app/database.py`
- `app/drafting.py`
- `app/errors.py`
- `app/image_providers.py`
- `app/main.py`
- `app/planner.py`
- `app/preferences.py`
- `app/providers.py`
- `app/secrets.py`
- `app/security.py`
- `app/settings_routes.py`
- `app/social/content_routes.py`
- `app/social/privacy.py`
- `app/static/actions.js`
- `app/static/app.css`
- `app/static/app.js`
- `app/static/forms.js`
- `app/static/settings.js`
- `app/static/social.js`
- `app/static/updates.js`
- `app/templates/desktop.html`
- `app/updates.py`
- `app/workspace.py`
- `app/workspace_routes.py`
- `docs/BUILD.md`
- `package.json`
- `scripts/build_backend.py`
- `scripts/check_profile_ui.cjs`
- `scripts/check_social_ui.cjs`
- `scripts/check_ui.cjs`
- `scripts/make_icons.py`
- `scripts/secret_scan.py`
- `scripts/smoke_backend.py`
- `src-tauri/src/updates.rs`
- `src-tauri/tauri.conf.json`
- `tests/test_extra_providers.py`
- `tests/test_updates.py`
- `tests/test_workflow.py`

### Pre-existing changes preserved

- `app/context_settings.py`
- `app/local_controls.py`
- `app/profile.py`
- `app/static/terminal.js`
- `app/terminal_feedback.py`
- `app/terminal_routes.py`
- `docs/SETTINGS-VERIFICATION-REPORT.md`
- `scripts/verify_live_settings.py`
- `tests/test_settings_receipts.py`
