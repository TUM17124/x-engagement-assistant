# Trend Radar

Last verified: 2026-10-03

Radar combines a bounded sample from several official public APIs. Refresh is explicit; opening the page reads the local cache. No social credentials, paid X searches or AI calls are used to refresh these sources. Existing X paid search and local social-feed patterns remain available.

| Source | API / evidence | Scope |
| --- | --- | --- |
| [Mastodon](https://docs.joinmastodon.org/methods/trends/) | `mastodon.social/api/v1/trends/statuses` | Instance-ranked public posts, including available image/video/audio attachments. Sensitive/spoiler posts are excluded. |
| [DEV / open-source Forem](https://developers.forem.com/api/v1) | `dev.to/api/articles?top=7` | Popular recent developer articles, not worldwide trends. |
| [PeerTube / Framatube](https://docs.joinpeertube.org/api-rest-reference.html) | `framatube.org/api/v1/videos?sort=-trending` | Instance-ranked video metadata. Direct playable files are requested only when a preview is opened. |
| [Hacker News](https://github.com/HackerNews/API) | Official Firebase top stories + item endpoints | Public API; HN itself is not an open-source platform. Top twenty stories, four concurrent item reads at most. |

The PeerTube [official OpenAPI schema](https://github.com/Chocobozzz/PeerTube/blob/develop/support/doc/api/openapi.yaml) documents trending sorting and video details. Mastodon's [media schema](https://docs.joinmastodon.org/entities/MediaAttachment/) documents audio, video, image and animated attachments.

## Using it

1. Open Trend Radar and set interests or reuse your onboarding interests.
2. Refresh public trends. Per-source errors retain cached content and its observation timestamp.
3. Filter by source, media type, saved items, interests or text. Save useful evidence; ignore distractions.
4. Load a media preview explicitly, or open its original source. Playback contacts that server, sends no app credentials and does not autoplay. No third-party embeds, scraping or transcription run.
5. Choose a post, hooks, thread, video script or audio/podcast outline, add your own angle and create a draft.
6. Review/edit it in Response Inbox. Publishing still requires approval and platform permissions.

AI receives selected source text/metadata, interests and the writing context allowed in AI Providers. It has not watched/listened to linked media. This is disclosed in the UI and prompt. It must not copy creators, invent facts, or treat source instructions as commands. Long scripts need adapting to platform limits before approval.

Relevance is a transparent local keyword match, not an AI virality prediction. Metrics are copied from source responses, never combined into fabricated growth. Audio/video filters may legitimately be empty. There is no claim of exhaustive coverage or trending music discovery.

## Limits and recovery

Each source has a fifteen-minute cache; refresh sessions have a configurable daily cap. 429 honors numeric Retry-After; access failures pause that source for a day. No automatic retry loop runs. Requests and item counts are bounded. Cached items persist across restart with stable source IDs; saved/ignored state survives refresh. Exact duplicate drafting requests return the existing draft.

Preview URLs allow only documented/configured media hosts. Unknown hosts, unsupported files or blocked playback use Open Original. This is intentionally narrower than unrestricted remote URL fetching. Reading a source's metadata does not license reuse of its media.

Terminal tools `trends.analyze`, `trends.scan`, and `trends.draft` use the same service. Automations may call the bounded scan/draft tools; they cannot approve or publish a result.
