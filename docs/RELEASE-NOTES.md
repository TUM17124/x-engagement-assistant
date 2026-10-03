# Social Engagement Command Center 0.3.4

A local, open-source social engagement workspace. AI prepares content; you approve public actions.

## Update repair

The live 0.3.1-to-0.3.3 update exposed an orphaned PyInstaller child holding the backend executable open. The launcher could be replaced while the backend stayed old. The native app now waits for actual process exit, stops only its owned process tree if graceful shutdown times out, and refuses installation while the backend file remains locked. Quit uses the same cleanup. Old cached release metadata is refreshed to load the platform download catalog.

Users on older builds who encounter this issue should quit the app and use the verified Windows installer. This shutdown repair takes effect once 0.3.4 is installed.

## What changed

- Provider-neutral AI settings with official signup/setup links, secure keys, model discovery and clear distinctions between API keys, local models and supported browser authorization. Includes OpenRouter PKCE and preserves existing ChatGPT connections. Other providers do not gain consumer-subscription sign-in merely by appearing in the catalog.
- Support for Claude, Cohere, DeepSeek, Gemini, Groq, Kimi, LM Studio, Mistral, Ollama, OpenAI, OpenRouter, Together, xAI and custom compatible APIs. Local-only mode, optional fallback, context controls and per-feature models.
- Expanded Trend Radar using Mastodon, DEV/Forem, PeerTube and Hacker News public APIs, with interest filters, opt-in media previews and AI drafts awaiting review.
- Separate Video Generation settings for Gemini Veo and xAI, secure credentials, explicit paid-job approval, persistent jobs and local MP4 downloads.
- Profile/settings save receipts and terminal feedback improvements.
- Integrated editable multiline AI Terminal: Enter sends, Shift+Enter inserts a line, Ctrl+C stops. Numbered approval/follow-up choices, rotating local-context tips, real Radar scans/reports, reviewable interest changes, limits and video setup guidance. The terminal still uses registered tools; it has no unrestricted OS or arbitrary web access.
- Update screen explains the installed version versus published releases. Local source edits are not automatically installed. This release has a new version so installed 0.3.1 applications can discover it.
- macOS/Linux build configurations and native CI; those installers are not included in this Windows release and still require native verification.

Existing X OAuth, paid X search, free web-search fallback, manual imports, approvals, scheduling and history remain available. No real social posts or paid video jobs were sent during testing. Provider adapters are mock-tested; API access and credits still depend on your own account. Live PeerTube/Hacker News reads passed; Mastodon/DEV live reads could not be verified in the build environment.

## Windows update

Use Settings > Updates > Check for updates, then approve Update to 0.3.4. The desktop updater downloads and verifies the signed installer, backs up your local database, installs and restarts. Save unfinished edits first. Accounts and drafts remain in the application-data directory.

[Download Windows installer](https://github.com/TUM17124/x-engagement-assistant/releases/latest/download/Social-Engagement-Command-Center-Setup.exe)

End users do not need Python, Node, Git or .env editing. Updater signatures are separate from Windows Authenticode; the installer may display an unknown-publisher warning. No update can guarantee success through network, disk or permission failures; errors remain visible and a verified installer download is available as a fallback.
