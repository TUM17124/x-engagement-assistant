# Download and install Social Engagement

Choose your operating system. A download link saves an installer; it cannot silently install software without your operating system's approval. No Python, Node, Git or terminal is needed for the Windows installer.

| Platform | Download / availability | How to install |
| --- | --- | --- |
| Windows 10/11 x64 | [Download Windows installer](https://github.com/TUM17124/x-engagement-assistant/releases/latest/download/Social-Engagement-Command-Center-Setup.exe) | Open the downloaded setup file, approve installation, launch Social Engagement Command Center. |
| macOS Apple Silicon (M-series) | Not published yet; [check release assets](https://github.com/TUM17124/x-engagement-assistant/releases/latest) for `Social-Engagement-Command-Center-arm64.dmg` | Once available: open DMG, drag the app to Applications, then launch it. |
| macOS Intel | Not published yet; [check release assets](https://github.com/TUM17124/x-engagement-assistant/releases/latest) for `Social-Engagement-Command-Center-x64.dmg` | Once available: open DMG, drag the app to Applications, then launch it. |
| Linux Ubuntu/Debian x64 | Not published yet; [check release assets](https://github.com/TUM17124/x-engagement-assistant/releases/latest) for `Social-Engagement-Command-Center-x64.deb` | Once available: open the package in your system's software installer. Dependencies and an OS keychain are required. |
| Linux AppImage x64 | Not published yet; [check release assets](https://github.com/TUM17124/x-engagement-assistant/releases/latest) for `Social-Engagement-Command-Center-x64.AppImage` | Once available: enable execution in file Properties / Permissions, then open it. This is a portable app, not a system package installer. |

The app's Settings > Updates page checks actual release assets and enables direct links only for available installers. macOS/Linux native workflows exist, but on October 3, 2026 GitHub refused to start them because the repository owner's account is locked by a billing issue. These installers are not claimed to be built or tested. Resolve the GitHub billing lock or build on native machines using [the contributor instructions](DESKTOP-PLATFORMS.md).

## Why does Windows show a warning?

This project does not currently have a Windows Authenticode publisher certificate or established download reputation. SmartScreen may therefore show an unrecognized-app or unknown-publisher warning. This is different from the Tauri signature that the in-app updater verifies. Neither being open source nor having an updater signature is a guarantee that software is safe.

Download only from this repository's releases and check that the file is the one you intended. For a reputation-only SmartScreen warning, Windows may offer More info > Run anyway if you decide to trust it. Do not disable security globally. If Windows reports malware, a corrupt file, or your organization's policy blocks it, stop and investigate rather than assume it is a harmless reputation warning. [Microsoft explains signing and SmartScreen](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation).

## Why might macOS block it?

An app without Apple Developer ID signing/notarization may be blocked because macOS cannot verify the developer/notarization. After verifying the source, macOS may allow an app-specific exception through System Settings > Privacy & Security > Open Anyway. Do not disable Gatekeeper globally or use this for an app reported as malicious/damaged. Maintainers need Apple signing/notarization credentials for normal public distribution. [Apple's installation guidance](https://support.apple.com/102445).

## Why might Linux warn or refuse to run it?

A package downloaded outside your distribution repository may be described as third-party or untrusted. AppImages also require executable permission, and may require FUSE/GTK/WebKit support depending on the distribution. Use the file manager's permissions dialog rather than changing global security settings. A working OS keychain is required to save API credentials securely. [Official AppImage guide](https://docs.appimage.org/introduction/quickstart.html).

## Updating an existing installation

Save unfinished form edits. Open Settings > Updates > Check for updates, review the release, then approve Update. A complete signed release includes the installer, its `.sig`, `latest.json` and checksums. Publishing only an EXE does not enable the signed in-app update path. The updater preserves local data and creates a database backup before closing for installation. Network, disk, OS permissions and security software can still prevent an update; the app must show the error instead of claiming success.
