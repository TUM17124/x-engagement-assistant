/* Cross-platform screens reuse the existing local API, approval and design primitives. */
let socialPlatform = "",
  socialFilter = "all",
  inboxTab = "review",
  socialDrafts = [],
  socialItems = [],
  mediaCache = [],
  ideaCache = [],
  watchCategory = "favorite";
let createVersions = {},
  createBrief = "",
  selectedPlatforms = ["x"];
const platformLabels = {
  x: "X",
  facebook: "Facebook",
  instagram: "Instagram",
  linkedin: "LinkedIn",
  tiktok: "TikTok",
  youtube: "YouTube",
  threads: "Threads",
};
const platformTag = (p) =>
  '<span class="pill platform-' +
  p +
  '">' +
  esc(platformLabels[p] || p) +
  "</span>";
const platformSelect = (name, value = "", all = true) =>
  select("Platform", name, value, [
    ...(all ? [["", "All platforms"]] : []),
    ...Object.entries(platformLabels),
  ]);
const msButton = (label, action, id = "", cls = "ghost") =>
  btn(label, "ms-" + action, id, cls);
function socialCard(f) {
  let metrics = {};
  try {
    metrics = JSON.parse(f.metrics);
  } catch {}
  let previews = [];
  try {
    previews = JSON.parse(f.media_json || "[]");
  } catch {}
  return (
    '<article class="card">' +
    platformTag(f.platform) +
    '<div class="author"><span class="avatar">' +
    (safeRemoteImage(f.avatar)
      ? '<img src="' +
        esc(f.avatar) +
        '" alt="" loading="lazy" referrerpolicy="no-referrer">'
      : esc((f.username || "?").slice(0, 1).toUpperCase())) +
    "</span><div><strong>" +
    esc(f.username) +
    "</strong><br><small>" +
    esc(fmt(f.posted_at || f.imported_at)) +
    " &middot; " +
    esc(f.content_kind) +
    '</small></div></div><div class="post-text">' +
    esc(f.text) +
    "</div>" +
    previews
      .filter((m) => safeRemoteImage(m.url))
      .map(
        (m) =>
          '<img class="media-preview" loading="lazy" referrerpolicy="no-referrer" src="' +
          esc(m.url) +
          '" alt="' +
          esc(m.alt_text || "Post image") +
          '">',
      )
      .join("") +
    (f.reason
      ? '<p class="hint">' +
        esc(f.reason) +
        " &middot; Opportunity " +
        f.priority +
        "/100</p>"
      : "") +
    '<div class="metrics">' +
    Object.entries(metrics)
      .map(([k, v]) => "<span>" + esc(k) + " " + esc(v) + "</span>")
      .join("") +
    '</div><div class="row">' +
    msButton(
      f.content_kind === "comment"
        ? "Generate Reply"
        : "Generate Reply / Comment",
      "analyze",
      f.id,
      "",
    ) +
    link("Open Original", f.url || "https://x.com/i/web/status/" + f.id) +
    btn(
      f.saved ? "Unsave" : "Save",
      f.saved ? "unsave-feed" : "save-feed",
      f.id,
    ) +
    btn("Ignore", "ignore-feed", f.id) +
    msButton("Mute", "mute", f.id) +
    "</div></article>"
  );
}
async function socialFeedPage() {
  accountsCache = await api("/api/social/accounts");
  socialItems = await api(
    "/api/social/feed?" +
      new URLSearchParams({ platform: socialPlatform, filter: socialFilter }),
  );
  return (
    heading(
      "Social Feed",
      "One place to review the activity you import or authorize.",
    ) +
    '<div class="row toolbar"><a class="btn" href="#x-discovery">X API Search / Web Search</a><a class="btn ghost" href="#listener">Social Listener</a></div><form id="social-feed-filter" class="row">' +
    platformSelect("platform", socialPlatform) +
    select("Show", "filter", socialFilter, [
      ["all", "All"],
      ["mentions", "Mentions"],
      ["comments", "Comments"],
      ["favorites", "Favorite Accounts"],
      ["high", "High Priority"],
      ["questions", "Questions"],
      ["ignored", "Ignored"],
    ]) +
    '<button type="submit">Filter</button></form><div class="grid"><section>' +
    (socialItems.length
      ? socialItems.map(socialCard).join("")
      : empty(
          "Your feed starts with one useful post",
          "Import a link and text, or connect an authorized API source.",
        )) +
    '</section><aside><form id="social-import-form" class="card"><h2>Import from any network</h2>' +
    platformSelect("platform", socialPlatform || "x", false) +
    input("Original URL (optional for pasted text)", "url", "", "url") +
    input("Author", "author") +
    select("Content type", "kind", "post", ["post", "comment", "mention"]) +
    area("Original text", "text", "", "required") +
    '<button type="submit">Import to feed</button><p class="hint">No scraping. URLs are validated locally; paste text when API access is unavailable.</p></form><div class="card"><h3>Authorized API sources</h3>' +
    accountsCache
      .filter((a) => a.connected)
      .map(
        (a) =>
          '<div class="notice">' +
          platformTag(a.platform) +
          '<div class="row">' +
          (a.capabilities.can_read_feed
            ? msButton("Sync own feed", "sync", a.platform)
            : "") +
          (a.capabilities.can_read_mentions
            ? msButton("Sync mentions", "mentions", a.platform)
            : "") +
          (a.capabilities.can_read_comments
            ? '<form class="social-comments-form" data-platform="' +
              a.platform +
              '">' +
              input(
                "Post / video ID (blank for YouTube channel comments)",
                "target",
              ) +
              '<button type="submit">Read comments</button></form>'
            : "") +
          "</div></div>",
      )
      .join("") +
    '<a href="#settings">Manage connected accounts</a></div></aside></div>'
  );
}
function responseCard(d) {
  const a = accountsCache.find((a) => a.platform === d.platform),
    caps = a?.capabilities || {},
    approved = ["approved", "scheduled"].includes(d.status),
    locked = ["published", "sending", "uncertain", "partial"].includes(
      d.status,
    );
  const attached = JSON.parse(d.media_ids || "[]");
  const supportsMedia =
    !attached.length ||
    (caps.can_upload_images &&
      attached.every((id) =>
        ["image/png", "image/jpeg"].includes(
          mediaCache.find((m) => m.id === id)?.mime,
        ),
      ));
  const canAPI =
    supportsMedia &&
    (d.kind === "original"
      ? caps.can_publish
      : d.kind === "comment"
        ? caps.can_comment
        : caps.can_reply) &&
    (d.kind === "original" ||
      d.platform === "x" ||
      (d.source || "").startsWith("API"));
  let flags = [];
  try {
    flags = JSON.parse(d.quality || "[]");
  } catch {}
  const media = JSON.parse(d.media_ids || "[]");
  return (
    '<article class="card" data-social-draft="' +
    d.id +
    '"><div class="row between"><div>' +
    platformTag(d.platform) +
    " <strong>" +
    esc(d.kind) +
    " " +
    esc(d.username ? "to " + d.username : "") +
    '</strong></div><span class="pill">' +
    esc(d.status) +
    " &middot; " +
    d.score +
    "/100 relevance</span></div>" +
    (d.source_text
      ? '<div class="source">' + esc(d.source_text) + "</div>"
      : "") +
    '<p class="hint">' +
    esc(d.reason || d.opportunity_reason || "Your saved content") +
    "</p>" +
    area(
      "Review and edit",
      "social-draft-" + d.id,
      d.text,
      locked ? "readonly" : "",
    ) +
    (!locked
      ? '<label>Attached media<select multiple name="media-edit-' +
        d.id +
        '">' +
        mediaCache
          .map(
            (m) =>
              '<option value="' +
              m.id +
              '" ' +
              (media.includes(m.id) ? "selected" : "") +
              ">" +
              esc(m.name) +
              "</option>",
          )
          .join("") +
        "</select></label>"
      : "") +
    '<p class="hint">' +
    d.text.length +
    " characters &middot; " +
    media.length +
    " attached media files</p>" +
    (flags.length
      ? '<div class="notice warning"><strong>Quality review</strong><br>' +
        flags.map(esc).join("<br>") +
        "</div>"
      : "") +
    (!locked
      ? '<div class="row">' +
        msButton("Save edits", "save", d.id) +
        (approved
          ? (canAPI ? msButton("Post Now (API)", "publish", d.id, "") : "") +
            msButton("Copy & open manually", "manual", d.id)
          : msButton("Approve exact content", "approve", d.id, "")) +
        (approved
          ? msButton("Schedule / reminder", "schedule", d.id)
          : "") +
        btn("Skip", "skip-draft", d.id) +
        '</div><div class="row">' +
        select("Rewrite / regenerate", "social-style-" + d.id, "Humanize", [
          "Humanize",
          "Regenerate",
          "Shorter",
          "Longer",
          "More casual",
          "More professional",
          "More technical",
          "More humorous",
          "Ask a question",
          "Disagree politely",
          "Mention my product naturally",
          "Do NOT mention my product",
        ]) +
        msButton("Apply AI style", "rewrite", d.id) +
        msButton("Duplicate for platform", "duplicate", d.id) +
        "</div>"
      : '<p class="hint">Publishing is locked for this status. Review History and the platform before attempting again.</p>') +
    (d.platform === "x" && d.kind === "reply"
      ? '<a href="#approvals">X quote / reply approval tools</a>'
      : "") +
    '<p class="hint">Edits clear approval. Manual handoff never claims the post was published.</p></article>'
  );
}
async function responseInboxPage() {
  mediaCache = await api("/api/media");
  accountsCache = await api("/api/social/accounts");
  socialDrafts = await api(
    "/api/social/inbox?" +
      new URLSearchParams({ tab: inboxTab, platform: socialPlatform }),
  );
  return (
    heading(
      "Response Inbox",
      "Opportunities, drafts, and your final decisions.",
    ) +
    '<div class="tabs">' +
    [
      ["review", "Needs Review"],
      ["mentions", "Mentions"],
      ["comments", "Comments"],
      ["questions", "Questions"],
      ["high", "High Priority"],
      ["favorites", "Favorite Accounts"],
      ["product", "Product Opportunities"],
      ["trending", "Trending"],
      ["approved", "Approved"],
      ["scheduled", "Scheduled"],
      ["ignored", "Ignored"],
    ]
      .map(([k, v]) =>
        msButton(v, "inbox-tab", k, k === inboxTab ? "active" : ""),
      )
      .join("") +
    "</div>" +
    (socialDrafts.length
      ? socialDrafts.map(responseCard).join("")
      : empty(
          "Nothing in this view yet",
          "Import content into Social Feed or write a post in Create.",
          '<a class="btn" href="#feed">Open Social Feed</a>',
        ))
  );
}
async function trendPage() {
  const trends = await api("/api/social/trends");
  return (
    heading(
      "Trend Radar",
      "Patterns in your local authorized sample, with evidence.",
    ) +
    '<div class="row toolbar"><a class="btn" href="#topics">Tracked topics &amp; X search queries</a><a class="btn ghost" href="#planner">AI Planner</a></div>' +
    (!trends.length
      ? empty(
          "Let a few conversations collect",
          "Add interests and import posts. Repeated topics and hashtags will appear here.",
        )
      : trends
          .map(
            (t, i) =>
              '<article class="card"><h2>' +
              esc(t.name) +
              "</h2><p>" +
              t.current +
              " items in the last 24h &middot; " +
              t.previous +
              " in the prior 24h &middot; Change " +
              (t.velocity > 0 ? "+" : "") +
              t.velocity +
              '</p><p class="hint">' +
              esc(t.note) +
              "<br>" +
              esc(t.reason) +
              '</p><div class="row">' +
              t.platforms.map(platformTag).join("") +
              "</div><details><summary>Related content</summary>" +
              t.related
                .map(
                  (p) =>
                    "<p>" +
                    esc(p.text) +
                    " " +
                    link(
                      "Open Original",
                      p.url || "https://x.com/i/web/status/" + p.id,
                      "",
                    ) +
                    "</p>",
                )
                .join("") +
              '</details><form class="trend-idea-form" data-topic="' +
              esc(t.name) +
              '">' +
              select(
                "Create an original suggestion",
                "task",
                "Generate post idea",
                [
                  "Generate post idea",
                  "Generate 3 hooks",
                  "Generate educational post",
                  "Generate funny post",
                  "Generate founder perspective",
                  "Generate question",
                  "Generate thread",
                  "Generate image-post concept",
                  "Generate short video script",
                ],
              ) +
              '<button type="submit">Generate idea</button></form><div class="suggestion-output"></div></article>',
          )
          .join(""))
  );
}
async function createPage() {
  accountsCache = await api("/api/social/accounts");
  mediaCache = await api("/api/media");
  return (
    heading("Create", "Give each platform its own version. Review every one.") +
    '<div class="row toolbar"><a class="btn ghost" href="#compose">X thread / quote composer</a><a class="btn ghost" href="#planner">AI weekly planner</a></div><form id="cross-compose-form" class="card">' +
    area("Your brief / shared source facts", "brief", createBrief) +
    '<div class="chips">' +
    Object.entries(platformLabels)
      .map(
        ([p, n]) =>
          '<label><input type="checkbox" name="platform" value="' +
          p +
          '" ' +
          (selectedPlatforms.includes(p) ? "checked" : "") +
          ">" +
          n +
          "</label>",
      )
      .join("") +
    "</div>" +
    select("AI writing tool", "task", "Write", [
      "Write",
      "Rewrite",
      "Shorten",
      "Expand",
      "More human",
      "More casual",
      "More professional",
      "More controversial but respectful",
      "More educational",
      "Founder voice",
      "Generate alternatives",
    ]) +
    '<div class="row"><button type="submit">Prepare selected versions</button>' +
    msButton("Adapt with AI (up to 3 platforms)", "adapt", "", "") +
    '</div><p class="hint">Preparing versions does not publish. AI adaptation uses one request per selected platform.</p></form><div id="platform-versions">' +
    Object.entries(createVersions)
      .map(([p, v]) => versionCard(p, v))
      .join("") +
    "</div>"
  );
}
function versionCard(p, v) {
  const a = accountsCache.find((a) => a.platform === p);
  return (
    '<form class="platform-version-form card" data-platform="' +
    p +
    '">' +
    platformTag(p) +
    (v.quality?.length
      ? '<div class="notice warning">' +
        v.quality.map(esc).join("<br>") +
        "</div>"
      : "") +
    area(
      "Editable " + platformLabels[p] + " version",
      "text",
      v.text,
      "required",
    ) +
    '<p class="hint">Limit: ' +
    a.limit +
    " characters. " +
    esc(a.note) +
    '</p><div class="preview">' +
    esc(v.text) +
    '</div><label>Attach local media (up to four)<select name="media_ids" multiple>' +
    mediaCache
      .map(
        (m) =>
          '<option value="' +
          m.id +
          '">' +
          esc(m.name) +
          " (" +
          esc(m.mime) +
          ")</option>",
      )
      .join("") +
    '</select></label><div class="row"><button type="submit">Save for approval</button></div><p class="hint">Attached media stays local until an approved supported API publish. Other platforms use download and manual upload.</p></form>'
  );
}
async function watchSocialPage(market = false) {
  const category = market ? "competitor" : "favorite",
    items = market
      ? (await api("/api/social/market")).map((x) => x.watch)
      : await api("/api/social/watch?category=" + category);
  return (
    heading(
      market ? "Market Watch" : "People & Accounts Watchlist",
      market
        ? "Public or authorized content only; no personal profiling."
        : "Prioritize people whose conversations you value.",
    ) +
    '<div class="row toolbar">' +
    (!market
      ? '<a class="btn" href="#x-watchlist">Existing X watchlist &amp; API tracking</a>'
      : "") +
    '<a class="btn ghost" href="#listener">Assistant Mode settings</a></div><div class="grid"><section>' +
    items
      .map(
        (w) =>
          '<article class="card">' +
          platformTag(w.platform) +
          "<h2>" +
          esc(w.handle) +
          "</h2><p>" +
          esc(w.priority) +
          " priority &middot; " +
          (w.enabled ? "Enabled" : "Disabled") +
          "<br>" +
          esc(w.topics) +
          "</p><small>Last checked: " +
          esc(fmt(w.last_checked)) +
          '</small><p class="hint">' +
          esc(
            w.error ||
              "API monitoring is limited to the accounts and permissions supported by the adapter.",
          ) +
          '</p><div class="row">' +
          link("Open Original", w.url) +
          msButton("Edit", "edit-watch", w.id) +
          msButton("Remove", "delete-watch", w.id) +
          "</div></article>",
      )
      .join("") +
    '</section><form id="social-watch-form" class="card">' +
    platformSelect("platform", "x", false) +
    input("Account ID / handle / keyword", "handle", "", "text", "required") +
    input("Profile URL (for manual opening)", "url", "", "url") +
    select("Category", "category", category, [
      "favorite",
      "competitor",
      "industry",
      "keyword",
      "brand",
    ]) +
    select("Priority", "priority", "Normal", ["Low", "Normal", "High"]) +
    input("Topics", "topics") +
    check("Enabled", "enabled", true) +
    check("Prepare drafts from authorized new content", "auto_draft", false) +
    check("Notify me", "notifications", false) +
    '<button type="submit">Save watch</button><p class="hint">Most non-X APIs expose your own authorized account, not arbitrary competitors. Unsupported monitoring remains an Open Original workflow.</p></form></div>' +
    (market
      ? '<div class="card"><h2>Observed market activity</h2>' +
        msButton("Summarize matching local posts", "market-summary") +
        '<div id="market-summary"></div></div>'
      : "")
  );
}
async function ideasPage() {
  ideaCache = await api("/api/social/ideas");
  return (
    heading(
      "Ideas",
      "Keep the rough thoughts. Turn them into something when ready.",
    ) +
    '<div class="grid"><section>' +
    ideaCache
      .map(
        (i) =>
          '<article class="card"><h2>' +
          esc(i.title) +
          '</h2><div class="post-text">' +
          esc(i.text) +
          '</div><div class="row">' +
          msButton("Create from idea", "use-idea", i.id) +
          msButton("Delete", "delete-idea", i.id) +
          (i.url ? link("Reference", i.url) : "") +
          "</div></article>",
      )
      .join("") +
    '</section><form id="idea-form" class="card">' +
    input("Title", "title", "", "text", "required") +
    area("Thought, quote, or source notes", "text", "", "required") +
    input("Reference link (optional)", "url", "", "url") +
    select("Type", "kind", "thought", [
      "thought",
      "quote",
      "link",
      "trend",
      "draft",
      "video script",
      "screenshot reference",
    ]) +
    '<button type="submit">Save idea</button></form></div>'
  );
}
async function mediaPage() {
  mediaCache = await api("/api/media");
  return (
    heading(
      "Media Library & Content Studio",
      "Your originals stay intact. Edits create a new image.",
    ) +
    '<div class="grid"><form id="media-upload-form" class="card"><h2>Add media</h2><input type="file" name="file" accept=".png,.jpg,.jpeg,.webp,.gif,.mp4" required><button type="submit">Upload locally</button><p class="hint">PNG, JPG, WEBP, GIF, MP4. Up to 50 MB. Nothing is uploaded to a social account.</p></form><form id="image-generation-form" class="card"><h2>Generate an image</h2>' +
    area("Image prompt", "prompt", "", "required") +
    '<button type="submit">Generate with configured image provider</button><p class="hint">Configure a separate image endpoint in AI Provider. This sends your prompt to that endpoint.</p></form></div><form id="media-filter-form" class="row">' +
    input("Search name, tags, caption", "q") +
    input("Folder", "folder") +
    check("Favorites only", "favorite", false) +
    '<button type="submit">Search</button></form><div class="grid" id="media-grid">' +
    mediaCache.map(mediaCard).join("") +
    "</div>"
  );
}
function mediaCard(m) {
  return (
    '<article class="card"><h3>' +
    esc(m.name) +
    "</h3>" +
    (m.mime === "video/mp4"
      ? '<video class="media-preview" controls preload="metadata" src="/api/media/' +
        m.id +
        '/file"></video>'
      : '<img class="media-preview" loading="lazy" src="/api/media/' +
        m.id +
        '/file" alt="' +
        esc(m.alt_text) +
        '">') +
    '<p class="hint">' +
    Math.round(m.size / 1024) +
    " KB &middot; " +
    (m.width ? m.width + " x " + m.height : "Video dimensions not inspected") +
    "<br>" +
    esc(fmt(m.created_at)) +
    '</p><form class="media-metadata-form" data-id="' +
    m.id +
    '">' +
    input("Tags", "tags", m.tags) +
    input("Folder", "folder", m.folder) +
    input("Caption", "caption", m.caption) +
    input("Alt text", "alt_text", m.alt_text) +
    check("Favorite", "favorite", m.favorite) +
    '<button type="submit">Save details</button></form><div class="row">' +
    msButton("AI captions / alt text", "media-assist", m.id) +
    msButton("Usage history", "media-usage", m.id) +
    msButton("Reuse in Create", "media-reuse", m.id) +
    '<a class="btn" href="/api/media/' +
    m.id +
    '/file?download=true" download>Download</a>' +
    msButton("Delete", "media-delete", m.id, "danger") +
    "</div>" +
    (m.width
      ? '<details><summary>Crop / resize a copy</summary><form class="media-transform-form" data-id="' +
        m.id +
        '">' +
        select("Aspect-ratio preset", "preset", "custom", [
          ["custom", "Custom"],
          ["square", "Square 1:1"],
          ["portrait", "Portrait 4:5"],
          ["story", "Story / short video 9:16"],
          ["landscape", "Landscape 16:9"],
        ]) +
        input(
          "Output width",
          "width",
          Math.min(m.width, 4096),
          "number",
          'min="16" max="4096" required',
        ) +
        input(
          "Output height",
          "height",
          Math.min(m.height, 4096),
          "number",
          'min="16" max="4096" required',
        ) +
        input("Optional crop: left, top, right, bottom", "crop") +
        '<button type="submit">Create edited PNG copy</button><p class="hint">Resize fits a centered crop to the chosen dimensions. Animated GIF edits export the selected first frame as PNG.</p></form></details>'
      : "") +
    '<div class="media-output"></div></article>'
  );
}
async function analyticsPage() {
  const d = await api("/api/social/analytics");
  return (
    heading(
      "Local analytics",
      "Real local activity. No invented impressions.",
    ) +
    '<div class="notice">' +
    esc(d.note) +
    '</div><div class="card"><h2>AI draft acceptance</h2>' +
    (d.acceptance || [])
      .map(
        (x) =>
          "<p>" +
          platformTag(x.platform) +
          " " +
          Math.round((x.accepted / x.generated) * 100) +
          "% (" +
          x.accepted +
          "/" +
          x.generated +
          ")</p>",
      )
      .join("") +
    '</div><div class="card"><table><thead><tr><th>Platform</th><th>Action</th><th>Status</th><th>Count</th></tr></thead><tbody>' +
    d.activity
      .map(
        (x) =>
          "<tr><td>" +
          platformTag(x.platform) +
          "</td><td>" +
          esc(x.action) +
          "</td><td>" +
          esc(x.status) +
          "</td><td>" +
          x.count +
          "</td></tr>",
      )
      .join("") +
    '</tbody></table></div><div class="grid"><div class="card"><h2>Top topics</h2>' +
    d.topics
      .map((x) => "<p>" + esc(x.topic) + ": " + x.count + "</p>")
      .join("") +
    '</div><div class="card"><h2>Accounts engaged with</h2>' +
    d.accounts
      .map(
        (x) =>
          "<p>" +
          platformTag(x.platform) +
          " " +
          esc(x.target_account) +
          ": " +
          x.count +
          "</p>",
      )
      .join("") +
    "</div></div>"
  );
}
async function socialHome(d) {
  accountsCache = await api("/api/social/accounts");
  const b = await api("/api/social/brief");
  await refreshChatGPT();
  return (
    '<section class="card hero"><div class="eyebrow">YOUR MULTI-SOCIAL COMMAND CENTER</div><h1>Better conversations.<br>Still your call.</h1><p>Discover what deserves your attention, find your words, and review every public action.</p><div class="row"><a class="btn" href="#terminal">Open AI Terminal</a><a class="btn" href="#automations">Automations</a><a class="btn" href="#queue">Review Replies</a><a class="btn" href="#create">Create Post</a><a class="btn" href="#media">Upload Image</a><a class="btn" href="#watchlist">Add Watch Account</a><a class="btn" href="#trends">Explore Trends</a></div></section><div class="stats">' +
    [
      ["Needs review", b.needs_review],
      ["High priority", b.high_priority_count || 0],
      ["Scheduled", d.scheduled],
      ["Today's API writes", d.today_writes],
    ]
      .map(
        ([l, v]) =>
          '<div class="stat"><small>' +
          l +
          "</small><strong>" +
          v +
          "</strong></div>",
      )
      .join("") +
    '</div>'+chatgptCard()+'<div class="grid"><div class="card"><h2>Connected accounts</h2>' +
    accountsCache
      .map(
        (a) =>
          "<p>" +
          platformTag(a.platform) +
          " " +
          esc(a.connected ? a.account.name : "Not connected") +
          (a.paused?.message ? " &middot; " + esc(a.paused?.message) : "") +
          "</p>",
      )
      .join("") +
    '<a href="#settings">Manage connections</a><p>AI: ' +
    esc(d.provider) +
    " / " +
    esc(d.model) +
    '</p></div><div class="card"><h2>Daily Brief</h2><p>' +
    esc(b.recommendation) +
    "</p><p>" +
    b.mentions +
    " imported mentions &middot; " +
    b.comments +
    " comments</p>" +
    b.trends
      .map(
        (t) =>
          "<p>" + esc(t.name) + " &middot; " + t.current + " local items</p>",
      )
      .join("") +
    '<div class="row"><a class="btn" href="#planner">AI Planner</a><a class="btn" href="#listener">Social Listener</a>' +
    msButton("Suggest daily actions", "daily-advice") +
    '</div><div id="daily-advice"></div></div></div>'
  );
}
function listenerPage() {
  return (
    heading(
      "Social Listener",
      "Assistant Mode prepares opportunities. It cannot auto-send replies.",
    ) +
    '<form id="listener-form" class="card">' +
    check(
      "Enable Assistant Mode: monitor, rank, draft and notify",
      "assistant_mode",
      config.assistant_mode,
    ) +
    input(
      "Polling interval (minutes)",
      "poll_minutes",
      config.poll_minutes,
      "number",
      'min="15" max="1440" required',
    ) +
    input(
      "Daily requests per social provider",
      "social_daily_request_cap",
      config.social_daily_request_cap,
      "number",
      'min="1" max="1000" required',
    ) +
    input(
      "Maximum feed items shown",
      "social_max_feed",
      config.social_max_feed,
      "number",
      'min="20" max="1000" required',
    ) +
    '<button type="submit">Save Assistant Mode</button><p class="hint">This is an opt-in paid-usage boundary. At most two local items are analyzed per pass, subject to the global AI limit. Account APIs and watchlists obey polling intervals. X paid search retains its own daily cap.</p></form>'
  );
}
function plannerPage() {
  return (
    heading(
      "AI Planner",
      "A suggested weekly rhythm, never an automatic posting campaign.",
    ) +
    '<div class="card"><p>Uses your tracked interests, observed trends, saved ideas, profile and recent local publishing history.</p>' +
    msButton("Suggest a weekly plan", "weekly-plan", "", "") +
    '<div id="weekly-plan"></div></div>'
  );
}

function safeRemoteImage(value) {
  try {
    const u = new URL(value);
    return (
      u.protocol === "https:" &&
      [
        "pbs.twimg.com",
        "fbcdn.net",
        "cdninstagram.com",
        "ytimg.com",
        "ggpht.com",
        "googleusercontent.com",
        "licdn.com",
        "tiktokcdn.com",
        "tiktokcdn-us.com",
      ].some((h) => u.hostname === h || u.hostname.endsWith("." + h))
    );
  } catch {
    return false;
  }
}
