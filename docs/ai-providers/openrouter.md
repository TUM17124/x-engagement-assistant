Last verified: 2026-10-03

# OpenRouter

| Research item | Finding |
|---|---|
| Authentication | Bearer API key or official browser PKCE exchange. Aggregator: underlying providers have separate data practices. |
| Base URL | `https://openrouter.ai/api/v1` |
| Generation API | `POST /chat/completions` |
| Model endpoint | `GET /models`; cached for six hours, Refresh Models bypasses cache |
| Streaming | SSE; cancellation closes the local HTTP stream |
| Structured output | Supported on eligible models; JSON/schema shapes differ by API |
| Vision | Model-dependent; missing model metadata is shown as unknown |
| Rate limits | Account/model dependent; 429 pauses work; no hidden retry loop |
| Error format | HTTP status plus provider-specific JSON or stream error events; bodies are not echoed or logged |
| Key setup | [Official setup](https://openrouter.ai/settings/keys) |
| Pricing | [Check current pricing](https://openrouter.ai/pricing); no hard-coded cost estimate |
| Free/trial | See current pricing/account terms; no permanent free label or guaranteed credits |
| Official documentation | [API documentation](https://openrouter.ai/docs/quickstart) |
| Data/privacy | [Provider policy](https://openrouter.ai/privacy) |
| OpenAI compatibility | Yes, documented compatibility; this adapter may use the native API. |
| OAuth / safer authorization | Official PKCE S256 implemented; manual API key also supported. |
| Recommended model | Choose from current discovery; no automatic expensive model selection |
| Deprecations / aliases | Refresh catalog; aliases are not immutable snapshots. See notes below. |

An aggregator: routing can involve different underlying providers and data policies. Catalog exposes modalities, supported parameters and pricing. PKCE S256 supports localhost callbacks on arbitrary ports and returns a user-controlled API key, not a consumer-session token. Health checks authenticate /key before reading the public catalog.

## Setup in Social Engagement

Settings ? AI Providers ? Configure ? open official setup page ? enter your key (optional for local servers) ? Test connection ? choose an available model ? Save provider ? Use as primary. Saved keys are masked and OS-encrypted. Replace by entering a new key; Delete key removes the local credential. Model-list tests consume no generated tokens but cannot guarantee inference credits.

## Sources and implementation limits

- [Official reference](https://openrouter.ai/docs/guides/overview/auth/oauth)
- [Official reference](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties)
- [Official reference](https://openrouter.ai/docs/api/api-reference/api-keys/get-current-api-key)
- [Official reference](https://openrouter.ai/docs/api_reference/errors-and-debugging)

Mocked adapter tests cover request/response contracts, streaming, authentication errors, billing/rate limits, timeouts, malformed responses and outages. They do not prove that a specific account has access. No real credentials or live credit-spending calls are part of the default test suite. Provider-level capability flags describe available API features, not a promise that every model supports them.
