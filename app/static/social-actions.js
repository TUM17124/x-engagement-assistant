async function saveSocialEdit(id) {
  const d = socialDrafts.find((d) => d.id === Number(id));
  if (!d) throw Error("Reload the inbox and try again.");
  const text = $('[name="social-draft-' + id + '"]').value;
  const selected = [...$('[name="media-edit-' + id + '"]').selectedOptions].map(
    (o) => o.value,
  );
  if (text !== d.text || JSON.stringify(selected) !== d.media_ids) {
    Object.assign(
      d,
      await api("/api/social/drafts/" + id, "PUT", {
        platform: d.platform,
        kind: d.kind,
        feed_id: d.feed_id,
        text,
        media_ids: selected,
      }),
    );
  }
  return d;
}
function suggestionOutput(text) {
  return (
    '<div class="preview">' +
    esc(text) +
    "</div>" +
    msButton("Save as idea", "save-suggestion", "", "ghost")
  );
}
async function msAction(a, id, el) {
  if(a==='delete-draft'){
    const draft=socialDrafts.find(d=>d.id===Number(id));
    if(!draft)throw Error('Reload the inbox and try again.');
    if(!confirm('Delete this local draft and cancel its schedule?\n\n'+draft.text))return;
    const result=await api('/api/drafts/'+id,'DELETE');toast(result.message);return render();
  }
  if (a === "analyze") {
    const d = await api("/api/social/analyze", "POST", { id });
    toast(d.skipped ? "AI skipped this item." : "Response ready for review");
    inboxTab = "review";
    location.hash = "queue";
    return render();
  }
  if (a === "mute") {
    const f = socialItems.find((f) => f.id === id);
    await api("/api/social/mute", "POST", {
      platform: f.platform,
      author: f.username,
    });
    return render();
  }
  if (a === "sync" || a === "mentions") {
    const d = await api("/api/social/sync/" + id, "POST", {
      kind: a === "mentions" ? "mentions" : "feed",
    });
    toast(d.items.length + " authorized items imported");
    return render();
  }
  if (a === "inbox-tab") {
    inboxTab = id;
    return render();
  }
  if (a === "save") {
    await saveSocialEdit(id);
    inboxTab = "review";
    return render();
  }
  if (a === "approve") {
    await saveSocialEdit(id);
    await api("/api/drafts/" + id + "/approve", "POST");
    inboxTab = "approved";
    return render();
  }
  if (a === "publish") {
    await saveSocialEdit(id);
    if (!confirm("Publish this exact approved platform version now?")) return;
    await api("/api/drafts/" + id + "/publish", "POST");
    toast("Published");
    return render();
  }
  if (a === "manual") {
    await saveSocialEdit(id);
    const d = await api("/api/social/drafts/" + id + "/manual", "POST");
    try {
      await navigator.clipboard.writeText(d.text);
      toast(
        "Copied. Finish publishing in the platform; this is recorded only as opened.",
      );
    } catch {
      toast(
        "Copy the text from the editable draft, then publish on the platform.",
      );
    }
    openExternal(d.url);
    return;
  }
  if (a === "rewrite") {
    const d = await saveSocialEdit(id),
      style = $('[name="social-style-' + id + '"]').value;
    if (d.feed_id) {
      await api("/api/social/analyze", "POST", {
        id: d.feed_id,
        draft_id: d.id,
        style: style === "Regenerate" ? "" : style,
      });
    } else {
      const result = await api("/api/social/suggest", "POST", {
        task: style,
        text: d.text,
        platform: d.platform,
      });
      await api("/api/social/drafts/" + id, "PUT", {
        platform: d.platform,
        kind: d.kind,
        feed_id: d.feed_id,
        text: result.text,
        generated_text: result.text,
        media_ids: JSON.parse(d.media_ids || "[]"),
      });
    }
    inboxTab = "review";
    return render();
  }
  if (a === "schedule") {
    await saveSocialEdit(id);
    const card = el.closest("article");
    if (card.querySelector(".social-schedule-form")) return;
    const f = document.createElement("form");
    f.className = "social-schedule-form notice";
    f.dataset.id = id;
    const d = socialDrafts.find((d) => d.id === Number(id)),
      account = accountsCache.find((a) => a.platform === d.platform);
    const apiSupported =
      d.kind === "original" && account?.capabilities.can_publish &&
      (!JSON.parse(d.media_ids || "[]").length ||
        account.capabilities.can_upload_images);
    f.innerHTML =
      input("Local date/time", "due", "", "datetime-local", "required") +
      select("Delivery", "delivery", apiSupported ? "api" : "manual", [
        ...(apiSupported
          ? [["api", "Publish this approved version through API"]]
          : []),
        ["manual", "Remind me to publish manually"],
      ]) +
      '<p class="hint">Keep the app running. Missed schedules are never replayed automatically.</p><button type="submit">Confirm this exact schedule</button>';
    card.append(f);
    return;
  }
  if (a === "duplicate") {
    const platform = prompt(
      "Target platform: x, facebook, instagram, linkedin, threads, tiktok, youtube",
    );
    if (!platform) return;
    await api("/api/social/drafts/" + id + "/duplicate", "POST", { platform });
    inboxTab = "review";
    toast("Separate draft created. Adapt and review it before approval.");
    return render();
  }
  if (a === "adapt") {
    const f = $("#cross-compose-form");
    createBrief = f.elements.brief.value;
    selectedPlatforms = new FormData(f).getAll("platform");
    if (!selectedPlatforms.length || selectedPlatforms.length > 3)
      throw Error("Choose 1-3 platforms per AI action.");
    if (!createBrief.trim())
      throw Error("Add your source facts or brief first.");
    for (const p of selectedPlatforms) {
      const d = await api("/api/social/suggest", "POST", {
        task: f.elements.task.value,
        text: createBrief,
        platform: p,
      });
      createVersions[p] = {
        text: d.text,
        generated: d.text,
        quality: d.quality,
      };
    }
    return render();
  }
  if (a === "save-suggestion") {
    const text = el.previousElementSibling.textContent;
    await api("/api/social/ideas", "POST", {
      title: text.slice(0, 80),
      text,
      kind: "AI suggestion",
    });
    toast("Saved to Ideas");
    return;
  }
  if (a === "use-idea") {
    const i = ideaCache.find((i) => i.id === Number(id));
    createBrief = i.text;
    location.hash = "create";
    return render();
  }
  if (a === "delete-idea") {
    if (confirm("Delete this saved idea?"))
      await api("/api/social/ideas/" + id, "DELETE");
    return render();
  }
  if (a === "delete-watch") {
    if (confirm("Remove this watch?"))
      await api("/api/social/watch/" + id, "DELETE");
    return render();
  }
  if (a === "edit-watch") {
    const all = (
      await Promise.all(
        ["favorite", "competitor", "industry", "keyword", "brand"].map((c) =>
          api("/api/social/watch?category=" + c),
        ),
      )
    ).flat();
    const w = all.find((w) => w.id === Number(id)),
      f = $("#social-watch-form");
    f.dataset.id = id;
    for (const [key, value] of Object.entries(w)) {
      const input = f.elements[key];
      if (input) {
        if (input.type === "checkbox") input.checked = !!value;
        else input.value = value;
      }
    }
    f.scrollIntoView({ behavior: "smooth" });
    return;
  }
  if (a === "market-summary") {
    const d = await api("/api/social/market");
    const evidence = d
      .filter((x) => x.matches.length)
      .map((x) => ({
        name: x.watch.handle,
        posts: x.matches.map((m) => m.text.slice(0, 500)),
      }));
    if (!evidence.length)
      throw Error(
        "Import matching authorized content first. There is no evidence to summarize yet.",
      );
    const r = await api("/api/social/suggest", "POST", {
      task: "Summarize announcements, messaging, pain points and feature requests only where supported by this evidence. Explain uncertainty.",
      text: JSON.stringify(evidence),
    });
    $("#market-summary").innerHTML = suggestionOutput(r.text);
    return;
  }
  if (a === "weekly-plan" || a === "daily-advice") {
    const task =
      a === "weekly-plan"
        ? "Weekly plan"
        : "Recommend a few useful daily actions with reasons; no volume target";
    const d = await api("/api/social/suggest", "POST", {
      task,
      platform:a === "weekly-plan" ? $('[name="planner_platform"]').value : 'x',
      timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,
      text:
        a === "daily-advice"
          ? JSON.stringify(await api("/api/social/brief"))
          : $('[name="planner_goal"]').value,
    });
    const target=$("#" + a);if(target)target.innerHTML = suggestionOutput(d.text);
    toast(a === "weekly-plan" ? "Weekly plan saved locally. Nothing was scheduled." : "Suggestions ready");
    return;
  }
  if (a === "media-assist") {
    if (
      !confirm(
        "Send a resized copy of this image to your configured AI provider for caption and alt-text suggestions?",
      )
    )
      return;
    const d = await api("/api/media/" + id + "/assist", "POST", {});
    el.closest("article").querySelector(".media-output").innerHTML =
      suggestionOutput(d.text);
    return;
  }
  if (a === "media-usage") {
    const d = await api("/api/media/" + id + "/usage");
    el.closest("article").querySelector(".media-output").innerHTML =
      '<p class="hint">' +
      (d.length
        ? d
            .map((x) =>
              esc(x.platform + " / " + x.status + " / " + fmt(x.used_at)),
            )
            .join("<br>")
        : "No recorded API publishing use yet.") +
      "</p>";
    return;
  }
  if (a === "media-reuse") {
    createBrief =
      "Create a post using " +
      mediaCache.find((m) => m.id === id).name +
      ". Describe your intended message here.";
    location.hash = "create";
    return render();
  }
  if (a === "media-delete") {
    if (confirm("Delete this local media file?"))
      await api("/api/media/" + id, "DELETE");
    return render();
  }
  if (a === "clear-data") {
    if (
      prompt(
        "This deletes the local workspace and media. Type DELETE to continue.",
      ) !== "DELETE"
    )
      return;
    await api("/api/social/data", "DELETE", { confirm: "DELETE" });
    return start();
  }
  throw Error('This action is unavailable in this app version. Refresh the page and try again.');
}
async function msSubmit(f) {
  const d = values(f);
  if (f.id === "social-feed-filter") {
    socialPlatform = d.platform;
    socialFilter = d.filter;
    return render();
  }
  if (f.id === "social-import-form") {
    await api("/api/social/import", "POST", d);
    toast("Content imported locally");
    return render();
  }
  if (f.classList.contains("social-comments-form")) {
    const r = await api("/api/social/sync/" + f.dataset.platform, "POST", {
      kind: "comments",
      target: d.target,
    });
    toast(r.items.length + " comments imported");
    return render();
  }
  if (f.id === "cross-compose-form") {
    createBrief = d.brief;
    selectedPlatforms = new FormData(f).getAll("platform");
    if (!selectedPlatforms.length) throw Error("Select a platform.");
    for (const p of selectedPlatforms)
      createVersions[p] ??= { text: createBrief, generated: "" };
    return render();
  }
  if (f.classList.contains("platform-version-form")) {
    const platform = f.dataset.platform;
    const selected = [...f.elements.media_ids.selectedOptions].map(
      (o) => o.value,
    );
    await api("/api/social/drafts", "POST", {
      platform,
      text: d.text,
      kind: "original",
      media_ids: selected,
      generated_text: createVersions[platform]?.generated || "",
    });
    createVersions[platform].text = d.text;
    toast("Saved for approval in Response Inbox");
    return;
  }
  if (f.classList.contains("social-schedule-form")) {
    await api("/api/social/drafts/" + f.dataset.id + "/schedule", "POST", {
      due_at: new Date(d.due).toISOString(),
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      delivery: d.delivery,
    });
    location.hash = "schedule";
    return render();
  }
  if (f.classList.contains("trend-idea-form")) {
    const trend = (await api("/api/social/trends")).find(
      (t) => t.name === f.dataset.topic,
    );
    const r = await api("/api/social/suggest", "POST", {
      task: d.task,
      text: JSON.stringify(trend),
    });
    f.parentElement.querySelector(".suggestion-output").innerHTML =
      suggestionOutput(r.text);
    return;
  }
  if (f.id === "social-watch-form") {
    if (f.dataset.id) d.id = Number(f.dataset.id);
    for (const k of ["enabled", "notifications", "auto_draft"])
      d[k] = f.elements[k].checked;
    await api("/api/social/watch", "POST", d);
    return render();
  }
  if (f.id === "idea-form") {
    await api("/api/social/ideas", "POST", d);
    return render();
  }
  if (f.id === "media-upload-form") {
    await api("/api/media", "POST", new FormData(f));
    toast("Media saved locally");
    return render();
  }
  if (f.id === "media-filter-form") {
    mediaCache = await api(
      "/api/media?" +
        new URLSearchParams({
          q: d.q,
          folder: d.folder,
          favorite: f.elements.favorite.checked,
        }),
    );
    $("#media-grid").innerHTML = mediaCache.map(mediaCard).join("");
    return;
  }
  if (f.id === "image-generation-form") {
    await api("/api/media/generate/image", "POST", d);
    toast("Generated image saved locally");
    return render();
  }
  if (f.classList.contains("media-metadata-form")) {
    d.favorite = f.elements.favorite.checked;
    await api("/api/media/" + f.dataset.id, "PUT", d);
    toast("Media details saved");
    return;
  }
  if (f.classList.contains("media-transform-form")) {
    const crop = d.crop.trim() ? d.crop.split(",").map(Number) : null;
    await api("/api/media/" + f.dataset.id + "/transform", "POST", {
      width: Number(d.width),
      height: Number(d.height),
      crop,
    });
    toast("A new image copy was created");
    return render();
  }
  if (f.id === "listener-form") {
    const next = {
      assistant_mode: f.elements.assistant_mode.checked,
      poll_minutes: Number(d.poll_minutes),
      social_daily_request_cap: Number(d.social_daily_request_cap),
      social_max_feed: Number(d.social_max_feed),
    };
    await api("/api/settings", "PUT", next);
    Object.assign(config, next);
    toast("Assistant Mode settings saved");
    return render();
  }
  if (f.id === "image-provider-form") {
    await api("/api/settings", "PUT", {
      image_provider: { endpoint: d.endpoint, model: d.model },
    });
    await saveSecrets(f, ["image_api_key"]);
    config.image_provider = { endpoint: d.endpoint, model: d.model };
    toast("Image provider saved");
    return;
  }
  if (f.id === "structured-profile-form") {
    if(f.dataset.kind==="my_profile"){
      config.my_profile=await api("/api/profile","PUT",d);
      toast("Profile saved");
      reportWork({state:"completed",message:"Profile saved"});
    }else{
      await api("/api/settings","PUT",{brand_voice:d});config.brand_voice=d;
      toast("Brand voice saved");
      reportWork({state:"completed",message:"Brand voice saved"});
    }
    return;
  }
}
const socialFormIds = new Set([
  "social-feed-filter",
  "social-import-form",
  "cross-compose-form",
  "social-watch-form",
  "idea-form",
  "media-upload-form",
  "media-filter-form",
  "image-generation-form",
  "listener-form",
  "image-provider-form",
  "structured-profile-form",
]);
function isSocialForm(f) {
  return (
    socialFormIds.has(f.id) ||
    [
      "social-comments-form",
      "platform-version-form",
      "social-schedule-form",
      "trend-idea-form",
      "media-metadata-form",
      "media-transform-form",
    ].some((c) => f.classList.contains(c))
  );
}
document.addEventListener("input", (e) => {
  const f = e.target.closest(".platform-version-form");
  if (f && e.target.name === "text") {
    createVersions[f.dataset.platform].text = e.target.value;
    f.querySelector(".preview").textContent = e.target.value;
  }
  if (e.target.name === "brief") createBrief = e.target.value;
});
document.addEventListener("change", (e) => {
  if (e.target.name === "preset") {
    const sizes = {
        square: [1080, 1080],
        portrait: [1080, 1350],
        story: [1080, 1920],
        landscape: [1920, 1080],
      },
      size = sizes[e.target.value];
    if (size) {
      e.target.form.elements.width.value = size[0];
      e.target.form.elements.height.value = size[1];
    }
  }
});
