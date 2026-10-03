# Video Generation

Last verified: 2026-10-03

Settings > Video Generation is separate from text AI and image generation. Add your own key, test the official model catalog, select a model, set a daily cap and save. Existing text-provider selection and credentials are unchanged. Keys and temporary signed download links live in OS-backed secure storage.

| Adapter | Official contract | Limits |
| --- | --- | --- |
| [Google Gemini / Veo](https://ai.google.dev/gemini-api/docs/veo) | `models/{model}:predictLongRunning`; poll returned operation; retrieve generated video URI | Discovers models advertising `predictLongRunning`. Uses provider defaults. The newer Gemini Omni Interactions API is not implemented here. |
| [xAI video](https://docs.x.ai/developers/model-capabilities/video/generation) | `POST /v1/videos/generations`; `GET /v1/videos/{request_id}` | [Video model discovery](https://docs.x.ai/developers/rest-api-reference/inference/models). Requests five seconds, landscape, 720p. Account/model restrictions can still reject a request. |

OpenAI's [official Videos API reference](https://developers.openai.com/api/reference/resources/videos/methods/create) says Sora 2 / Videos shut down September 24, 2026. It is not offered as a working adapter. Other video APIs can be added through `VideoProvider`; there is no invented universal compatible video endpoint.

## Workflow and costs

Media > Generate a video > enter prompt > explicitly confirm provider charges. A local persistent job is created before submission. Check status polls at most every thirty seconds. The app does not submit again after timeout, crash or an ambiguous response. An uncertain job requires checking the provider dashboard; identical requests are not charged again by an automatic retry. Providers may continue processing while this app is closed. There is no cancellation guarantee or refund promise.

Save a ready video into Media Library before the provider's temporary output expires. Downloads are bounded to 50 MB and validated as MP4. Credentials are only sent to the official authenticated API host; redirects to approved storage hosts receive no API key. Unknown output hosts are blocked, with a dashboard fallback. Local AI Only blocks cloud video generation and downloads.

Review the video and add it to Create. Generating/downloading a clip never posts it. Publishing video depends on the social adapter; unsupported platforms retain manual export/publishing. This implementation is text-to-video, not video editing, image-to-video, automatic transcription, or automatic social uploads.

Model discovery is a low-cost access check, not proof of generation credits. API billing is separate from consumer subscriptions. Prices are not embedded. Use official pricing links in Settings. Live paid generation tests are not run by the standard suite.
