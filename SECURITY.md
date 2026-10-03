# Security and responsible disclosure

Report security vulnerabilities privately through GitHub Security Advisories for this repository. Never include credentials, private databases, prompts, or complete OAuth callback URLs in public issues. If a credential has been exposed, revoke/rotate it; deleting a file does not remove Git history.

## Credentials

API keys remain retrievable because hashing cannot support API requests. Windows uses per-user DPAPI; macOS/Linux use supported OS keychains. There is no plaintext fallback. SQLite stores provider configuration and model metadata, not credentials. Saved keys are masked; replace/delete controls call the backend vault. Custom keys are bound to their configured endpoint in the vault. Redirects do not forward credentials. Known providers use fixed official endpoints.

The new OpenRouter PKCE flow opens the official site in the normal browser, uses S256, a random single-use callback path and five-minute expiry, and exchanges codes in the backend. The returned key never appears in callback HTML or renderer responses. Existing social OAuth and optional ChatGPT OAuth stay separate. Run development servers with access logging disabled to avoid recording OAuth callback query parameters.

## Data sent to AI

Requested source content, selected images and necessary instructions go to the selected provider. Writing Voice/Brand Voice, My Profile, My Product and conversation context can be disabled in AI Providers. Context preview shows enabled saved context; the selected source/brief/image is additional task input. The terminal includes minimal app state needed to route requested commands. External posts cannot approve actions or change permissions.

Local AI Only blocks cloud text, vision and image-generation routes and cloud fallback. Ollama remote aliases are checked using model metadata; unverifiable models are rejected. Local custom servers must be configured not to forward to cloud services; this application cannot attest arbitrary proxy internals. Social API and update connections are separate from AI inference.

## Logs, exports and deletion

Usage logging is optional and stores provider/model/feature/time/status plus tokens if returned. Full prompts are off by default; explicit prompt-history opt-in stores redacted text locally. API response bodies, validation inputs and keys are not echoed in error messages. AI Usage ? Clear removes usage and saved prompt history. Delete key removes the local vault credential; revoke at the provider if required. SQLite backups can contain private social content and optional prompt history, so keep them private.

Automatic fallback requires explicit opt-in and only handles temporary failures. Authentication, billing and permission problems never silently charge another provider. Existing approval protections and duplicate/write limits remain in force.

See [the existing security model](docs/SECURITY.md) for desktop isolation, approval and publishing details.


Public Trend Radar fetches only fixed official API hosts and bounded samples. Source HTML is reduced to text and escaped; it cannot run tools or approve actions. Media previews are opt-in and limited to approved source hosts, with no autoplay or embedded third-party scripts.

Video API keys and signed output URLs remain in the OS vault. Jobs store non-secret metadata, require an explicit potentially-paid request, never resubmit uncertain submissions, and never publish socially. Downloads have host/redirect checks, a 50 MB cap, and MP4 validation. No credentials are forwarded across storage redirects. Local AI Only blocks cloud video generation/downloads.

macOS/Linux use approved Keychain/Secret Service/KWallet backends and fail closed without a usable secure store. Isolated application-data directories get separate keychain namespaces, so packaged smoke tests cannot overwrite normal user credentials. See [desktop packaging](docs/DESKTOP-PLATFORMS.md) for platform-signing requirements.
