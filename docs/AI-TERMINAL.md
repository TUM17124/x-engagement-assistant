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
