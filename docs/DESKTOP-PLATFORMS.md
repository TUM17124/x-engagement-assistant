# Windows, macOS and Linux builds

The existing Tauri shell bundles a native PyInstaller backend and Python runtime. End users do not install Python, Node, Rust or Git. Build on the target OS/CPU; a Windows backend cannot run on macOS/Linux.

| Target | Bundle | Build workflow |
| --- | --- | --- |
| Windows x64 | NSIS `.exe` | `.github/workflows/windows.yml` |
| macOS Apple Silicon | `.app` + `.dmg` | `unix-desktop.yml`, macos-15 / aarch64-apple-darwin |
| macOS Intel | `.app` + `.dmg` | `unix-desktop.yml`, macos-15-intel / x86_64-apple-darwin |
| Linux x64 | `.deb` + `.AppImage` | `unix-desktop.yml`, Ubuntu 22.04 |

Native CI runs mock tests, UI checks, packaged-backend smoke and installer builds, then uploads artifacts plus checksums. It does not publish a release. The macOS/Linux workflows were added from Windows; their actual build/runtime results must be checked on those runners before release.

## Contributor commands

Install [Tauri native prerequisites](https://v2.tauri.app/start/prerequisites/), Python 3.13, Node 22 and Rust stable. Then, in the repository:

```sh
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-build.txt
npm ci
python -B -m unittest discover -s tests -v
npm run check:ui
python scripts/make_icons.py
python scripts/build_backend.py
python scripts/collect_notices.py
```

Build local/test installers without updater-signing credentials:

```sh
# Windows
npm run desktop:build -- --config src-tauri/tauri.ci.conf.json
# macOS (run natively on each CPU)
npm run desktop:build -- --config src-tauri/tauri.macos.conf.json --config src-tauri/tauri.ci.conf.json
# Linux
npm run desktop:build -- --config src-tauri/tauri.linux.conf.json --config src-tauri/tauri.ci.conf.json
```

Artifacts are under `src-tauri/target/release/bundle`. `python scripts/package_checksums.py` copies native installers with stable architecture-specific names into `artifacts` and writes SHA256 checksums. Development: `npm run desktop:dev` after building the matching backend, or `.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8787 --no-access-log` for web development (`.venv/Scripts/python.exe` on Windows).

## Signing and release

CI test builds are not notarized public releases. For normal macOS distribution, the maintainer must supply an Apple Developer signing identity/certificate and notarization credentials following [Tauri's official signing guide](https://v2.tauri.app/distribute/sign/macos/). Set `APPLE_SIGNING_IDENTITY` before packaging the backend so PyInstaller signs its embedded native libraries. Tauri must use the same identity. The checked-in entitlements enable Python native runtime loading. Never commit signing keys. Gatekeeper may block unnotarized downloads.

For signed app updates, supply `TAURI_SIGNING_PRIVATE_KEY` and `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` securely and omit the CI config. Publish the platform-specific installer plus signed updater artifact (`.app.tar.gz` on macOS, `.AppImage` on Linux, setup `.exe` on Windows) and a correctly generated multi-platform `latest.json`. Keep one existing updater trust key. A matching release is offered only when it contains the native download and signature metadata. These new platforms have not been published by this change.

Linux requires a working Secret Service/KWallet desktop keychain; no plaintext fallback is provided. DEB declares GNOME Keyring as a dependency. AppImage users need the desktop's keychain service and compatible WebKit/GTK/FUSE support. See [AppImage requirements](https://v2.tauri.app/distribute/appimage/). Linux distribution compatibility needs native testing.

## Data and uninstall

Data stays in the existing per-user application-data folder: LocalAppData on Windows, `~/Library/Application Support/XEngagementAssistant` on macOS, and `$XDG_DATA_HOME/XEngagementAssistant` (default `~/.local/share`) on Linux. Existing profiles remain. Uninstall through the OS (remove the macOS app, uninstall the DEB, or remove the AppImage); local data is retained deliberately. Clear local workspace and delete saved provider keys from Settings before uninstalling if desired. No startup service is installed.
