# Architecture

## Repository audit

Frontend: plain JavaScript/CSS with Jinja-served HTML, not React or Electron. Backend: Python/FastAPI. Desktop: Tauri 2 launches a PyInstaller-bundled sidecar and displays its loopback UI.

SQLite owns versioned migrations, drafts, approvals, schedules, history, usage, media metadata, and social account metadata. Secrets are separate: per-user DPAPI on Windows, supported OS keychains elsewhere.

Original X PKCE OAuth and official paid recent search remain present. Gemini, OpenAI, compatible servers, and Ollama remain AI adapters. Social providers cover X, Facebook Pages, Instagram professional, LinkedIn, TikTok, YouTube, and Threads with explicit implementation capabilities.

Existing asyncio workers handle approved-original scheduling and official API monitoring. Local mutations use session CSRF/origin checks; Tauri control uses a separate private runtime token.

## Extension

GUI, terminal, and automation editor call the validated command registry and existing services. ChatGPT adds an authentication service and provider, not another runtime. A temporary private loopback listener owns sign-in callbacks. The model never sees credentials or an unrestricted action executor.

## Modules

- chatgpt_auth.py: registration, browser authorization, JWT verification, account selection, vault, refresh, revocation.
- chatgpt_provider.py: account model catalog, streamed Responses inference, error states.
- chatgpt_routes.py: safe connection controls.
- command_tools.py: typed tools, categories, limits, service adapters.
- command_bus.py: explicit/natural parsing, validation, review requests, execution audit.
- terminal_routes.py: SSE, cancellation, history, GUI requests, confirmation.
- automations.py: daily/watch execution, bounded steps, persistence and recovery.
- static/terminal.js: terminal, ChatGPT controls, automation editor, action review.
- Existing workspace/social/media/search/providers/workers modules retain their responsibilities.

## Migrations

Version 5 added multi-social columns and account/watch/media tables. Version 6 added platform-aware action history and invalidated older approvals that lacked account/media context.

Version 7 adds terminal_commands, action_requests, automations, automation_runs, automation_steps, command_events, and application_memory. Existing saved AI provider settings remain; fresh installs prefer ChatGPT.

Restored drafts need approval, schedules are cancelled, action requests are rejected, and automations are paused.
