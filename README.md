# Social Engagement Command Center

**Find useful conversations. Prepare thoughtful responses. Keep control of every public action.**

An open-source local desktop workspace for founders, creators, developers, and small teams. Originally X Engagement Assistant, it combines supported social accounts, a review inbox, content tools, and an application-only AI Terminal.

AI helps discover, summarize, rank, draft, and organize. You review, edit, and approve. There is no mass-reply, follow, like, or DM automation.

## Install and start

[**Download for Windows**](https://github.com/TUM17124/x-engagement-assistant/releases/latest/download/Social-Engagement-Command-Center-Setup.exe) ? [Release notes](https://github.com/TUM17124/x-engagement-assistant/releases/latest) ? [Source code](https://github.com/TUM17124/x-engagement-assistant)

Windows is the currently verified desktop target. Native macOS (Apple Silicon and Intel) DMG and Linux DEB/AppImage build workflows are included; see [platform packaging](docs/DESKTOP-PLATFORMS.md) for commands and release-signing requirements. These new native targets need runner validation before publishing. Run the NSIS installer from a tested release/build, launch **Social Engagement Command Center**, and complete onboarding. End users do not install Python, Node.js, Rust, or Git and do not edit an environment file.

1. Choose your AI provider: cloud BYOK, a local model, or a custom endpoint.
2. Follow the selected provider's setup guide: save your API key, use supported browser authorization, or connect a local server. Test the connection and choose a model.
3. Connect social accounts independently, or start with manual post import.
4. Add interests and watched accounts.
5. Open **AI Terminal**, enter **help**, and review drafts in Response Inbox / Approval Center.

The installer has a Tauri updater signature but does not yet have a Windows Authenticode certificate; Windows may show an unknown-publisher warning. See [BUILD.md](docs/BUILD.md).

[Downloads for Windows, macOS and Linux, plus installation-warning help](docs/INSTALLATION.md). The in-app Updates screen enables a platform download only when the official release actually contains its installer.

## Updates and free email alerts

Open **Updates** in the top bar to check GitHub releases, review notes, and approve installation. Updates preserve your local workspace and require no Git or terminal. Background checks are optional; nothing installs silently.

Choose **Get free email updates** to open the free Blogtrottr signup with our release feed prefilled. Enter your email there and complete its verification. No sender account or API key is needed. The service is ad-supported and sends updates even when the app is closed; this app does not collect your email. [Details and unsubscribe instructions](docs/UPDATES.md).

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

## Bring your own AI provider

**Social Engagement does not require one specific AI company.** Connect the AI provider you choose through **Settings ? AI Providers**. Add multiple connections, test access, discover models, save, then explicitly select your primary. No `.env` editing is needed. Providers are shown alphabetically.

| Provider | Cloud/Local | Setup | Model discovery | Status |
|---|---|---|---|---|
| Anthropic Claude | Cloud | [Setup](https://platform.claude.com/settings/keys) | Yes | Adapter + mocked tests |
| Cohere | Cloud | [Setup](https://dashboard.cohere.com/api-keys) | Yes | Adapter + mocked tests |
| DeepSeek | Cloud | [Setup](https://platform.deepseek.com/api_keys) | Yes | Adapter + mocked tests |
| Google Gemini | Cloud | [Setup](https://aistudio.google.com/apikey) | Yes | Adapter + mocked tests |
| Groq | Cloud | [Setup](https://console.groq.com/keys) | Yes | Adapter + mocked tests |
| Kimi | Cloud | [Setup](https://platform.kimi.ai/) | Yes | Adapter + mocked tests |
| LM Studio | Local | [Setup](https://lmstudio.ai/docs/developer/core/authentication) | Yes | Adapter + mocked tests |
| Mistral AI | Cloud | [Setup](https://console.mistral.ai/api-keys) | Yes | Adapter + mocked tests |
| Ollama | Local | [Setup](https://docs.ollama.com/api/authentication) | Yes | Adapter + mocked tests |
| OpenAI | Cloud | [Setup](https://platform.openai.com/api-keys) | Yes | Adapter + mocked tests |
| OpenRouter | Gateway | [Setup](https://openrouter.ai/settings/keys) | Yes | Adapter + mocked tests |
| Together AI | Gateway | [Setup](https://api.together.ai/settings/projects/~current/api-keys) | Yes | Adapter + mocked tests |
| xAI / Grok | Cloud | [Setup](https://console.x.ai/team/default/api-keys) | Yes | Adapter + mocked tests |
| Custom OpenAI-compatible | Cloud or local | Enter your endpoint | When server supports `/models` | Adapter + mocked tests |
| ChatGPT authorized plan | Cloud, optional | Official browser authorization | Account catalog | Existing integration retained |

Open **Help / Documentation** inside the app for setup, privacy, pricing and troubleshooting links, or read the [official research records](docs/ai-providers/README.md). Recommendations are checked against the live catalog; no model name is guaranteed permanent. Consumer chat subscriptions do not automatically grant API access. OpenRouter offers official browser PKCE authorization as well as manual keys.

Keys use the OS vault. Configure **Local AI Only**, context-sharing switches, request logging, optional fallback and per-feature provider/model choices in AI Providers. Fallback is off by default and may incur charges if you enable it. It never handles authentication, billing or permission errors by charging a different provider. Interrupted streams require an explicit retry. **AI Usage** shows returned token counts without inventing prices or saving prompts by default.

Optional contributor `.env` values are imported once. Existing AI_BASE_URL, AI_API_KEY and AI_MODEL values migrate with a private backup; original credentials/configuration are retained. Installed builds never read `.env`.

## AI Terminal

[Interactive terminal guide](docs/AI-TERMINAL.md).

This is an application command interface, **not CMD, PowerShell, Bash, or a code-execution shell**.

The prompt is an editable multiline part of the conversation. Enter sends; Shift+Enter adds a line; Ctrl+C stops an active command. Choose numbered options or type your own response. Exact action previews use 1/yes to confirm, 2/no to cancel, or 3 to describe changes. Context tips read local state without spending AI credits. `scan trends`, `trend report`, `set radar interests to AI, books`, `show limits` and `video status` use the same data and services as the GUI. Local safety-limit changes and potentially paid video generation require confirmation; platform billing and API restrictions cannot be overridden.

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

Commands stream progress and supported provider text. Stop cancels the operation; completed local work remains visible. Arrow keys recall history, /search searches it, and Clear clears the display. History stays local. Never paste credentials into the terminal.

[Full command reference](docs/AI-TERMINAL.md)

## Approval and scheduling

Drafting never publishes. Approval binds exact platform, target, text, selected account, and attached media context. Editing invalidates approval.

Terminal publishing, scheduling, automation activation, and destructive actions create review requests. A model cannot confirm its own request. GUI controls and terminal commands call the same underlying services.

The AI Planner creates a locally saved seven-day plan from your interests and available evidence. A plan is a suggestion, not a scheduled campaign.

Only explicitly approved original posts with a supported API path can publish on schedule. Replies/comments use manual reminders. Keep the app running or enable optional tray mode. No startup service is installed. Missed schedules require review; interrupted writes are not blindly retried.

Automations persist in SQLite, run bounded reads/drafting, and keep step/run history. They wait for review when drafts are ready. Resume explicitly after review or a connection/usage failure. Interrupted runs remain paused; missed runs do not produce catch-up bursts.

## Watchlist, trends, and memory

Watchlist monitoring uses official access and configured intervals. Some networks cannot monitor arbitrary creators; Open Original and manual import remain available.

Trend Radar combines public API source rankings with interest matching, media previews and review-only AI drafts. Its separate connected-feed section compares your locally imported sample across two 24-hour windows. Neither view claims global coverage or predicts virality; metrics are never invented.

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


### Profile and terminal controls (0.3.1)

Settings > My Profile saves a structured local profile: name, role, bio, industry, expertise, products, audience and goals. Optional fields can be empty. Saved values reload when Settings opens. Individual writing preferences remain separate.

The AI Terminal uses whichever AI provider you explicitly select. It can read and edit profiles, writing context, drafts, media metadata, topics, watchlists and local limits; create drafts, prepare schedules, inspect usage, and request approvals. It cannot reveal credentials, execute arbitrary code, bypass platform quotas or disable human approval. Deleting a local draft cancels its schedule and preserves activity/duplicate protection. Deleting an already-public post is not supported by this control; use the original platform.

Examples that work without an AI call:

```text
show profile
set profile bio to I build useful tools for creators
show settings
show limits
set daily ai limit to 100
save draft A useful observation about building in public.
edit draft 12 to Revised text for review.
check draft 12
delete draft 12
approve 12
publish 12
settings ai
connect grok
use claude
show topics
export drafts
```

Commands that change settings, approve publishing or delete items show the exact action first. Type `yes` only after reviewing one pending preview, or `no` to cancel. Natural language uses the same validated tools. A changed target invalidates its pending approval. Basic explicit commands continue to work when AI usage is exhausted.

Grok, Claude, Kimi and DeepSeek connect through official developer APIs in Settings > AI Provider. Follow the provider-console link, create a key, enter an available model, save and test. Keys use the existing OS-protected vault and remain separate for each provider. Claude also supports the optional workspace ID required by multi-workspace keys. These are API connections, not consumer subscription OAuth. Existing ChatGPT plan authorization is unchanged; fallback requires explicit configuration; billing/authentication failures never trigger it.

Official references: [xAI](https://docs.x.ai/developers/quickstart), [Claude authentication](https://platform.claude.com/docs/en/manage-claude/authentication), [Kimi](https://platform.kimi.ai/docs/overview), [DeepSeek](https://api-docs.deepseek.com/).

For local validation diagnostics, set `XEA_DEBUG_VALIDATION=1` in a developer session. Logs include only schema names, field names and error codes, never supplied values or credentials. See [profile/control implementation report](docs/PROFILE-CONTROL-REPORT.md) for exact changes and verification limits.


## Public Trend Radar and video creation

[Trend Radar](docs/TREND-RADAR.md) now reads official Mastodon, DEV/Forem, PeerTube and Hacker News APIs without X credentials. Filter by interests/source/media, inspect available video/audio, save evidence and ask your chosen AI provider for an original draft. Every result states its source and sample limits; drafts wait in Response Inbox.

[Video Generation](docs/VIDEO-GENERATION.md) has a separate Settings screen and Media Library workflow for Gemini Veo and xAI video APIs. Configure your own key/model, explicitly confirm generation charges, check persistent job status and save the resulting MP4 locally. Video generation never publishes automatically. No Sora adapter is offered because its API is officially shut down.

[Desktop platform guide](docs/DESKTOP-PLATFORMS.md): Windows EXE, macOS DMG (both architectures), Linux DEB/AppImage. Builds bundle the backend/runtime. macOS distribution needs maintainer signing/notarization, and Linux requires an unlocked OS keychain.
