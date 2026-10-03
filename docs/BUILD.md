# Windows desktop build

## Build-machine prerequisites

Windows 10/11 x64, Python 3.13, Node.js 22+, stable Rust/MSVC, Visual Studio C++ Build Tools and Windows SDK. End users need none of these development tools. The installer bootstraps WebView2 if missing.

## Exact commands

From the repository root in PowerShell:

    py -3.13 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
    npm ci
    .\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
    npm run check:ui
    .\.venv\Scripts\python.exe scripts/make_icons.py
    .\.venv\Scripts\python.exe scripts/build_backend.py
    cargo metadata --manifest-path src-tauri/Cargo.toml --format-version 1 > $null
    .\.venv\Scripts\python.exe scripts/collect_notices.py
    npm run desktop:build -- --config src-tauri/tauri.ci.conf.json

If Rust was installed during the current shell session:

    $env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"

The backend output is src-tauri/binaries/xea-backend-x86_64-pc-windows-msvc.exe. It contains Python and dependencies.

The installer output is:

    src-tauri/target/release/bundle/nsis/Social Engagement Command Center_0.3.3_x64-setup.exe

Verify the sidecar with isolated data and no external API calls:

    .\.venv\Scripts\python.exe scripts/smoke_backend.py src-tauri/binaries/xea-backend-x86_64-pc-windows-msvc.exe

Desktop development:

    npm run desktop:dev

Rebuild the sidecar after Python/UI edits. For quick browser development:

    .\.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8787 --no-access-log

Do not run both servers simultaneously on port 8787.

## Lifecycle

Tauri owns the backend child process, waits for a private health check, then displays the loopback UI. Closing quits unless tray mode is enabled. Quit stops scheduling/monitoring. No startup task/service is installed.

Installation is per-user. Uninstall through Windows Settings. The uninstaller asks whether to remove local data; keeping it is the default. Data and DPAPI credentials remain in %LOCALAPPDATA%\XEngagementAssistant, preserving the original upgrade path.

Builds are unsigned unless the maintainer configures Authenticode. Packaging does not establish platform app-review approval or ChatGPT eligibility.

## CI

.github/workflows/windows.yml runs mocked tests/UI checks and builds artifacts. GitHub Actions previously could not obtain a runner because of the account's billing/lock state. Local build results are independent of that restriction.

See [Tauri prerequisites](https://v2.tauri.app/start/prerequisites/) and [Windows installers](https://v2.tauri.app/distribute/windows-installer/).


## Signed public installer

The commands above build an unsigned development installer. The release maintainer uses:

    .\.venv\Scripts\python.exe -B scripts/setup_update_key.py
    .\.venv\Scripts\python.exe -B scripts/build_backend.py
    .\scripts\build_signed.ps1
    .\.venv\Scripts\python.exe -B scripts/package_release.py
    .\.venv\Scripts\python.exe -B scripts/smoke_backend.py src-tauri/binaries/xea-backend-x86_64-pc-windows-msvc.exe

Commit and push the tested source, then upload a draft or publish the release:

    .\.venv\Scripts\python.exe -B scripts/publish_release.py
    .\.venv\Scripts\python.exe -B scripts/publish_release.py --publish

Signing keys live outside the repository, with an encrypted private key and an OS-protected password. Do not regenerate the key for an established product or replace published version assets. Forks must change the repository URLs and signing identity before distributing their own builds.

See [Updates and release process](UPDATES.md).


## macOS and Linux

Native macOS (Apple Silicon and Intel) DMG and Linux DEB/AppImage builds are described in [DESKTOP-PLATFORMS.md](DESKTOP-PLATFORMS.md). The repository includes separate native CI runners, Python sidecars, platform icons and secure-keychain smoke tests. Do not distribute a cross-platform artifact until its native build and runtime checks pass.
