const fs = require("fs"),
  vm = require("vm"),
  assert = require("assert");
const ctx = {
  console,
  URLSearchParams,
  FormData,
  Date,
  setTimeout,
  clearTimeout,
  URL,
  document: {
    addEventListener() {},
    querySelector() {
      return null;
    },
  },
  window: { addEventListener() {} },
  location: { hash: "" },
};
vm.createContext(ctx);
for (const file of [
  "app",
  "settings",
  "feed",
  "screens",
  "actions",
  "accounts",
  "social",
  "social-actions",
  "terminal",
])
  vm.runInContext(fs.readFileSync("app/static/" + file + ".js", "utf8"), ctx, {
    filename: file + ".js",
  });
vm.runInContext(
  `
config={onboarded:true,ai_provider:'gemini',ai_model:'test',interests:[],theme:'dark',image_provider:{},social_max_feed:200,social_daily_request_cap:100};
const account={platform:'facebook',name:'Facebook Pages',home:'https://facebook.com/',limit:63206,note:'Test permissions',connected:false,account:{},capabilities:{can_manual:true},config:{},choices:[]};
const emptyAPI={
 '/api/terminal/automations':{items:[],runs:[],paused:false},'/api/chatgpt/status':{connected:false,profiles:[],state:'Disconnected'},'/api/social/accounts':[account],'/api/social/brief':{needs_review:0,high_priority:[],high_priority_count:0,mentions:0,comments:0,scheduled:[],trends:[],recommendation:'Review useful items'},
 '/api/social/analytics':{activity:[],topics:[],accounts:[],drafts:[],acceptance:[],note:'Local only'},
};
api=async path=>emptyAPI[path]||[];
`,
  ctx,
);
(async () => {
  for (const expr of [
    "terminalPage()",
    "automationPage()",
    "controlApprovalsPage()",
    "writingMemoryPage()",
    "socialFeedPage()",
    "responseInboxPage()",
    "trendPage()",
    "createPage()",
    "watchSocialPage()",
    "watchSocialPage(true)",
    "ideasPage()",
    "mediaPage()",
    "analyticsPage()",
    'socialHome({today_writes:0,scheduled:0,provider:"gemini",model:"test"})',
  ]) {
    const html = await vm.runInContext(expr, ctx);
    assert(typeof html === "string" && html.length > 100, expr);
    assert(!html.includes("[object Object]"), expr);
  }
  const html = vm.runInContext(
    `responseCard({id:1,platform:'instagram',status:'approved',kind:'original',text:'Caption',score:0,media_ids:'[]',quality:'[]'})`,
    ctx,
  );
  assert(
    html.includes("Copy &amp; open manually") ||
      html.includes("Copy & open manually"),
  );
  assert(
    !html.includes("Post Now (API)"),
    "Unsupported publishing button must be hidden",
  );
  vm.runInContext(
    `accountsCache=[{...account,connected:true,capabilities:{can_publish:true,can_upload_images:true}}];mediaCache=[{id:'video',name:'video.mp4',mime:'video/mp4'}]`,
    ctx,
  );
  const video = vm.runInContext(
    `responseCard({id:2,platform:'facebook',status:'approved',kind:'original',text:'Caption',score:0,media_ids:'["video"]',quality:'[]'})`,
    ctx,
  );
  assert(
    !video.includes("Post Now (API)"),
    "Unsupported video publishing must use manual handoff",
  );
  assert(
    vm
      .runInContext(`nav.map(n=>n[2]).join(',')`, ctx)
      .includes("Response Inbox"),
  );
  console.log(
    "Multi-social screen rendering and capability-based action checks passed.",
  );
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
