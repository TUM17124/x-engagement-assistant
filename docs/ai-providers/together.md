Last verified: 2026-10-03

# Together AI

| Research item | Finding |
|---|---|
| Authentication | Bearer API key. Model catalog includes pricing and context metadata. |
| Base URL | `https://api.together.ai/v1` |
| Generation API | `POST /chat/completions` |
| Model endpoint | `GET /models`; cached for six hours, Refresh Models bypasses cache |
| Streaming | SSE; cancellation closes the local HTTP stream |
| Structured output | Supported on eligible models; JSON/schema shapes differ by API |
| Vision | Model-dependent; missing model metadata is shown as unknown |
| Rate limits | Account/model dependent; 429 pauses work; no hidden retry loop |
| Error format | HTTP status plus provider-specific JSON or stream error events; bodies are not echoed or logged |
| Key setup | [Official setup](https://api.together.ai/settings/projects/~current/api-keys) |
| Pricing | [Check current pricing](https://www.together.ai/pricing); no hard-coded cost estimate |
| Free/trial | See current pricing/account terms; no permanent free label or guaranteed credits |
| Official documentation | [API documentation](https://docs.together.ai/reference/chat-completions) |
| Data/privacy | [Provider policy](https://docs.together.ai/docs/privacy-and-security) |
| OpenAI compatibility | Yes, documented compatibility; this adapter may use the native API. |
| OAuth / safer authorization | BYOK/local access verified. No general consumer-subscription OAuth assumed; separately documented enterprise flows are not implemented. |
| Recommended model | Choose from current discovery; no automatic expensive model selection |
| Deprecations / aliases | Refresh catalog; aliases are not immutable snapshots. See notes below. |

OpenAI-compatible chat with native catalog metadata. /models returns an array rather than the usual data envelope. It includes model type, context and pricing. Account credits, availability and serverless rate limits apply. Choose a chat model rather than embeddings/audio.

## Setup in Social Engagement

Settings ? AI Providers ? Configure ? open official setup page ? enter your key (optional for local servers) ? Test connection ? choose an available model ? Save provider ? Use as primary. Saved keys are masked and OS-encrypted. Replace by entering a new key; Delete key removes the local credential. Model-list tests consume no generated tokens but cannot guarantee inference credits.

## Sources and implementation limits

- [Official reference](https://docs.together.ai/reference/models)
- [Official reference](https://docs.together.ai/docs/quickstart)
- [Official reference](https://docs.together.ai/docs/serverless/rate-limits)

Mocked adapter tests cover request/response contracts, streaming, authentication errors, billing/rate limits, timeouts, malformed responses and outages. They do not prove that a specific account has access. No real credentials or live credit-spending calls are part of the default test suite. Provider-level capability flags describe available API features, not a promise that every model supports them.
