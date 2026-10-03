Last verified: 2026-10-03

# xAI / Grok

| Research item | Finding |
|---|---|
| Authentication | Bearer API key. Responses is current; Chat Completions is legacy. Grok consumer subscriptions do not pay API costs. |
| Base URL | `https://api.x.ai/v1` |
| Generation API | `POST /responses` |
| Model endpoint | `GET /models`; cached for six hours, Refresh Models bypasses cache |
| Streaming | SSE; cancellation closes the local HTTP stream |
| Structured output | Supported on eligible models; JSON/schema shapes differ by API |
| Vision | Model-dependent; missing model metadata is shown as unknown |
| Rate limits | Account/model dependent; 429 pauses work; no hidden retry loop |
| Error format | HTTP status plus provider-specific JSON or stream error events; bodies are not echoed or logged |
| Key setup | [Official setup](https://console.x.ai/team/default/api-keys) |
| Pricing | [Check current pricing](https://docs.x.ai/developers/models); no hard-coded cost estimate |
| Free/trial | See current pricing/account terms; no permanent free label or guaranteed credits |
| Official documentation | [API documentation](https://docs.x.ai/developers/rest-api-reference/inference/chat) |
| Data/privacy | [Provider policy](https://docs.x.ai/developers/faq/security) |
| OpenAI compatibility | Yes, documented compatibility; this adapter may use the native API. |
| OAuth / safer authorization | BYOK/local access verified. No general consumer-subscription OAuth assumed; separately documented enterprise flows are not implemented. |
| Recommended model | Choose from current discovery; no automatic expensive model selection |
| Deprecations / aliases | Refresh catalog; aliases are not immutable snapshots. See notes below. |

Responses replaces legacy Chat Completions for this integration. Models/language-models can expose aliases, context and pricing. Grok 4.7 is current flagship in the reviewed docs; the app does not auto-select a flagship. No consumer subscription flow is assumed. Request storage is disabled.

## Setup in Social Engagement

Settings ? AI Providers ? Configure ? open official setup page ? enter your key (optional for local servers) ? Test connection ? choose an available model ? Save provider ? Use as primary. Saved keys are masked and OS-encrypted. Replace by entering a new key; Delete key removes the local credential. Model-list tests consume no generated tokens but cannot guarantee inference credits.

## Sources and implementation limits

- [Official reference](https://docs.x.ai/developers/rest-api-reference/inference/models)
- [Official reference](https://docs.x.ai/developers/models)
- [Official reference](https://docs.x.ai/developers/faq/security)

Mocked adapter tests cover request/response contracts, streaming, authentication errors, billing/rate limits, timeouts, malformed responses and outages. They do not prove that a specific account has access. No real credentials or live credit-spending calls are part of the default test suite. Provider-level capability flags describe available API features, not a promise that every model supports them.
