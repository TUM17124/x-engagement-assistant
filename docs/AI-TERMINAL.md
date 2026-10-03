# AI Terminal and automations

## Commands

| Area | Commands |
| --- | --- |
| Account | help, login, logout, status, accounts, connect x / facebook / instagram / linkedin / tiktok / youtube / threads |
| Discovery | scan feed, scan x (or another adapter), scan trends, search [x for] query, watched, watch @handle, unwatch @handle |
| Content | draft reply post-id, draft post about topic, generate ideas topic, summarize feed |
| Review | show drafts, show approvals, approve draft-id, publish draft-id |
| Schedule | schedule draft-id tomorrow 8am, schedule draft-id ISO-offset-time, cancel schedule id |
| Automation | show automations, pause automation id, resume automation id, delete automation id |
| Preferences | show memory, clear memory; visible editor under Brand Voice |
| Terminal | settings, clear, /search history-text, arrow-key recall, Copy Output, Stop |

Explicit schedule creates a **manual reminder proposal** by default. Natural language or GUI can request API delivery for supported originals. The card shows exact time, timezone, delivery, and content. Reddit has no adapter in this release and is reported unavailable.

## Execution

command_tools.py defines each tool's argument schema, permission category, timeout, local hourly limit, and automation eligibility. command_bus.py validates the complete plan before execution. No shell, eval, arbitrary HTTP, filesystem, token-reading, or confirmation tool is exposed to AI.

The model translates user commands. Retrieved posts do not enter a tool-execution loop. Summarization/drafting receive posts as untrusted data and have no executor. Public actions become database-backed proposals.

READ_ONLY and DRAFT tools may run directly. EXTERNAL_ACTION and DESTRUCTIVE tools need a separate UI confirmation. Requests are consumed once, and content must still match the snapshot. Existing draft approvals and daily write limits apply.

Commands and tool events are local SQLite records. A failed command may have completed earlier local steps; inspect output before retrying. Reusing a command UUID does not replay it.

## Natural language

The selected provider receives the user command, tool schemas, timezone, a few draft/watchlist identifiers, and visible preferences. Unknown tools, additional fields, and malformed arguments are rejected. Missing identifiers/times should produce clarification.

Recurring workflows have a narrow schema: daily or watch trigger, one platform, optional X query, account/topics, interval, and at most five drafts per run.

## Automation lifecycle

The existing Python worker process runs an asyncio automation loop beside the original scheduler. Runs claim persistent state before work; steps retain results. Interrupted work is not automatically replayed.

- active: eligible at its next time
- running: claimed by the worker
- waiting-for-approval: drafts ready; review and resume explicitly
- paused: user pause, usage issue, or interrupted run
- needs-auth: ChatGPT connection needs attention
- failed: inspect the run before resuming
- deleted: hidden from active workflows; history retained

Runs missed by more than 15 minutes are recorded and moved to their next occurrence. Keep the app running. Tray Pause stops future automation work and cooperatively stops a running workflow between operations.

Automations can only invoke selected read/draft tools. Publishing, approval, scheduling public content, logout, and deletion are not eligible steps.

## Runtime decision

Direct streamed Responses requests fit the existing Python provider layer. [Codex app-server](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server) was evaluated; its coding runtime/tools are unnecessary for this explicit application-tool registry. No Codex binary or extra Node agent runtime is bundled.

ChatGPT inference requests disable storage and enable streaming. Only response.completed indicates success. Failed/interrupted output is not saved as a completed draft. Cancellation closes the stream. Existing alternative providers retain their completion behavior: progress plus final text, not token-by-token streaming.

## Authentication boundary

The backend owns dynamic registration, loopback callbacks, JWT verification, refresh, revocation, and OS-vault storage. The renderer receives account metadata, states, and model names only. A stable UUIDv4 URI identifies the installation. Each saved account/workspace retains its own issued client ID and tokens.

Live acceptance still requires browser consent and completed inference with an eligible account. Mocked tests do not establish eligibility or real account access.


## Conversational control and typed confirmations

The terminal calls the same services as the GUI. Tool results include grounded readable feedback and expandable result details. It can inspect accounts, explain connection setup, start configured OAuth, navigate to screens, generate a weekly plan, import text, draft/edit/skip, prepare publishing or manual handoff, inspect schedules/history/analytics/media, save ideas and review changes to selected settings. File selection and credential entry remain in their dedicated secure GUI forms.

Examples:

    is Facebook connected?
    how do I connect fb
    connect facebook
    test x
    weekly plan
    show history
    show schedule
    show analytics
    show media
    open planner
    publish 12
    yes

A publishing request first displays the exact draft and selected account. Typing yes confirms only that one displayed request using its stored ID and content checksum. Typing no rejects it. A second yes cannot repeat the action. Editing the content or changing the connected account invalidates the preview. Multiple pending actions require their individual buttons; yes is not blanket permission. The model has no confirmation tool, and source posts cannot supply confirmation.

A confirmed publishing request now performs approval and publication together for that exact reviewed version. The separate approve command still only approves and never publishes. Only the user's explicit confirmation can invoke these actions.

Natural-language follow-ups receive recent user commands, assistant clarification messages, draft identifiers, watchlist metadata, and safe connection states. Retrieved post text is not inserted into command-routing instructions. The app gives connection guidance based on actual saved state; it does not claim that Facebook or another network is connected without credentials.

## Action errors and progress

All shared button/form action boundaries display a progress indicator and persistent, named error messages. Errors offer Settings and History links and expandable technical details. Field validation identifies the field; dropped connections and timeouts explain that an operation may have completed and must be checked before retrying. The app never automatically retries publishing. ChatGPT Plan and OpenAI API-key failures are labeled separately.

The weekly Planner uses dedicated planning instructions, the user's interests and topics, and seven local calendar dates. It saves its last successful result locally and keeps that result if generation fails. It never creates scheduled posts by itself.


## Work state and completion reports

A persistent Working indicator shows the active action, current step and elapsed time even when the user changes screens. Activity & Reports shows recent session outcomes. Terminal completion reports are also stored with terminal history.

Reports distinguish Completed, Waiting for approval, Stopped and Needs attention. They use actual service results rather than another AI call. New drafts explicitly say they are waiting for review in Response Inbox. Plans link to AI Planner; schedules link to Schedule; confirmed publications include post IDs and a History link. Reports suggest a next action but never execute that suggestion automatically. Network failure, missing completion and cancellation are not reported as success.

The UI clears stale Terminal action previews when a new command starts. A typed confirmation consumes the selected preview; multiple previews require individual confirmation buttons.


## Interactive conversation in 0.3.3

The prompt lives inside the conversation surface. Enter sends, Shift+Enter inserts a newline, and Ctrl+C (Command+C on macOS) stops an active command while the terminal is open. With no active command, normal copy behavior remains available. Single-line history uses Up/Down only at the text boundary; multiline cursor movement remains normal. The prompt is resizable and unsent text survives app navigation. Requests above 64,000 characters are rejected with an explanation, without silently truncating the editable input.

## Conversation and choices

The AI may ask a question and supply numbered options; choose a button, type its number, or type another response. After a draft, the app offers a publishing preview, continued editing, or keeping it for later. Choosing a publishing preview does not publish.

An exact action preview offers:

1. Yes: execute that exact reviewed action.
2. No: cancel that action.
3. Type changes: keep the action unexecuted while you describe what to change.

Only one selected preview can accept a plain yes/1. Multiple actions require their own confirmation buttons. The server verifies the request ID, checksum, current draft/account/settings and pending state. Changed or already-handled requests cannot execute again. Model suggestions cannot confirm actions. After navigating back, only a still-pending preview from the latest terminal result is restored.

## Application awareness

The selected AI provider receives the registered tool catalog and current non-secret metadata for local limits, Radar counts/interests, video configuration and pending drafts. Writing/conversation context follows the AI privacy settings. It does not receive API keys or social passwords. Local tips rotate while the terminal is idle; reading tips does not call AI or social APIs. AI-generated follow-up choices are based on the requested task and verified results.

Commands include:

- `show app state`, `accounts`, `is Facebook connected?`
- `scan trends` to refresh configured public APIs; `show trends` to read cached sources
- `trend report` to ask the selected AI for a grounded report on up to eight cached items
- `set radar interests to AI, programming` to review a settings change
- `show limits`, `set daily ai limit to 100` to review a local-cap change
- `video status`, `settings video`
- `generate video A peaceful forest scene` to review a potentially paid job
- `check video <job-id>`, `save video <job-id>`
- existing draft, profile, settings, X paid-search, watchlist, scheduling and approval commands

Radar reports cite retrieved evidence and do not claim to watch videos, hear audio or know worldwide growth. Source text is untrusted data. Scans use supported public/official APIs and their cache/backoff limits. Existing paid X searches still have separate costs. There is no unrestricted browser, shell or OS-root access. Background work runs as cancellable app tasks; persistent monitoring uses the existing review-first automation engine.

Limits can be reviewed and changed within existing bounds after confirmation. The app cannot increase a provider's account quota, remove its billing restrictions, turn off duplicate protection or bypass required approval. Video uses a separate configured provider/key; API-key entry stays in secure Settings. Video prompts require approval and may incur charges, and generated media is never automatically published.

## Verification

Mocked tests cover keyboard dispatch, multiline/history editing, numbered choices, exact approvals, stale previews, cancellation, local-state privacy, Radar configuration/reporting, source prompt injection and video generation approval. No real social post or paid video was used by these tests.
