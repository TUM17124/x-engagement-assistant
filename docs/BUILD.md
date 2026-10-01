# Windows desktop build and lifecycle

## Contributor prerequisites

Windows 10/11 x64, Python 3.13, Node.js 22+, stable Rust with the MSVC target, Microsoft C++ build tools and Windows SDK, and WebView2.

See [Tauri prerequisites](https://v2.tauri.app/start/prerequisites/) and [Windows installers](https://v2.tauri.app/distribute/windows-installer/).

## Build

1. Create/activate a virtualenv and install `requirements-build.txt`.
2. Run `npm ci`.
3. Run `python scripts/make_icons.py`.
4. Run `python scripts/build_backend.py`.
5. Run `python scripts/collect_notices.py
npm run desktop:build`.

The backend step creates a self-contained sidecar named `src-tauri/binaries/xea-backend-x86_64-pc-windows-msvc.exe`. No system Python is needed by the resulting installer.

The Tauri build outputs an NSIS setup executable under `src-tauri/target/release/bundle/nsis/`. The Windows CI workflow copies it to `X-Engagement-Assistant-Setup.exe` and supplies a SHA-256 checksum.

Desktop development uses `npm run desktop:dev` after building the sidecar. Rebuild the sidecar after changing Python/UI code. For rapid browser development, use uvicorn instead; do not run both on port 8787 simultaneously.

## CI

The Windows desktop workflow runs Python tests, UI checks and a secret scan, bundles the backend, compiles Tauri, and uploads the installer/checksum. It can run on a push or manually from Actions. No X/AI credentials are required or supplied to CI.

## Installation and uninstall

The installer is per-user and includes application shortcuts and a standard Windows uninstaller. WebView2's bootstrapper runs only if needed. The app does not register startup tasks or services.

Uninstall through Windows Settings -> Apps. The program and shortcuts are removed. The uninstaller asks whether to delete workspace data and credentials; No is the default. After exporting anything you need, you can also remove `%LOCALAPPDATA%\XEngagementAssistant` to delete the database and DPAPI-encrypted credentials. Credentials from this directory are bound to that Windows user.

Do not sign releases with a key stored in the repository. Authenticode signing is a maintainer/release configuration step; unsigned development builds may trigger SmartScreen.

## Runtime behavior

One backend owns the workspace lock. The Tauri shell waits for its own private authenticated health endpoint before navigating to the UI. If startup remains on the loading page, check for a conflicting process on port 8787.

Closing the window quits unless the user enabled tray mode. Quit always stops scheduling. No catch-up burst runs on restart; missed schedules need explicit review.
