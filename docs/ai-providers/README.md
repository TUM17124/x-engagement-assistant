# AI provider research and architecture

Last verified: 2026-10-03

Official documentation was browsed before adapters were implemented. The central metadata registry is `app/ai_catalog.json`; update its links and verification date together with these research records. Model lists are fetched at runtime, not embedded catalogs. Missing model capabilities remain unknown. Recommendation IDs are dated hints, never an automatically selected model.

`ai_base.py` owns shared prompts. `ai_adapters.py` translates normalized requests/results to native protocols. `ai_connections.py` owns encrypted-key references, non-secret configuration, migration, model caching, context policy, routing and usage. `ai_routes.py` and `ai-providers.js` expose these services through the existing localhost/CSRF boundary. Existing ChatGPT authorization stays optional.

Migrations add connection/model-cache/request metadata tables without rewriting existing social tables. A pre-schema SQLite backup is created beside the private database. Original developer settings and keys remain after migration. No secrets are exported into SQLite.

Local-only mode blocks cloud text/vision/image-generation routes and cloud fallback. It also rejects Ollama remote model metadata. A user-controlled local proxy can itself forward traffic: disable cloud forwarding there; this app cannot attest arbitrary server internals.

Fallback is opt-in and limited to transient non-streamed failures; it never retries rejected credentials, billing or permissions. Interrupted streams are reported rather than silently replayed to another paid provider. ChatGPT plan errors keep their existing explicit recovery flow. X search costs are unrelated to AI costs.

Additional provider researched: [Fireworks Chat API](https://docs.fireworks.ai/api-reference/post-chatcompletions), [model management](https://docs.fireworks.ai/api-reference/list-models), [pricing](https://fireworks.ai/pricing), [privacy](https://fireworks.ai/privacy-policy). Its official OpenAI-compatible endpoint can use Custom. A dedicated account-scoped model-management adapter is not included in this change. Together AI and LM Studio were added as dedicated choices; existing Kimi support was retained.

The API supports structured JSON generation and safe parsing. Claude schema-constrained output is enabled only when discovery confirms capability; older models use a JSON instruction. Custom servers vary in /models and feature support; Custom configuration offers an explicit manual-model option for servers without discovery. Testing it makes a small generation request and says so before use.
