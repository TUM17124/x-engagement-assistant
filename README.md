# X Engagement Assistant

**Turn an X conversation into a reply you can review, edit, and publish.**

X Engagement Assistant is an open-source, local dashboard for founders, creators, and anyone who wants a more deliberate way to join conversations on X. Find a post on X, paste its URL and text, generate a contextual draft with your chosen AI model, and decide what to send.

Built with Python and FastAPI. Runs on your computer. Licensed under the [MIT License](LICENSE).

## What you get out of it

- **Less time staring at a blank reply box.** Start from an AI-generated response grounded in the post you pasted, then make it your own.
- **A simpler path from discovery to participation.** Search, draft, edit, and choose a reply or quote without maintaining a separate drafting workflow.
- **Control over your public voice.** Nothing is published by generating or regenerating a draft. You choose whether to reply, quote, publish an original post, or skip.
- **No paid X recent-search dependency.** Discovery opens normal X.com search in a new tab. There is no call to the X API recent-search endpoint and no search bearer token to configure.
- **A usable draft even when API replies fail.** Your edited text stays available, with a button to open X's reply composer and send it yourself.
- **A record of successful API activity.** Local history, duplicate-text blocking, and a daily write cap help you keep track of what the app has published.

These are workflow benefits, not promises of followers, impressions, leads, or revenue. The quality and relevance of the conversations still depend on you.

## The workflow

```text
Open X Search -> find a post -> copy its URL and text
    -> paste into Draft from X Post -> Generate Reply
    -> edit -> Try API Reply / Quote Post / Reply Manually on X / Skip
```

1. Enter a search query and click **Open X Search**. For example:

   ```text
   ("PDF editor" OR "PDF reader" OR ebook) lang:en -is:retweet
   ```

2. Find a relevant post on X and copy its link and text.
3. Paste the link into **Draft from X Post**. The app extracts the author username and tweet ID locally; paste the post text and adjust the author if needed.
4. Click **Generate Reply** to use the AI endpoint and model configured in your `.env`.
5. Edit the draft. Choose **Try API Reply**, **Quote Post**, **Reply Manually on X**, **Regenerate**, or **Skip**.

**Try API Reply**, **Quote Post**, and the original-post **Publish** button send when clicked. **Reply Manually on X** opens a composer where you review and send on X.

## Features

| Feature | What it does |
| --- | --- |
| X web search | Opens your query on X.com in a new tab, including filters you type. |
| Draft from X Post | Accepts a tweet URL, pasted text, and author username. No post fetching or scraping. |
| Automatic URL parsing | Extracts the username and tweet ID from normal `x.com/username/status/123456789` links; also accepts supported Twitter-domain links. Invalid URLs show a clear error. |
| Configurable AI drafting | Uses `AI_BASE_URL`, `AI_API_KEY`, and `AI_MODEL` with an OpenAI-compatible chat-completions endpoint, including a compatible Gemini setup. |
| Editable reply drafts | Shows a reply textarea with a character counter and a 280-character editing limit. |
| Regenerate and skip | Request another draft from the same source, or move on without publishing. |
| API reply attempt | Sends a reply with your connected X account when you explicitly choose it. Failed replies are not automatically retried. |
| Quote publishing | Publishes your edited text as a quote of the selected post. |
| Manual reply on X | Opens X's official reply intent with the parsed tweet ID and your edited text. |
| Original posts | Write and publish an original post from the dashboard. |
| OAuth login | Connects your X account using OAuth 2.0 PKCE and supports token refresh and disconnect. |
| Local activity history | Displays the most recent successful API posts, quotes, and replies. |
| Duplicate protection | Blocks matching text already recorded in local history, after trimming surrounding whitespace. |
| Daily write counter | Counts successful API writes by UTC date; the default local cap is 100. |
| Error recovery | Preserves source input on drafting errors and preserves the edited draft when an API reply or quote fails. |
| Dark dashboard | A simple responsive interface served locally by FastAPI. |

## What runs locally, and what leaves your computer

The dashboard and SQLite database run on your computer. The database stores OAuth tokens and local activity, so treat it as private.

- **Search:** your query goes to X.com in the browser tab you open.
- **Drafting:** the pasted post text and author, plus the app's drafting instructions, go to your configured AI endpoint. The source URL, OAuth credentials, and local activity history are not included in the drafting payload.
- **X account and API actions:** OAuth, account lookup, token refresh, and explicitly approved publishing communicate with X.
- **Manual replies:** the selected tweet ID and edited reply text are passed to the X composer in your browser.

You can use a compatible local AI endpoint if you want drafting inference to stay on your machine. Cloud model providers receive the drafting content you submit to them.

The app uses no Selenium, Playwright, scraping, browser automation, scheduled engagement, or automatic reply loop.

## Quick start

Use Python 3.10 or newer. The project has been checked locally with Python 3.13. Node.js is optional for the JavaScript regression check; the app itself does not require it.

### 1. Clone and install

Windows PowerShell:

```powershell
git clone https://github.com/TUM17124/x-engagement-assistant.git
cd x-engagement-assistant
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

macOS / Linux:

```bash
git clone https://github.com/TUM17124/x-engagement-assistant.git
cd x-engagement-assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Configure drafting and the local session

Edit `.env`:

| Setting | Purpose |
| --- | --- |
| `AI_BASE_URL` | Base URL of your OpenAI-compatible endpoint; the app appends `/chat/completions`. |
| `AI_API_KEY` | Provider API key, if your endpoint requires one. |
| `AI_MODEL` | Exact model identifier accepted by that endpoint. |
| `SESSION_SECRET` | A random secret used to sign the local browser session. |
| `DEFAULT_QUERY` | Optional default text for X web search. |

Generate a session secret and paste the result into `SESSION_SECRET`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

If you already have a working AI configuration, keep it. The model must be available to your provider account. Missing configuration and provider errors appear in the dashboard; the app does not silently substitute canned replies.

### 3. Configure X OAuth for API publishing

You can search on X and generate drafts without connecting an X account to this app. To publish through the API, configure your X Developer App:

1. Enable OAuth 2.0. Use a web/confidential client if your setup has a client secret.
2. Register the exact callback `http://127.0.0.1:8787/auth/callback`.
3. Allow the scopes `tweet.read`, `tweet.write`, `users.read`, and `offline.access`.
4. Set `X_CLIENT_ID`, `X_CLIENT_SECRET` when applicable, and `X_REDIRECT_URI` in `.env`.

No `X_BEARER_TOKEN` is required. Posting uses your OAuth user access token.

### 4. Run the dashboard

From the project directory, with the virtual environment active:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8787 --reload
```

Open [http://127.0.0.1:8787](http://127.0.0.1:8787). Click **Connect X account** when you want API publishing.

## Costs and limits

- **The source code is free under MIT.** External AI services and X API access may still require payment, credits, or suitable permissions. Removing paid API search does not make every external service free.
- **AI billing is separate from X billing.** An HTTP 402 while generating a draft comes from the configured AI provider; check that provider's credits and billing. A 429 may indicate rate or quota limits.
- **X can reject API replies or other writes.** The app displays the failure and does not bypass X restrictions. If a send has an uncertain result, check X before retrying to avoid a duplicate.
- **Manual sends are outside local tracking.** The app cannot observe whether you sent a reply in X's composer. Those replies do not enter local history, duplicate checks, or the daily counter.
- **The local cap counts successful API writes, not drafts.** Search, drafting, and regeneration do not increment it. Change `daily_write_cap` in `app/config.py` if needed. This local safeguard is not a replacement for provider rate limits.
- **This is a local, single-user tool.** Run it on localhost; it is not designed as a public, multi-user hosted service.

## Development and checks

With the virtual environment active:

```bash
python -B -m unittest discover -s tests -v
```

The regression suite uses temporary storage and mocked X/AI requests. It checks dashboard rendering, URL validation, drafting and regeneration, error recovery, manual reply URL construction, API write logging, duplicate protection, and the daily cap. Tests do not publish real posts. The JavaScript check runs when Node.js is available.

Main files:

```text
app/main.py             FastAPI routes and approval-driven actions
app/drafting.py         Configured AI request and reply handling
app/post_urls.py        Local tweet URL parsing
app/x_api.py            X OAuth, account lookup, and API publishing
app/storage.py          Local OAuth tokens and activity storage
app/config.py           Environment settings and local write cap
app/templates/          Dark dashboard and editable draft screens
tests/test_workflow.py  Isolated regression tests
.env.example            Safe configuration template
```

## Contributing

Issues and pull requests are welcome. Describe the problem and the outcome your change improves. Keep publishing explicit, preserve the local workflow, and run the regression suite before submitting a change. Use mocked services for tests; do not publish real tweets to exercise a test.

Never commit `.env`, API keys, OAuth tokens, or the local database. The included `.gitignore` excludes environment files, SQLite databases, virtual environments, Python caches, logs, and common local editor files. Only the empty `.env.example` template belongs in the repository.

## License

[MIT](LICENSE). You can use, modify, and distribute this project under the license terms.
