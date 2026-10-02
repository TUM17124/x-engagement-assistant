# Social Engagement Command Center 0.3.1

A local, open-source AI engagement workspace. Discover relevant conversations, prepare thoughtful replies and content, and review every public action.

## Install on Windows

[Download the Windows installer](https://github.com/TUM17124/x-engagement-assistant/releases/latest/download/Social-Engagement-Command-Center-Setup.exe)

Run the installer, launch the app, and complete onboarding. No Python, Git, Node.js, terminal, or .env editing is needed.

## New in this release

- Fixed My Profile saving: dedicated validated profile API, optional fields, persistence and a clear ?Profile saved? result.
- Broader typed terminal controls for settings, safety limits, profile, drafts, topics, watchlists, media and approvals. Destructive changes require confirmation.
- Grok, Claude, Kimi and DeepSeek official API provider options with secure per-provider keys. Consumer subscription sign-in is not implied.
- Updates button and Settings > Updates & Email.
- Published GitHub release checks with download progress and explicit install approval.
- Tauri-signed updater artifacts with version-bound signatures, plus a private database backup before updating.
- Free release-email signup through Blogtrottr: no API key, sender setup or GitHub account. The provider asks for your email and verification; its free plan contains ads.
- Persistent AI Terminal work status, completion reports, next-step links and exact yes/no approvals.
- Dedicated weekly AI Planner and clearer connection, quota, validation and network errors.

Existing X OAuth, paid X search and free web fallback, manual imports, AI providers, approval workflows, scheduling, media, history and local analytics remain available.

The Windows executable does not yet have a commercial Authenticode certificate; Windows may show an unknown-publisher warning. Updater signatures verify our release artifacts and are separate from Windows publisher reputation.

AI and social API eligibility, quotas and charges remain separate. No social actions are sent during update checks. Installing closes the app briefly; scheduling requires the app to be running.

[Source code and documentation](https://github.com/TUM17124/x-engagement-assistant)
