Last verified: 2026-10-03

# OpenAI

| Research item | Finding |
|---|---|
| Authentication | Bearer API key. Existing authorized ChatGPT plan access is a separate optional connection. |
| Base URL | `https://api.openai.com/v1` |
| Generation API | `POST /responses` |
| Model endpoint | `GET /models`; cached for six hours, Refresh Models bypasses cache |
| Streaming | SSE; cancellation closes the local HTTP stream |
| Structured output | Supported on eligible models; JSON/schema shapes differ by API |
| Vision | Model-dependent; missing model metadata is shown as unknown |
| Rate limits | Account/model dependent; 429 pauses work; no hidden retry loop |
| Error format | HTTP status plus provider-specific JSON or stream error events; bodies are not echoed or logged |
| Key setup | [Official setup](https://platform.openai.com/api-keys) |
| Pricing | [Check current pricing](https://developers.openai.com/api/docs/pricing); no hard-coded cost estimate |
| Free/trial | See current pricing/account terms; no permanent free label or guaranteed credits |
| Official documentation | [API documentation](https://developers.openai.com/api/docs/guides/text) |
| Data/privacy | [Provider policy](https://developers.openai.com/api/docs/guides/your-data) |
| OpenAI compatibility | Yes, documented compatibility; this adapter may use the native API. |
| OAuth / safer authorization | BYOK/local access verified. No general consumer-subscription OAuth assumed; separately documented enterprise flows are not implemented. |
| Recommended model | `gpt-6-luna`, only if returned by discovery |
| Deprecations / aliases | Refresh catalog; aliases are not immutable snapshots. See notes below. |

Responses is recommended for new text applications. Model listing may not expose every capability. GPT-6 Luna is the current cost-sensitive recommendation; it is only suggested when discovered. API keys and eligible SIWC grants are separate. Responses storage is disabled by this app.

## Setup in Social Engagement

Settings ? AI Providers ? Configure ? open official setup page ? enter your key (optional for local servers) ? Test connection ? choose an available model ? Save provider ? Use as primary. Saved keys are masked and OS-encrypted. Replace by entering a new key; Delete key removes the local credential. Model-list tests consume no generated tokens but cannot guarantee inference credits.

## Sources and implementation limits

- [Official reference](https://developers.openai.com/api/reference/resources/models/methods/list)
- [Official reference](https://developers.openai.com/api/docs/models)
- [Official reference](https://developers.openai.com/api/docs/guides/your-data)
- [Official reference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)

Mocked adapter tests cover request/response contracts, streaming, authentication errors, billing/rate limits, timeouts, malformed responses and outages. They do not prove that a specific account has access. No real credentials or live credit-spending calls are part of the default test suite. Provider-level capability flags describe available API features, not a promise that every model supports them.
