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
