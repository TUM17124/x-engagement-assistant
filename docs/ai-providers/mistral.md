Last verified: 2026-10-03

# Mistral AI

| Research item | Finding |
|---|---|
| Authentication | Bearer API key. Select a current Small model for short, cost-sensitive drafting. |
| Base URL | `https://api.mistral.ai/v1` |
| Generation API | `POST /chat/completions` |
| Model endpoint | `GET /models`; cached for six hours, Refresh Models bypasses cache |
| Streaming | SSE; cancellation closes the local HTTP stream |
| Structured output | Supported on eligible models; JSON/schema shapes differ by API |
| Vision | Model-dependent; missing model metadata is shown as unknown |
| Rate limits | Account/model dependent; 429 pauses work; no hidden retry loop |
| Error format | HTTP status plus provider-specific JSON or stream error events; bodies are not echoed or logged |
| Key setup | [Official setup](https://console.mistral.ai/api-keys) |
| Pricing | [Check current pricing](https://mistral.ai/pricing/); no hard-coded cost estimate |
| Free/trial | See current pricing/account terms; no permanent free label or guaranteed credits |
| Official documentation | [API documentation](https://docs.mistral.ai/api) |
| Data/privacy | [Provider policy](https://legal.mistral.ai/terms/privacy-policy/) |
| OpenAI compatibility | Yes, documented compatibility; this adapter may use the native API. |
| OAuth / safer authorization | BYOK/local access verified. No general consumer-subscription OAuth assumed; separately documented enterprise flows are not implemented. |
| Recommended model | Choose from current discovery; no automatic expensive model selection |
| Deprecations / aliases | Refresh catalog; aliases are not immutable snapshots. See notes below. |

The docs recommend Small models for cost-sensitive work. Alias targets can change. Models metadata includes completion_chat, vision, context and aliases. Free Studio access is documented, but account limits and billing requirements still apply; the app promises no permanent free allowance.

## Setup in Social Engagement

Settings ? AI Providers ? Configure ? open official setup page ? enter your key (optional for local servers) ? Test connection ? choose an available model ? Save provider ? Use as primary. Saved keys are masked and OS-encrypted. Replace by entering a new key; Delete key removes the local credential. Model-list tests consume no generated tokens but cannot guarantee inference credits.

## Sources and implementation limits

- [Official reference](https://docs.mistral.ai/api/endpoint/models)
- [Official reference](https://docs.mistral.ai/models)
- [Official reference](https://docs.mistral.ai/getting-started/quickstarts/developer/first-api-request)

Mocked adapter tests cover request/response contracts, streaming, authentication errors, billing/rate limits, timeouts, malformed responses and outages. They do not prove that a specific account has access. No real credentials or live credit-spending calls are part of the default test suite. Provider-level capability flags describe available API features, not a promise that every model supports them.
