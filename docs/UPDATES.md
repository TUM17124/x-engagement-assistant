# Updates and free release emails

## For users

Click **Updates** in the app's top bar, or open **Settings > Updates & Email**.

- **Check for updates** reads this repository's latest stable GitHub release.
- Review the version and release notes, then choose **Update**. Installation never starts merely because a release exists.
- The installed desktop app downloads the Windows installer, verifies its Tauri signature and signed version, backs up the local database, and closes for installation.
- Accounts, drafts and settings stay in the private application-data folder.
- Browser/developer sessions offer the same public installer download link.
- Optional background checks run at most every six hours while the app runs. No Git installation or GitHub token is required.
- Quota, connection, missing-release, interrupted-download and installation errors appear in the Updates screen. Checks use HTTP ETags, a persisted interval and rate-limit backoff.

Save unfinished form edits before installing. Scheduled actions require the app to be running; normal missed-run handling remains in effect during an update.

## Free email notifications, without sender setup

Choose **Get free email updates**. This opens Blogtrottr with the repository's public Atom release feed preselected. Enter your email on the provider's page and complete its signup, browser verification and confirmation email if requested.

No SMTP setup, API key, EmailJS account, GitHub account or hosted backend is needed from the user or project maintainer. The independent service watches the feed and sends mail even when this app is closed.

The free service is ad-supported. It controls delivery timing and verification. Its documented free polling interval for ordinary feeds is hourly; do not expect immediate mail. Unsubscribe from a link in its emails. This app does not collect email addresses, track verification, report fake subscription success or send test emails silently.

The hosted signup form was checked on 2026-10-02: the `subscribe` query preloads the feed. Email entry and any anti-abuse verification happen on the real provider page; the app does not bypass those checks. The provider's programmatic API is paid, so this integration uses its free public signup flow, not that API.

Sources: [Blogtrottr free plan and no-account signup](https://blogtrottr.com/about), [delivery and unsubscribe help](https://blogtrottr.com/help).

GitHub users can instead choose **Watch > Custom > Releases**, with email enabled in their GitHub notification settings. [GitHub release notifications](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

## Maintainer release process

An update is a tested compiled release, not `git pull` into an installed app. A locally rebuilt installer does not change an existing installation or the latest GitHub release. Every distributed change needs a new version and a published signed release. The Updates screen explicitly distinguishes equal published versions from a newer local build.

The first maintainer setup generates a password-encrypted signing key outside Git:
`%LOCALAPPDATA%\SocialCommandReleaseSigning\updater.key`.
Its password is protected by Windows DPAPI in the adjacent private vault. Only the public verification key is included in the app. Keep an independent secure backup of both release-signing credentials; losing them prevents future updates for existing installations.

1. Increment the version consistently in app/paths.py, package.json/package-lock.json, Cargo.toml/Cargo.lock and tauri.conf.json.
2. Update docs/RELEASE-NOTES.md and run tests.
3. Build the Python sidecar.
4. Build the signed desktop installer using scripts/build_signed.ps1.
5. Run scripts/package_release.py. It independently verifies the installer signature and version and creates the installer, signature, SHA256.txt and latest.json.
6. Commit/push the tested source.
7. Run scripts/publish_release.py to upload a draft release. Add --publish only when ready to publish the exact assets.

The publishing script refuses a dirty source tree, verifies the installer signature/version again, and requires its commit to exist on GitHub before uploading the complete asset set. It cannot repair a manually published EXE-only release; create a new version instead.

The publishing script uses the maintainer's existing Git Credential Manager authorization in memory and never prints credentials. It refuses to replace an already-public version. Users need no GitHub credentials for downloads.

Ordinary CI creates unsigned test installers using tauri.ci.conf.json and never receives signing keys. Trusted releases are signed and published on the maintainer's machine. This also permits releases when GitHub Actions runners are unavailable.

[Tauri updater documentation](https://v2.tauri.app/plugin/updater/).

## Signing distinction

Tauri's updater signature authenticates the downloaded artifact and its version. It is separate from a Windows Authenticode publisher certificate. This project does not yet have an Authenticode certificate, so Windows may show an unknown-publisher warning on first installation.
