Last verified: 2026-10-03

# Anthropic Claude

| Research item | Finding |
|---|---|
| Authentication | API key (Bearer); anthropic-version required. Enterprise WIF/App Attest are separate integrations. |
| Base URL | `https://api.anthropic.com/v1` |
| Generation API | `POST /messages` |
| Model endpoint | `GET /models`; cached for six hours, Refresh Models bypasses cache |
| Streaming | SSE; cancellation closes the local HTTP stream |
| Structured output | Supported on eligible models; JSON/schema shapes differ by API |
| Vision | Model-dependent; missing model metadata is shown as unknown |
| Rate limits | Account/model dependent; 429 pauses work; no hidden retry loop |
| Error format | HTTP status plus provider-specific JSON or stream error events; bodies are not echoed or logged |
| Key setup | [Official setup](https://platform.claude.com/settings/keys) |
| Pricing | [Check current pricing](https://platform.claude.com/docs/en/about-claude/pricing); no hard-coded cost estimate |
| Free/trial | See current pricing/account terms; no permanent free label or guaranteed credits |
| Official documentation | [API documentation](https://platform.claude.com/docs/en/api/overview) |
| Data/privacy | [Provider policy](https://privacy.claude.com/en/articles/7996868-is-my-data-used-for-model-training) |
| OpenAI compatibility | Native Messages used; do not assume Chat Completions compatibility. |
| OAuth / safer authorization | BYOK/local access verified. No general consumer-subscription OAuth assumed; separately documented enterprise flows are not implemented. |
| Recommended model | `claude-haiku-4-5`, only if returned by discovery |
| Deprecations / aliases | Refresh catalog; aliases are not immutable snapshots. See notes below. |

Bearer is currently recommended; legacy x-api-key remains documented. Models list reports capabilities and pagination. Haiku 4.5 is the economical family in the reviewed catalog. Structured outputs use output_config.format on supporting models. WIF and App Attest require separate enterprise/platform setup; no general consumer login is implemented here.

## Setup in Social Engagement

Settings ? AI Providers ? Configure ? open official setup page ? enter your key (optional for local servers) ? Test connection ? choose an available model ? Save provider ? Use as primary. Saved keys are masked and OS-encrypted. Replace by entering a new key; Delete key removes the local credential. Model-list tests consume no generated tokens but cannot guarantee inference credits.

## Sources and implementation limits

- [Official reference](https://platform.claude.com/docs/en/manage-claude/authentication)
- [Official reference](https://platform.claude.com/docs/en/api/models/list)
- [Official reference](https://platform.claude.com/docs/en/models/overview)
- [Official reference](https://platform.claude.com/docs/en/api/errors)
- [Official reference](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)

Mocked adapter tests cover request/response contracts, streaming, authentication errors, billing/rate limits, timeouts, malformed responses and outages. They do not prove that a specific account has access. No real credentials or live credit-spending calls are part of the default test suite. Provider-level capability flags describe available API features, not a promise that every model supports them.
