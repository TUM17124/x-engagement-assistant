Last verified: 2026-10-03

# DeepSeek

| Research item | Finding |
|---|---|
| Authentication | Bearer API key. Consumer chat login is separate. |
| Base URL | `https://api.deepseek.com` |
| Generation API | `POST /chat/completions` |
| Model endpoint | `GET /models`; cached for six hours, Refresh Models bypasses cache |
| Streaming | SSE; cancellation closes the local HTTP stream |
| Structured output | Supported on eligible models; JSON/schema shapes differ by API |
| Vision | Model-dependent; missing model metadata is shown as unknown |
| Rate limits | Account/model dependent; 429 pauses work; no hidden retry loop |
| Error format | HTTP status plus provider-specific JSON or stream error events; bodies are not echoed or logged |
| Key setup | [Official setup](https://platform.deepseek.com/api_keys) |
| Pricing | [Check current pricing](https://api-docs.deepseek.com/quick_start/pricing/); no hard-coded cost estimate |
| Free/trial | See current pricing/account terms; no permanent free label or guaranteed credits |
| Official documentation | [API documentation](https://api-docs.deepseek.com/api/create-chat-completion/) |
| Data/privacy | [Provider policy](https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html) |
| OpenAI compatibility | Yes, documented compatibility; this adapter may use the native API. |
| OAuth / safer authorization | BYOK/local access verified. No general consumer-subscription OAuth assumed; separately documented enterprise flows are not implemented. |
| Recommended model | `deepseek-flash`, only if returned by discovery |
| Deprecations / aliases | Refresh catalog; aliases are not immutable snapshots. See notes below. |

Use deepseek-flash for current Flash access. Legacy v4-flash names map to retired models/replacements; do not treat aliases as permanent. Flash supports vision; V4 Pro is text-only in the current pricing table. HTTP 402 indicates balance problems. Responses and Anthropic compatibility also exist.

## Setup in Social Engagement

Settings ? AI Providers ? Configure ? open official setup page ? enter your key (optional for local servers) ? Test connection ? choose an available model ? Save provider ? Use as primary. Saved keys are masked and OS-encrypted. Replace by entering a new key; Delete key removes the local credential. Model-list tests consume no generated tokens but cannot guarantee inference credits.

## Sources and implementation limits

- [Official reference](https://api-docs.deepseek.com/api/list-models/)
- [Official reference](https://api-docs.deepseek.com/quick_start/error_codes/)
- [Official reference](https://api-docs.deepseek.com/quick_start/pricing/)
- [Official reference](https://api-docs.deepseek.com/updates/)

Mocked adapter tests cover request/response contracts, streaming, authentication errors, billing/rate limits, timeouts, malformed responses and outages. They do not prove that a specific account has access. No real credentials or live credit-spending calls are part of the default test suite. Provider-level capability flags describe available API features, not a promise that every model supports them.
