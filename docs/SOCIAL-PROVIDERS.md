# Social adapters and external setup

An implemented adapter does not mean an account is connected. State comes from the user's local OAuth credentials/profile. Tests mock APIs and never publish.

| Network | Implemented API features | Manual / limited in this release |
| --- | --- | --- |
| X | Existing OAuth, paid recent search, account posts, mentions, lookup, text originals/threads/quotes/replies, available metrics | Web-search fallback, local-media handoff; project credits/permissions apply |
| Facebook Pages | OAuth/Page selection, managed Page feed/comments, text and PNG/JPEG posts, comments/replies | Personal profile posting and other media; approved scopes needed |
| Instagram professional | Instagram Login, own media/profile, authorized media comments and replies | Local-media publishing, arbitrary creators, general search |
| LinkedIn | OAuth identity, text posts | Restricted read feeds/comments and media are not implemented |
| TikTok | Login Kit, Display API profile/own videos | Direct post, upload and comments are manual |
| YouTube | Google OAuth, own channel, authorized comments and replies | Community posts and video upload |
| Threads | OAuth, own threads/replies, text posts/replies | Local media and broad discovery |
| Reddit / future adapters | No adapter installed | Clearly unavailable; no fake account |

One selected account/page per social platform is currently supported. ChatGPT registrations are separate.

## Setup

Where platforms require developer apps, enter your own registered client configuration in Connected Accounts, then authorize in the official browser flow. Approved scopes, app review, account type, and region still apply. Never enter a social password.

The UI provides callback guidance. If a provider requires an HTTPS callback, register your authorized callback and use the completion UI with its returned URL. State must match the pending flow. There is no hidden relay or cookie extraction.

Meta/Threads expiry may require reconnecting. Google/TikTok refresh tokens are used when issued. Unreported permissions are labelled unverified; endpoint responses determine availability.

Paid X read/write costs are separate from ChatGPT-plan inference. Local caps count requests rather than estimating prices. Billing/access failures pause discovery and preserve manual fallback.

## Adding a provider

1. Add truthful implemented capabilities to social/catalog.py.
2. Subclass SocialProvider using fixed documented official endpoints and normalized posts.
3. Register it in social/registry.py and add documented OAuth configuration.
4. Keep tokens in the existing OS vault.
5. Use shared approval-first publishing; never publish during discovery/analysis.
6. Keep unsupported actions manual.
7. Add mocked OAuth, error, capability, and payload tests.
8. Extend typed terminal platform enums only when the adapter is usable.
9. Document app-review and account restrictions.

No scraping, Selenium, Playwright, private APIs, session-cookie extraction, or anti-bot bypass is used.
