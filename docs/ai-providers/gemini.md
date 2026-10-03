Last verified: 2026-10-03

# Google Gemini

| Research item | Finding |
|---|---|
| Authentication | API key in x-goog-api-key. Google Cloud OAuth is a separate project setup, not consumer subscription sharing. |
| Base URL | `https://generativelanguage.googleapis.com/v1beta` |
| Generation API | `POST /models/{model}:generateContent` |
| Model endpoint | `GET /models`; cached for six hours, Refresh Models bypasses cache |
| Streaming | SSE; cancellation closes the local HTTP stream |
| Structured output | Supported on eligible models; JSON/schema shapes differ by API |
| Vision | Model-dependent; missing model metadata is shown as unknown |
| Rate limits | Account/model dependent; 429 pauses work; no hidden retry loop |
| Error format | HTTP status plus provider-specific JSON or stream error events; bodies are not echoed or logged |
| Key setup | [Official setup](https://aistudio.google.com/apikey) |
| Pricing | [Check current pricing](https://ai.google.dev/gemini-api/docs/pricing); no hard-coded cost estimate |
| Free/trial | See current pricing/account terms; no permanent free label or guaranteed credits |
| Official documentation | [API documentation](https://ai.google.dev/api/generate-content) |
| Data/privacy | [Provider policy](https://ai.google.dev/gemini-api/terms) |
| OpenAI compatibility | Yes, documented compatibility; this adapter may use the native API. |
| OAuth / safer authorization | BYOK/local access verified. No general consumer-subscription OAuth assumed; separately documented enterprise flows are not implemented. |
| Recommended model | `gemini-3.5-flash-lite`, only if returned by discovery |
| Deprecations / aliases | Refresh catalog; aliases are not immutable snapshots. See notes below. |

Current model docs recommend 3.5 Flash-Lite for inexpensive workloads. Access to older 2.5 models may be restricted to existing users. Free and paid tiers have different data-use terms. Native models list supports pagination and generation-method filtering; compatibility API also exists.

## Setup in Social Engagement

Settings ? AI Providers ? Configure ? open official setup page ? enter your key (optional for local servers) ? Test connection ? choose an available model ? Save provider ? Use as primary. Saved keys are masked and OS-encrypted. Replace by entering a new key; Delete key removes the local credential. Model-list tests consume no generated tokens but cannot guarantee inference credits.

## Sources and implementation limits

- [Official reference](https://ai.google.dev/api/models)
- [Official reference](https://ai.google.dev/gemini-api/docs/models)
- [Official reference](https://ai.google.dev/gemini-api/docs/troubleshooting)
- [Official reference](https://ai.google.dev/gemini-api/docs/structured-output)

Mocked adapter tests cover request/response contracts, streaming, authentication errors, billing/rate limits, timeouts, malformed responses and outages. They do not prove that a specific account has access. No real credentials or live credit-spending calls are part of the default test suite. Provider-level capability flags describe available API features, not a promise that every model supports them.
