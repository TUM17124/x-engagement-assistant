# X Engagement Assistant

**AI drafts. You decide.**

An open-source desktop workspace for founders, creators, developers, brands, and anyone who wants to join better conversations on X. Find relevant posts, prepare thoughtful replies, write original content, and keep every publishing decision in your hands.

## What you get

- **Less blank-page time:** contextual replies, original posts, threads, hooks, rewrites, and alternatives.
- **A focused engagement routine:** a mini feed, favorite-account watchlist, Topic Radar, and a scored Engagement Queue.
- **Control of your public voice:** review, edit, approve exact content, then publish or open X's manual reply composer.
- **Two discovery modes:** paid official X API search inside the app, or free manual X web search with copy/paste import.
- **Clear boundaries:** duplicate and similar-content checks, daily/hourly write limits, AI/search budgets, and repeated-author limits.
- **A local record:** activity history, draft acceptance rate, top engaged accounts/topics, and portable backups.

No promised growth numbers, fabricated impressions, scraping, or autonomous reply campaigns.

## Install and get started

Windows is the first supported desktop target. Download **X-Engagement-Assistant-Setup.exe** from a published release, or the **X-Engagement-Assistant-Windows** artifact in [Windows desktop builds](https://github.com/TUM17124/x-engagement-assistant/actions/workflows/windows.yml).

The installer bundles the Python backend/runtime. End users do **not** install Python, use a terminal, run uvicorn, or edit `.env`. Windows WebView2 is installed by the installer when needed; that step requires internet access.

1. Install and launch **X Engagement Assistant**.
2. Complete the six-step onboarding wizard.
3. Enter your own X and AI credentials in Settings.
4. Connect X in your system browser.
5. Add interests and favorite accounts.
6. Search/import a post, generate a draft, edit it, approve it, and choose how to reply.

You can skip X API connection and use manual discovery/replies. An AI endpoint is required for AI features.

## Discovery: paid API or free web search

**Settings -> X Connection -> Discovery Mode**

| Mode | Behavior |
| --- | --- |
| Automatic | On a requested search, tries the official API. Billing/access failures offer the same query on X.com. |
| X API Search | Uses `GET /2/tweets/search/recent` with your bearer token or OAuth credentials; results enter Feed. Access errors still offer a manual fallback. |
| X Web Search | Opens X.com search; no paid API search request is made. Paste a post back into Feed. |

Queries support boolean operators, language and author filters, exclusion of retweets/replies, and 10-100 maximum results. Returned author information and public metrics are displayed when provided.

The app shows API search availability, searches today, and posts retrieved today. A 402 is remembered: it is **not repeatedly retried**. After fixing access, use **Retest search access on next search**. Rate-limit backoff remains in force. No dollar-cost estimates are fabricated.

Background monitoring is **off by default**. Enabling it requires an explicit setting, a minimum 15-minute interval, and a daily search budget. The default interval is 30 minutes and default search cap is 20 per UTC day.

## Workspace screens

| Screen | Features |
| --- | --- |
| Home | Connection state, provider/model, waiting drafts, scheduled posts, today's writes, watchlist updates, and local analytics. |
| Feed | Official API results, watchlist/topic posts, manual imports, avatars/metrics when available, save/ignore, open on X, generate reply. |
| Engagement Queue | Original post, suggested reply, reason, relevance score, topic, edit/regenerate/style tools, skip, mute author/topic. AI can return SKIP. |
| Approval Center | Replies, originals, threads, quotes, and scheduled content. Editing clears approval. |
| Compose | Original post, thread, quote, saved draft; generation, rewriting, shortening, tone changes, hooks, alternatives, repetition review. |
| Schedule | Local-time queue and month calendar; approved original posts only; edit, cancel, publish now. |
| Watchlist | Account enable/disable, priority, topics, draft preparation, notification preferences, last-seen tracking, open latest posts on X. |
| Topic Radar | Keywords, exclusions, languages, priority, custom/AI-assisted queries, official API or manual search. |
| History | Generated vs final text, action, timestamp, post ID, account, provider/model, manual/API channel, status and errors. |
| Settings | X credentials/discovery, AI provider, Writing Voice, My Product, appearance/tray/notifications, safety, data and backup. |

Supported AI adapters: **Gemini**, **OpenAI**, **OpenAI-compatible API**, and **local Ollama**. Configure the provider and exact model identifier in the app. Credentials are kept separately per AI provider.

## Publishing and scheduling rules

- Generating, scoring, rewriting, and approving never publish.
- Publishing requires an explicit action after approval of the exact content.
- Replies are never bulk-sent or scheduled automatically.
- Only an explicitly approved and scheduled **original post** can publish automatically.
- Threads require approval of the entire thread. Partial failures are recorded and not automatically replayed.
- Editing cancels approval and an existing pending schedule.
- **The app must remain running for schedules.** Optional tray mode can keep it running when its window closes. No startup task/service is installed.
- Missed schedules are marked for review on restart. Interrupted sends are marked uncertain, never blindly retried.
- Manual composer opens are recorded as **opened**, not published. They do not inflate API write counts or success metrics.

## Privacy and credentials

Windows uses **DPAPI**, scoped to the current Windows user, for retrievable API credentials, session secrets, and OAuth tokens. Other platforms require a supported OS keychain; there is no plaintext fallback.

Secrets are masked after saving, can be revealed for 15 seconds, replaced, or deleted. They are not stored in SQLite, source files, logs, browser localStorage, or exports.

Windows data lives in `%LOCALAPPDATA%\XEngagementAssistant`. SQLite stores workspace content, metadata, and versioned migrations. Backups exclude secrets; restored drafts need fresh approval and restored schedules are cancelled.

Drafting sends source text and author plus your chosen writing/product context to your configured AI endpoint. Cloud AI is not local inference. API discovery and publishing communicate with X. See [secure configuration](docs/SECURITY.md).

To migrate the original developer app, use **Settings -> Data & Backup -> Migrate the original developer app** and select its engagement.db. History and available OAuth tokens are imported without overwriting an existing login. Keep the original file private; it may contain old plaintext tokens.

## Service limitations

X API read/write access, credits, rate limits, and reply permissions are controlled by X. AI access and credits are controlled by your AI provider. The app explains errors and offers manual discovery/reply alternatives; it does not bypass restrictions.

Local analytics describe this app's recorded activity, not follower growth or account-wide reach. Feed metrics are shown only when returned by X.

This is a **local single-user application**, not a hosted multi-user service. Windows packages are unsigned unless a maintainer configures code signing; Windows may show an unknown-publisher warning.

## Development and builds

Contributors need Python 3.13, Node.js, and (for desktop builds) Rust, the Microsoft C++ build tools/Windows SDK, and WebView2. End users do not.

```powershell
git clone https://github.com/TUM17124/x-engagement-assistant.git
cd x-engagement-assistant
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-build.txt
npm ci
git config core.hooksPath .githooks
uvicorn app.main:app --host 127.0.0.1 --port 8787 --reload --no-access-log
```

Open localhost:8787 for browser development. Configure in the UI. `.env` is optional for developers and is never loaded by packaged builds.

Desktop development / Windows installer:

```powershell
python scripts/make_icons.py
python scripts/build_backend.py
npm run desktop:dev
# Close the development app, then:
python scripts/collect_notices.py
npm run desktop:build
```

Do not leave a separate server running on port 8787 when launching the desktop shell. The shell owns its bundled backend. Installer output: `src-tauri/target/release/bundle/nsis/`.

Detailed instructions: [build and uninstall](docs/BUILD.md), [architecture](docs/ARCHITECTURE.md), [contributing](CONTRIBUTING.md), [screenshots](docs/screenshots/README.md).

## Tests

```powershell
python -B -m unittest discover -s tests -v
node scripts/check_ui.cjs
python -B scripts/secret_scan.py
```

External APIs are mocked and storage is isolated. Tests never publish real X posts. No browser automation is used.

## License

[MIT](LICENSE). Third-party components retain their own licenses; see [dependency licensing](docs/LICENSES.md).
