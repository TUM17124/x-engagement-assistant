# Social Engagement Command Center

**Find useful conversations. Prepare thoughtful responses. Keep control of every public action.**

An open-source local desktop workspace for founders, creators, developers, and small teams. Originally X Engagement Assistant, it combines supported social accounts, a review inbox, content tools, and an application-only AI Terminal.

AI helps discover, summarize, rank, draft, and organize. You review, edit, and approve. There is no mass-reply, follow, like, or DM automation.

## Install and start

Windows is the first supported desktop target. Run the NSIS installer from a tested release/build, launch **Social Engagement Command Center**, and complete onboarding. End users do not install Python, Node.js, Rust, or Git and do not edit an environment file.

1. Choose **Continue with ChatGPT**, or explicitly select another AI provider.
2. Authorize in your normal browser. Return to the app and choose an available model.
3. Connect social accounts independently, or start with manual post import.
4. Add interests and watched accounts.
5. Open **AI Terminal**, enter **help**, and review drafts in Response Inbox / Approval Center.

This development release is unsigned. See [BUILD.md](docs/BUILD.md). A public installer exists only when it appears on the repository's Releases page.

## What you can do

- Discover X conversations through official paid API search, with a same-query free X web-search fallback.
- Import URLs and post text without paid read access.
- Review a unified feed and contextual AI response suggestions.
- Track favorite accounts, topics, and locally observed trends.
- Use natural language or explicit commands to operate the same services as the graphical interface.
- Prepare recurring, bounded discovery/drafting workflows that finish at human review.
- Write platform-specific posts, keep a local media library, and schedule approved originals or manual reminders.
- Track actual local actions, provider usage, drafts, and approval rates.
- Export settings without secrets, drafts, history, and a SQLite backup.

See [platform capabilities and limitations](docs/SOCIAL-PROVIDERS.md). API access, app review, account type, region, and platform charges affect individual features.

## Continue with ChatGPT

The app implements OpenAI's documented public-client flow for open-source/local applications. A stable installation ID lives in private app data. The backend opens OpenAI authorization in the system browser, uses dynamic registration on first connection, verifies identity, and keeps tokens in OS-protected storage.

**ChatGPT Plan: Enabled** appears only when the returned grant permits plan usage. Models come from the connected account's catalog. Inference uses streamed Responses requests. Saved account/workspace registrations stay separate. AI settings provides reconnect, account selection, sign out, and Manage Usage.

Eligibility and usage limits apply. App or account limits may stop inference. Open **Manage ChatGPT Usage**, then explicitly retry or choose another provider. The app never silently switches to paid API-key usage.

ChatGPT connection grants no access to ChatGPT conversations, memory, or social accounts. X API costs remain separate.

OAuth and inference contracts have automated mocked tests. On 2026-10-02 the installed Windows app also completed real browser authorization, received plan permission and the account model catalog, and streamed a completed terminal response. Eligibility and available models still depend on each account. See [verification details](docs/IMPLEMENTATION-REPORT.md).

Official references: [registration](https://developers.openai.com/siwc/token-sharing-open-source/sign-in), [accounts and refresh](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions), [models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference), [usage/error recovery](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery).

## Optional AI providers

Settings supports ChatGPT Plan, Gemini, OpenAI API key, an OpenAI-compatible endpoint, and local Ollama. Existing saved provider configuration is preserved. Enter keys in the UI; each provider's key is stored separately through the OS vault. Ollama needs a local server/model.

An environment file is an optional contributor mechanism. Source runs can import the existing AI_BASE_URL, AI_API_KEY, and AI_MODEL configuration once. Bundled builds never load .env.

## AI Terminal

This is an application command interface, **not CMD, PowerShell, Bash, or a code-execution shell**.

    help
    status
    accounts
    login
    scan x
    search "AI agents" lang:en -is:retweet
    watch @favoriteperson
    watched
    scan trends
    draft reply <imported-post-id>
    draft post about lessons from shipping a small product
    generate ideas accessible PDF editing
    show drafts
    show approvals
    approve 12
    schedule 12 tomorrow 8am
    show automations
    pause automation 3

Natural language uses the selected AI provider to produce a validated plan. For example:

> Every morning at 7 scan X for AI engineering discussions and prepare up to five replies.

The recurring workflow and its costs are shown for review before activation. That workflow cannot publish replies.

The terminal also explains connection setup, answers account-status questions, opens app screens and operates shared drafts, schedules, ideas, media metadata and analytics. After an exact action preview, type **yes** to confirm that single action or **no** to cancel. Editing the draft invalidates its preview. File uploads and credentials still use their dedicated GUI forms.

Commands stream progress and ChatGPT text. Stop cancels the operation; completed local work remains visible. Arrow keys recall history, /search searches it, and Clear clears the display. History stays local. Never paste credentials into the terminal.

[Full command reference](docs/AI-TERMINAL.md)

## Approval and scheduling

Drafting never publishes. Approval binds exact platform, target, text, selected account, and attached media context. Editing invalidates approval.

Terminal publishing, scheduling, automation activation, and destructive actions create review requests. A model cannot confirm its own request. GUI controls and terminal commands call the same underlying services.

The AI Planner creates a locally saved seven-day plan from your interests and available evidence. A plan is a suggestion, not a scheduled campaign.

Only explicitly approved original posts with a supported API path can publish on schedule. Replies/comments use manual reminders. Keep the app running or enable optional tray mode. No startup service is installed. Missed schedules require review; interrupted writes are not blindly retried.

Automations persist in SQLite, run bounded reads/drafting, and keep step/run history. They wait for review when drafts are ready. Resume explicitly after review or a connection/usage failure. Interrupted runs remain paused; missed runs do not produce catch-up bursts.

## Watchlist, trends, and memory

Watchlist monitoring uses official access and configured intervals. Some networks cannot monitor arbitrary creators; Open Original and manual import remain available.

Trend Radar compares counts in **your local retrieved/imported sample** across two 24-hour windows. It is not a global trend feed or virality prediction. Impressions and follower growth are never invented.

Writing Voice, Brand Voice, My Profile, and visible application preferences provide optional context. Inspect or clear this app's memory in Settings. Edits do not silently create hidden profiles.

## Media and backup

Upload supported PNG, JPEG, WEBP, GIF, or MP4 files to the local library. Crop/resize creates a derivative and preserves the original. Captions, alt text, tags, folders, favorites, and reuse are available. Optional vision assistance sends a resized image to the selected compatible provider after an explicit action. Image generation has a separate provider. The ChatGPT adapter currently handles text; image assistance requires a separately selected vision-capable provider.

API media publishing currently supports Facebook Page PNG/JPEG images. Other media publishing uses manual handoff. SQLite backups include media metadata, **not media files**; preserve/export files separately.

Data exports exclude the credential vault. Restored drafts need fresh approval, schedules are cancelled, and automations are paused.

## Troubleshooting

- **ChatGPT needs renewal:** reconnect the saved registration.
- **Plan usage disabled:** enable browser consent or explicitly choose another provider.
- **Usage limit reached:** Manage ChatGPT Usage; there is no paid fallback.
- **Model unavailable:** refresh the model list and select an offered model.
- **X 402 / no credits:** use Open Search on X; repeated automatic search retries stop.
- **Social permission denied:** check approved scopes/account type; use manual import meanwhile.
- **Missed schedule:** keep the app running and explicitly reschedule.
- **Loading screen:** quit another local instance that may own port 8787.

## Contributor development

The frontend is plain JavaScript/CSS served by FastAPI. Tauri wraps the local app and bundles Python. SQLite is the only database.

    py -3.13 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
    npm ci
    .\.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8787 --no-access-log

For tests and desktop development:

    .\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
    npm run check:ui
    .\.venv\Scripts\python.exe scripts/build_backend.py
    npm run desktop:dev

Do not run development and desktop servers on port 8787 simultaneously.

See [architecture](docs/ARCHITECTURE.md), [build instructions](docs/BUILD.md), [provider guide](docs/SOCIAL-PROVIDERS.md), [contributing](CONTRIBUTING.md), and [credential model](docs/SECURITY.md).

MIT licensed. Dependencies retain their own licenses; see [license notes](docs/LICENSES.md) and generated third-party notices.
