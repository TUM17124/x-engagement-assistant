Last verified: 2026-10-03

# Groq

| Research item | Finding |
|---|---|
| Authentication | Bearer API key. Free/paid limits depend on account and model. |
| Base URL | `https://api.groq.com/openai/v1` |
| Generation API | `POST /chat/completions` |
| Model endpoint | `GET /models`; cached for six hours, Refresh Models bypasses cache |
| Streaming | SSE; cancellation closes the local HTTP stream |
| Structured output | Supported on eligible models; JSON/schema shapes differ by API |
| Vision | Model-dependent; missing model metadata is shown as unknown |
| Rate limits | Account/model dependent; 429 pauses work; no hidden retry loop |
| Error format | HTTP status plus provider-specific JSON or stream error events; bodies are not echoed or logged |
| Key setup | [Official setup](https://console.groq.com/keys) |
| Pricing | [Check current pricing](https://console.groq.com/docs/models); no hard-coded cost estimate |
| Free/trial | See current pricing/account terms; no permanent free label or guaranteed credits |
| Official documentation | [API documentation](https://console.groq.com/docs/api-reference) |
| Data/privacy | [Provider policy](https://console.groq.com/docs/your-data) |
| OpenAI compatibility | Yes, documented compatibility; this adapter may use the native API. |
| OAuth / safer authorization | BYOK/local access verified. No general consumer-subscription OAuth assumed; separately documented enterprise flows are not implemented. |
| Recommended model | `openai/gpt-oss-20b`, only if returned by discovery |
| Deprecations / aliases | Refresh catalog; aliases are not immutable snapshots. See notes below. |

The production catalog includes GPT OSS 20B; preview models can retire quickly. Responses is beta, so this adapter uses Chat Completions. Use max_completion_tokens, not deprecated max_tokens. Vision and strict structured output availability vary by model.

## Setup in Social Engagement

Settings ? AI Providers ? Configure ? open official setup page ? enter your key (optional for local servers) ? Test connection ? choose an available model ? Save provider ? Use as primary. Saved keys are masked and OS-encrypted. Replace by entering a new key; Delete key removes the local credential. Model-list tests consume no generated tokens but cannot guarantee inference credits.

## Sources and implementation limits

- [Official reference](https://console.groq.com/docs/models)
- [Official reference](https://console.groq.com/docs/rate-limits)
- [Official reference](https://console.groq.com/docs/errors)
- [Official reference](https://console.groq.com/docs/your-data)

Mocked adapter tests cover request/response contracts, streaming, authentication errors, billing/rate limits, timeouts, malformed responses and outages. They do not prove that a specific account has access. No real credentials or live credit-spending calls are part of the default test suite. Provider-level capability flags describe available API features, not a promise that every model supports them.
