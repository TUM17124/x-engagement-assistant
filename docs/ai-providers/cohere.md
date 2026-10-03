Last verified: 2026-10-03

# Cohere

| Research item | Finding |
|---|---|
| Authentication | Bearer API key. Trial and production keys have different limits. |
| Base URL | `https://api.cohere.ai` |
| Generation API | `POST /v2/chat` |
| Model endpoint | `GET /v1/models`; cached for six hours, Refresh Models bypasses cache |
| Streaming | SSE; cancellation closes the local HTTP stream |
| Structured output | Supported on eligible models; JSON/schema shapes differ by API |
| Vision | Model-dependent; missing model metadata is shown as unknown |
| Rate limits | Account/model dependent; 429 pauses work; no hidden retry loop |
| Error format | HTTP status plus provider-specific JSON or stream error events; bodies are not echoed or logged |
| Key setup | [Official setup](https://dashboard.cohere.com/api-keys) |
| Pricing | [Check current pricing](https://cohere.com/pricing); no hard-coded cost estimate |
| Free/trial | See current pricing/account terms; no permanent free label or guaranteed credits |
| Official documentation | [API documentation](https://docs.cohere.com/v2/reference/chat) |
| Data/privacy | [Provider policy](https://cohere.com/privacy) |
| OpenAI compatibility | Yes, documented compatibility; this adapter may use the native API. |
| OAuth / safer authorization | BYOK/local access verified. No general consumer-subscription OAuth assumed; separately documented enterprise flows are not implemented. |
| Recommended model | `command-r7b-12-2024`, only if returned by discovery |
| Deprecations / aliases | Refresh catalog; aliases are not immutable snapshots. See notes below. |

Native v2 Chat is used; the separate compatibility API is also documented. Model listing remains v1 and can filter chat models. Command R7B remains live in the reviewed catalog; command-r and command-light aliases were deprecated. Trial keys are evaluation access, distinct from production limits.

## Setup in Social Engagement

Settings ? AI Providers ? Configure ? open official setup page ? enter your key (optional for local servers) ? Test connection ? choose an available model ? Save provider ? Use as primary. Saved keys are masked and OS-encrypted. Replace by entering a new key; Delete key removes the local credential. Model-list tests consume no generated tokens but cannot guarantee inference credits.

## Sources and implementation limits

- [Official reference](https://docs.cohere.com/v2/reference/list-models)
- [Official reference](https://docs.cohere.com/v2/reference/chat-stream)
- [Official reference](https://docs.cohere.com/docs/models)
- [Official reference](https://docs.cohere.com/docs/rate-limits)
- [Official reference](https://docs.cohere.com/docs/compatibility-api)
- [Official reference](https://docs.cohere.com/v2/docs/retrieval-augmented-generation-rag)

Mocked adapter tests cover request/response contracts, streaming, authentication errors, billing/rate limits, timeouts, malformed responses and outages. They do not prove that a specific account has access. No real credentials or live credit-spending calls are part of the default test suite. Provider-level capability flags describe available API features, not a promise that every model supports them.
