# Windows update shutdown repair - 0.3.4

Verified October 4, 2026.

## Root cause

The actual signed 0.3.1-to-0.3.3 update downloaded and verified its installer, then closed its HTTP listener. The native updater killed only the PyInstaller launcher. Its Python child remained alive and held the backend executable open. The installer replaced the desktop executable while the backend stayed old; restart failed. No successful direct update is claimed for that attempt.

## Repair

The native app records the sidecar termination event and waits for process exit before installation. If graceful shutdown exceeds 15 seconds, Windows stops only the owned PID and its descendants. The updater then checks that the backend executable is released. A remaining file lock prevents installation. Normal Quit shares this cleanup. Old release caches without the platform download catalog are re-fetched instead of indefinitely receiving HTTP 304.

Version 0.3.4 preserves the signing key and never replaces public 0.3.3 assets. No schema migration, provider credential change, OAuth change, scheduler change or social integration change was needed.

## Actual verification

- 14 mocked Python updater tests passed, including the new legacy-cache regression.
- Four native Rust tests passed, including a real disposable parent/child tree holding a file lock. One fixture-only test is intentionally ignored by the normal harness and invoked by the regression test.
- All six Node UI suites passed, including interactive terminal keyboard/choice/cancellation tests.
- Packaged backend smoke passed with an explicit source-version assertion, profile persistence after restart, secret masking, URL parsing, settings, terminal/context and zero social writes.
- Optimized Tauri Windows build and NSIS installer succeeded. The installer signature, version binding and checksum were independently verified.
- The verified local installer exited 0. The installed backend SHA-256 matched the tested bundled backend.
- Two isolated native startup/normal-close cycles passed, with no owned backend process left behind.
- The normal installed workspace reports 0.3.4. Dashboard, interactive terminal assets/context, provider catalog, video settings and Radar routes returned HTTP 200.
- Hash comparisons against a private pre-install SQLite backup confirmed drafts, actions, schedules, social account metadata, My Profile, Writing Voice, My Product and Brand Voice were unchanged.
- Syntax and whitespace checks passed. Secret scanning is also run at the source checkpoint.

The local upgrade used the verified installer to recover from the old updater. A complete future in-app download/install from 0.3.4 to a newer published version has not yet been exercised. The process cleanup responsible for the observed failure was tested directly and through the actual native application; this is not a guarantee against all network, disk or OS failures.

No public social action or paid AI/video generation was issued during these checks. UI regression tests use local JavaScript execution, and native lifecycle checks use normal window close; no browser automation or scraping was used.

## Platform limitation

Only Windows artifacts are built and verified. The existing macOS/Linux native workflows were blocked before execution by the GitHub account billing lock (run 37123272612). They require unlocked runners or native build machines. No unavailable installer links are presented as working downloads.

## Reproduce on Windows

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_updates.py -v
cargo test --manifest-path src-tauri/Cargo.toml
npm run check:ui
.venv\Scripts\python.exe -B scripts/build_backend.py
.\scripts\build_signed.ps1
.venv\Scripts\python.exe -B scripts/package_release.py
.venv\Scripts\python.exe -B scripts/smoke_backend.py dist/xea-backend.exe
# Close other instances before the isolated native test:
.venv\Scripts\python.exe -B scripts/smoke_desktop_lifecycle.py src-tauri/target/release/x-engagement-assistant.exe
```

Signing uses the existing OS-protected maintainer credentials. End users install the published setup file and need no development runtime.

## Files changed in this repair

- `app/paths.py`
- `app/updates.py`
- `docs/BUILD.md`
- `docs/RELEASE-NOTES.md`
- `docs/UPDATE-0.3.3.md`
- `docs/UPDATE-0.3.4.md`
- `docs/UPDATES.md`
- `package-lock.json`
- `package.json`
- `scripts/smoke_backend.py`
- `scripts/smoke_desktop_lifecycle.py`
- `src-tauri/Cargo.lock`
- `src-tauri/Cargo.toml`
- `src-tauri/src/backend_lifecycle.rs`
- `src-tauri/src/main.rs`
- `src-tauri/src/updates.rs`
- `src-tauri/tauri.conf.json`
- `tests/test_updates.py`
