# Direct update correction - 0.3.3

Verified October 3, 2026.

The installed 0.3.1 backend differed from the newly built backend while both had the same version. The updater correctly compared published releases, but could not discover an unpublished local installer. A subsequent public 0.3.2 release contained only an EXE, without its updater signature or latest.json. Such a release offers a download, not signed in-app installation.

This change uses a new version, 0.3.3, and packages the EXE, version-bound signature, latest.json and SHA256. It preserves the existing public verification key. No public version assets are replaced. The release script now checks committed source, its presence on GitHub, and verifies signatures before uploading.

Settings > Updates distinguishes the installed version from the published version and explains why local source changes are not installed. It lists native installer downloads only when they exist in the official release. Guidance explains Windows publisher/reputation warnings, macOS signing/notarization and Linux executable/package requirements. It does not tell users to disable security globally. Native updater URL selection now uses each platform's updater artifact rather than always requesting an EXE.

Provider cards distinguish API-key setup, local-server setup, OpenRouter browser authorization and existing ChatGPT authorization. Third-party consumer subscriptions are not represented as API authorization.

Validation before publishing: 161 Python tests, six Node UI suites, packaged-backend launch/restart/profile persistence smoke, secret scan, whitespace check and Windows signed build passed. The installer signature and version binding were independently verified. Native updater URL tests are separate from native Mac/Linux build verification.

Mac/Linux release assets are unavailable. GitHub Actions run 37123272612 refused to start all native jobs because the owner account is locked by a billing issue. Those platforms need unlocked runners or native build machines. Windows is built locally. No social actions or paid AI generations were used to test the update.

The integrated terminal now supports Enter/Shift+Enter, Ctrl+C cancellation, editable multiline input, numbered exact approvals and follow-up choices. It receives local Radar/limit/video metadata, can refresh supported Radar sources, generate grounded reports, request interest/limit changes for approval and request potentially paid video jobs for exact approval. No OS shell or unrestricted browser is exposed. Ten focused backend tests and a keyboard-dispatch UI suite cover these behaviors.

A private backup of the existing workspace and comparison fingerprints were saved before attempting the installed-app update. End-to-end installation results are reported after the actual update, not inferred from the build.

## Changed files in this correction

- `README.md`
- `app/command_bus.py`
- `app/command_tools.py`
- `app/paths.py`
- `app/static/app.css`
- `app/static/terminal.js`
- `app/static/updates.js`
- `app/templates/desktop.html`
- `app/terminal_feedback.py`
- `app/terminal_routes.py`
- `app/updates.py`
- `docs/AI-TERMINAL.md`
- `docs/BUILD.md`
- `docs/RELEASE-NOTES.md`
- `docs/UPDATES.md`
- `package-lock.json`
- `package.json`
- `scripts/check_feedback.cjs`
- `scripts/check_profile_ui.cjs`
- `scripts/check_social_ui.cjs`
- `scripts/check_ui.cjs`
- `scripts/publish_release.py`
- `scripts/smoke_backend.py`
- `src-tauri/Cargo.lock`
- `src-tauri/Cargo.toml`
- `src-tauri/src/updates.rs`
- `src-tauri/tauri.conf.json`
- `tests/test_social.py`
- `tests/test_updates.py`
- `app/static/terminal-interactive.js`
- `app/terminal_context.py`
- `docs/INSTALLATION.md`
- `docs/UPDATE-0.3.3.md`
- `scripts/check_terminal_interactive.cjs`
- `tests/test_terminal_interactive.py`

## Actual installed-app result (October 4, 2026)

The signed 0.3.1-to-0.3.3 download completed, but the old native shutdown code killed the PyInstaller launcher before its Python child exited. The installer replaced the desktop executable while the still-running backend prevented replacement of its file. Automatic restart did not succeed. This is a failed direct-update test, not a successful one.

Recovery stopped only the verified orphan owned by this installation, re-ran the signature-verified 0.3.3 installer (exit 0), and launched the installed app. `/health` reported 0.3.3. Dashboard, interactive terminal assets/context, AI provider catalog, video settings and Trend Radar returned HTTP 200. Hash comparisons against the private pre-update SQLite backup confirmed drafts, actions, schedules, social-account metadata, My Profile, Writing Voice, My Product and Brand Voice were unchanged. No real social action was sent.

The process-lifecycle repair is tracked in version 0.3.4. Published 0.3.3 artifacts are not replaced.
