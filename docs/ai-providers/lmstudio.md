Last verified: 2026-10-03

# LM Studio

| Research item | Finding |
|---|---|
| Authentication | Optional local API token. Start the server in LM Studio Developer settings. |
| Base URL | `http://127.0.0.1:1234/v1` |
| Generation API | `POST /chat/completions` |
| Model endpoint | `GET /models`; cached for six hours, Refresh Models bypasses cache |
| Streaming | SSE; cancellation closes the local HTTP stream |
| Structured output | Supported on eligible models; JSON/schema shapes differ by API |
| Vision | Model-dependent; missing model metadata is shown as unknown |
| Rate limits | Account/model dependent; 429 pauses work; no hidden retry loop |
| Error format | HTTP status plus provider-specific JSON or stream error events; bodies are not echoed or logged |
| Key setup | [Official setup](https://lmstudio.ai/docs/developer/core/authentication) |
| Pricing | [Check current pricing](https://lmstudio.ai/pricing); no hard-coded cost estimate |
| Free/trial | See current pricing/account terms; no permanent free label or guaranteed credits |
| Official documentation | [API documentation](https://lmstudio.ai/docs/developer/openai-compat) |
| Data/privacy | [Provider policy](https://lmstudio.ai/app-privacy) |
| OpenAI compatibility | Yes, documented compatibility; this adapter may use the native API. |
| OAuth / safer authorization | BYOK/local access verified. No general consumer-subscription OAuth assumed; separately documented enterprise flows are not implemented. |
| Recommended model | Choose from current discovery; no automatic expensive model selection |
| Deprecations / aliases | Refresh catalog; aliases are not immutable snapshots. See notes below. |

Developer UI can start a local server without a terminal. Optional Bearer tokens are supported. Native v1 is recommended by LM Studio; this app uses its documented stateless OpenAI compatibility endpoint to reuse the tested adapter. Model discovery lists models visible to the server. Download model weights separately.

## Setup in Social Engagement

Settings ? AI Providers ? Configure ? open official setup page ? enter your key (optional for local servers) ? Test connection ? choose an available model ? Save provider ? Use as primary. Saved keys are masked and OS-encrypted. Replace by entering a new key; Delete key removes the local credential. Model-list tests consume no generated tokens but cannot guarantee inference credits.

## Sources and implementation limits

- [Official reference](https://lmstudio.ai/docs/developer/rest)
- [Official reference](https://lmstudio.ai/docs/developer/core/authentication)
- [Official reference](https://lmstudio.ai/docs/developer/openai-compat/models)

Mocked adapter tests cover request/response contracts, streaming, authentication errors, billing/rate limits, timeouts, malformed responses and outages. They do not prove that a specific account has access. No real credentials or live credit-spending calls are part of the default test suite. Provider-level capability flags describe available API features, not a promise that every model supports them.
