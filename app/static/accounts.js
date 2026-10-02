let accountsCache = [];
function accountsPage() {
  return (
    "<h2>Connected Accounts</h2><p>Authorize through each platform in your browser. Never enter a social-media password here.</p>" +
    accountsCache
      .map(
        (a) =>
          '<article class="card"><div class="row between"><h2>' +
          esc(a.name) +
          '</h2><span class="pill ' +
          (a.connected ? "green" : "") +
          '">' +
          (a.connected ? "Connected" : "Not connected") +
          "</span></div><p>" +
          esc(a.account.name || "No account selected") +
          "<br>" +
          esc(a.note) +
          '</p><p class="hint">API: ' +
          esc(a.paused.message || a.account.api_status || "Not tested") +
          "<br>Last synchronization: " +
          esc(fmt(a.account.last_sync)) +
          '</p><div class="chips">' +
          Object.entries(a.capabilities)
            .filter(([k, v]) => v)
            .map(
              ([k]) =>
                '<span class="pill">' +
                esc(k.replace("can_", "").replaceAll("_", " ")) +
                "</span>",
            )
            .join("") +
          '</div><details><summary>View permissions &amp; capabilities</summary><p class="hint">Reported granted permissions: ' +
          esc(
            a.account.permissions ||
              "Not returned by provider; verify in the platform account settings.",
          ) +
          "<br>Requested by this adapter: " +
          esc(a.scopes || a.account.permissions || "") +
          '<br>API capabilities require account permissions and provider access. Unsupported actions use copy-and-open.</p></details><div class="row">' +
          (a.platform === "x"
            ? btn("X Connection settings", "settings-tab", "x")
            : btn(
                a.connected ? "Reconnect" : "Connect",
                "social-connect",
                a.platform,
              )) +
          btn("Test Connection", "social-test", a.platform) +
          (a.connected
            ? btn("Disconnect", "social-disconnect", a.platform)
            : "") +
          btn(
            "Delete account data",
            "social-delete-data",
            a.platform,
            "danger",
          ) +
          "</div>" +
          (a.choices.length
            ? '<div class="notice">Select the Page you want to manage:' +
              a.choices
                .map((p) => btn(esc(p.name), "social-select-page", p.id))
                .join("") +
              "</div>"
            : "") +
          (a.platform !== "x"
            ? '<details><summary>OAuth app configuration</summary><form class="social-account-form" data-platform="' +
              a.platform +
              '">' +
              input(
                "OAuth Client ID / Client key",
                "client_id",
                a.config.client_id || "",
              ) +
              input(
                "Registered callback URL",
                "redirect_uri",
                a.config.redirect_uri,
                "url",
                "required",
              ) +
              '<p class="hint">Register this exact callback with your developer app. If the provider requires HTTPS, use your own registered callback and paste its returned URL below. This app does not host a callback relay.</p><div class="row"><span id="social-secret-' +
              a.platform +
              '" class="secret">' +
              esc(a.secret || "Not saved") +
              "</span>" +
              btn("Reveal temporarily", "social-reveal", a.platform) +
              btn("Delete secret", "social-delete-secret", a.platform) +
              "</div>" +
              input(
                "Replace OAuth Client Secret (never your account password)",
                "client_secret",
                "",
                "password",
                'autocomplete="new-password"',
              ) +
              '<button type="submit">Save OAuth configuration</button></form><form class="social-callback-form" data-platform="' +
              a.platform +
              '">' +
              input(
                "Returned callback URL (only when needed)",
                "url",
                "",
                "url",
                'required autocomplete="off"',
              ) +
              '<button type="submit">Complete authorization</button></form></details>'
            : "") +
          "</article>",
      )
      .join("") +
    '<div class="notice">Future networks can be added through the SocialProvider adapter interface. No scraping or cookie imports.</div>'
  );
}
async function socialAccountAction(a, id) {
  const root = "/api/social/accounts/" + id;
  if (a === "social-connect") {
    const d = await api(root + "/connect", "POST");
    openExternal(d.url);
    toast(
      "Complete authorization in the official browser window, then refresh Connected Accounts.",
    );
    return;
  }
  if (a === "social-test") {
    await api(root + "/test", "POST");
    toast("Connection tested");
    return render();
  }
  if (a === "social-disconnect") {
    if (!confirm("Disconnect this provider locally? Saved drafts remain."))
      return;
    const d = await api(root + "/disconnect", "POST");
    toast(d.note);
    return render();
  }
  if (a === "social-select-page") {
    await api("/api/social/accounts/facebook/select", "POST", { id });
    return render();
  }
  if (a === "social-reveal") {
    const d = await api(root + "/secret/reveal", "POST"),
      el = $("#social-secret-" + id);
    el.textContent = d.value;
    setTimeout(() => {
      if (el.isConnected)
        el.textContent =
          accountsCache.find((x) => x.platform === id)?.secret || "Not saved";
    }, 15000);
    return;
  }
  if (a === "social-delete-secret") {
    if (confirm("Delete this OAuth app secret?"))
      await api(root + "/secret", "DELETE");
    return render();
  }
  if (a === "social-delete-data") {
    if (
      confirm(
        "Delete locally stored content, drafts, history, and connection for this platform? This does not delete anything on the social platform.",
      )
    )
      await api(root + "/data", "DELETE");
    return render();
  }
}
async function socialAccountSubmit(f) {
  const id = f.dataset.platform,
    d = values(f);
  if (f.classList.contains("social-callback-form")) {
    await api("/api/social/accounts/" + id + "/complete", "POST", d);
    f.reset();
  } else {
    await api("/api/social/accounts/" + id + "/config", "PUT", d);
    f.elements.client_secret.value = "";
  }
  toast("Saved");
  return render();
}

let usageCache = {};
function extendedSettings() {
  if (settingsTab === "usage")
    return (
      "<h2>API Usage</h2><p>" +
      esc(usageCache.note || "") +
      '</p><div class="notice">X API searches today: ' +
      (usageCache.search?.searches_today || 0) +
      " / " +
      (usageCache.search?.daily_limit || 0) +
      "<br>Posts retrieved: " +
      (usageCache.search?.posts_retrieved_today || 0) +
      "<br>AI generations today: " +
      (usageCache.ai_today || 0) +
      " / " +
      config.daily_ai_limit +
      "</div><table><tr><th>Provider</th><th>Operation</th><th>Status</th><th>Requests</th></tr>" +
      (usageCache.items || [])
        .map(
          (x) =>
            "<tr><td>" +
            esc(x.platform) +
            "</td><td>" +
            esc(x.operation) +
            "</td><td>" +
            esc(x.status) +
            "</td><td>" +
            x.requests +
            "</td></tr>",
        )
        .join("") +
      '</table><a class="btn" href="#listener">Assistant Mode & polling limits</a>'
    );
  const kind = settingsTab === "memory" ? "my_profile" : "brand_voice",
    fields =
      kind === "my_profile"
        ? [
            "Name",
            "Role",
            "Bio",
            "Industry",
            "Expertise",
            "Products",
            "Audience",
            "Goals",
          ]
        : [
            "Tone",
            "Humor level",
            "Technical level",
            "Preferred sentence length",
            "Emoji preference",
            "Words to avoid",
            "Favorite phrases",
            "Banned phrases",
          ];
  return (
    '<form id="structured-profile-form" data-kind="' +
    kind +
    '"><h2>' +
    (kind === "my_profile" ? "My Profile" : "Brand Voice") +
    "</h2>" +
    fields.map((k) => {const key=kind==="my_profile"?k.toLowerCase():k;return area(k,key,config[kind]?.[key]||"",'maxlength="'+(kind==="my_profile"?({name:160,role:240,industry:240}[key]||4000):4000)+'"')}).join("") +
    '<button type="submit">Save</button></form>'
  );
}
function imageProviderFields() {
  return (
    '<hr class="divider"><form id="image-provider-form"><h2>Image generation provider</h2><p>A separate OpenAI-compatible image endpoint returning base64 image data. Image generation happens only when you request it in Media.</p>' +
    input(
      "Image API base URL",
      "endpoint",
      config.image_provider?.endpoint || "",
      "url",
    ) +
    input("Image model", "model", config.image_provider?.model || "") +
    secretField("image_api_key", "Image API key") +
    '<button type="submit">Save image provider</button></form>'
  );
}
