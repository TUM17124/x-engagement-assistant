Last verified: 2026-10-03

# Ollama

| Research item | Finding |
|---|---|
| Authentication | No key for local inference. Cloud models are a separate service, even through a localhost server. |
| Base URL | `http://127.0.0.1:11434` |
| Generation API | `POST /api/chat` |
| Model endpoint | `GET /api/tags`; cached for six hours, Refresh Models bypasses cache |
| Streaming | NDJSON; cancellation closes the local HTTP stream |
| Structured output | Supported on eligible models; JSON/schema shapes differ by API |
| Vision | Model-dependent; missing model metadata is shown as unknown |
| Rate limits | Account/model dependent; 429 pauses work; no hidden retry loop |
| Error format | HTTP status plus provider-specific JSON or stream error events; bodies are not echoed or logged |
| Key setup | [Official setup](https://docs.ollama.com/api/authentication) |
| Pricing | [Check current pricing](https://ollama.com/pricing); no hard-coded cost estimate |
| Free/trial | See current pricing/account terms; no permanent free label or guaranteed credits |
| Official documentation | [API documentation](https://docs.ollama.com/api/chat) |
| Data/privacy | [Provider policy](https://ollama.com/privacy) |
| OpenAI compatibility | Yes, documented compatibility; this adapter may use the native API. |
| OAuth / safer authorization | BYOK/local access verified. No general consumer-subscription OAuth assumed; separately documented enterprise flows are not implemented. |
| Recommended model | Choose from current discovery; no automatic expensive model selection |
| Deprecations / aliases | Refresh catalog; aliases are not immutable snapshots. See notes below. |

Local requests require no key. /api/chat streams NDJSON; format supports JSON/schema. Models can be local or cloud-backed, even at localhost. Local-only checks /api/show metadata and rejects remote/unverifiable models. Disable cloud features in Ollama too. Hardware and model licences constrain local use.

## Setup in Social Engagement

Settings ? AI Providers ? Configure ? open official setup page ? enter your key (optional for local servers) ? Test connection ? choose an available model ? Save provider ? Use as primary. Saved keys are masked and OS-encrypted. Replace by entering a new key; Delete key removes the local credential. Model-list tests consume no generated tokens but cannot guarantee inference credits.

## Sources and implementation limits

- [Official reference](https://docs.ollama.com/api/introduction)
- [Official reference](https://docs.ollama.com/api/tags)
- [Official reference](https://docs.ollama.com/api/authentication)
- [Official reference](https://docs.ollama.com/faq)

Mocked adapter tests cover request/response contracts, streaming, authentication errors, billing/rate limits, timeouts, malformed responses and outages. They do not prove that a specific account has access. No real credentials or live credit-spending calls are part of the default test suite. Provider-level capability flags describe available API features, not a promise that every model supports them.
