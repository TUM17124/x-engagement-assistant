'use strict';
let csrf='',config={},secretMasks={},profile=null,route='home',onStep=0,editingWatch=null,editingTopic=null;
let draftCache=[],feedCache=[],scheduleMode='queue',approvalTab='reply',settingsTab='accounts',composing=null;
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=v=>v?new Date(v).toLocaleString():'Not available';
const btn=(l,a,id='',cls='ghost',extra='')=>'<button type="button" class="'+cls+'" data-action="'+a+'" data-id="'+esc(id)+'" '+extra+'>'+l+'</button>';
const link=(l,u,cls='btn ghost')=>'<a class="'+cls+'" href="'+esc(u)+'" target="_blank" rel="noopener noreferrer">'+l+'</a>';
const input=(l,n,v='',t='text',x='')=>'<label>'+l+'<input name="'+n+'" type="'+t+'" value="'+esc(v)+'" '+x+'></label>';
const area=(l,n,v='',x='')=>'<label>'+l+'<textarea name="'+n+'" '+x+'>'+esc(v)+'</textarea></label>';
const check=(l,n,v)=>'<label class="check"><input type="checkbox" name="'+n+'" '+(v?'checked':'')+'>'+l+'</label>';
const select=(l,n,v,opts)=>'<label>'+l+'<select name="'+n+'">'+opts.map(o=>{const [k,t]=Array.isArray(o)?o:[o,o];return '<option value="'+esc(k)+'" '+(v===k?'selected':'')+'>'+esc(t)+'</option>'}).join('')+'</select></label>';
const empty=(t,d,a='')=>'<div class="empty"><div class="empty-icon">&#10022;</div><h2>'+t+'</h2><p>'+d+'</p>'+a+'</div>';
function toast(m){const el=$('#toast');el.textContent=m;el.style.display='block';clearTimeout(toast.timer);toast.timer=setTimeout(()=>el.style.display='none',7000)}
function responseError(data,status){
 const fields=Array.isArray(data?.detail)?data.detail.map(d=>{const name=(d.loc||[]).filter(x=>x!=='body').join(' / ');return (name?name+': ':'')+(d.msg||'Check this value');}).join('; '):'';
 const defaults={401:'This connection needs authorization. Open Settings and test the selected provider.',403:'This action is not permitted. Check the connection and permissions in Settings.',404:'This action or item is no longer available. Refresh the page.',413:'The file is too large. Choose a smaller file.',422:'Check the required fields and try again.',429:'The service is rate limited. Wait before trying again.'};
 const e=Error(data?.error||(typeof data?.detail==='string'?data.detail:fields)||defaults[status]||'The app could not complete this request. Check History before repeating a publishing action.');
 e.status=status;e.technical=data?.technical||('App HTTP '+status);e.hint=data?.hint||'';return e;
}
async function api(path,method='GET',body,options={}){
 const multi=body instanceof FormData,controller=new AbortController();
 const timer=setTimeout(()=>controller.abort(),options.timeoutMs??(method==='GET'?30000:180000));
 let response;
 try{
  response=await fetch(path,{method,signal:controller.signal,headers:{...(!multi?{'Content-Type':'application/json'}:{}),'X-CSRF-Token':csrf},...(body!==undefined?{body:multi?body:JSON.stringify(body)}:{})});
  if(response.status===204)return {};
  let data;try{data=await response.json()}catch(error){if(error.name==='AbortError')throw error;throw responseError({error:'The app returned an unreadable response. Reopen the app; check History before retrying a publishing action.'},response.status)}
  if(!response.ok)throw responseError(data,response.status);return data;
 }catch(error){
  if(error.name==='AbortError'||error instanceof TypeError){
   const e=Error(error.name==='AbortError'?'This request took too long. Check your connection and the selected provider.':'The local app connection was interrupted. Reopen the app and check your connection.');
   e.hint=method==='GET'?'Try again after the connection is restored.':'The operation may have finished even though no response arrived. Check History or the relevant list before trying again; publishing was not retried automatically.';throw e;
  }throw error;
 }finally{clearTimeout(timer)}
}
function errorPanel(error,action=''){
 $('#page-error')?.remove();const el=document.createElement('div');el.id='page-error';el.className='error-box';el.setAttribute('role','alert');el.tabIndex=-1;
 el.innerHTML='<strong>'+esc(action?String(action).trim()+' could not finish':'Something needs attention')+'</strong><p>'+esc(error?.message||'The action could not be completed.')+'</p>'+(error?.hint?'<p>'+esc(error.hint)+'</p>':'')+(error?.technical?'<details><summary>Technical details</summary>'+esc(error.technical)+'</details>':'')+'<div class="row"><a href="#settings">Open Settings</a><a href="#history">Check History</a><button type="button" data-dismiss-error>Dismiss</button></div>';
 ($('.content')||$('.onboarding')||$('#app')).prepend(el);el.scrollIntoView?.({block:'nearest',behavior:'smooth'});el.focus?.({preventScroll:true});
}
async function runUIAction(button,operation,label=''){
 if(button?.dataset.busy)return;
 const title=label||button?.textContent?.trim()||'Action';let progress;
 const disabled=button?.disabled;
 if(button){button.dataset.busy='true';button.disabled=true;button.setAttribute('aria-busy','true')}
 $('#page-error')?.remove();
 try{
  progress=document.createElement('div');progress.className='notice action-progress';progress.setAttribute('role','status');progress.textContent=title+' ? working?';
  ($('.content')||$('.onboarding')||$('#app')).prepend(progress);
  return await operation();
 }catch(error){errorPanel(error,title)}finally{
  progress?.remove();if(button){delete button.dataset.busy;button.disabled=disabled;button.removeAttribute('aria-busy')}
 }
}
document.addEventListener('click',e=>{if(e.target.closest('[data-dismiss-error]'))$('#page-error')?.remove()});
function values(f){return Object.fromEntries(new FormData(f))}
function openExternal(u){if(window.__XEA_DESKTOP__){window.location.href=u}else{window.open(u,'_blank','noopener,noreferrer')}}
const nav=[['home','','Home'],['terminal','','AI Terminal'],['automations','','Automations'],['control-approvals','','Approval Center'],['feed','','Social Feed'],['queue','','Response Inbox'],['trends','','Trend Radar'],['create','','Create'],['schedule','','Schedule'],['watchlist','','Watchlist'],['market','','Market Watch'],['ideas','','Ideas'],['media','','Media'],['analytics','','Analytics'],['history','','History'],['settings','','Settings']];
function heading(t,s,a=''){return '<div class="row between toolbar"><div><div class="eyebrow">YOUR ENGAGEMENT WORKSPACE</div><h1>'+t+'</h1><p>'+s+'</p></div>'+a+'</div>'}
function shell(content,d){document.body.classList.toggle('dim',config.theme==='dim');const label=nav.find(n=>n[0]===route)?.[2]||'Home';$('#app').innerHTML='<div class="app-shell"><aside class="sidebar"><a class="brand" href="#home"><img src="/static/icon.svg" alt=""><div>Social Command<small>AI ENGAGEMENT WORKSPACE</small></div></a><nav class="nav">'+nav.map(([id,icon,t])=>'<a href="#'+id+'" class="'+(id===route?'active':'')+'"><span class="nav-icon">'+navIcon(id)+'</span>'+t+'</a>').join('')+'</nav><div class="sidebar-bottom"><strong>Human in the loop. Always.</strong>Local workspace &middot; v0.3.0<br>AI drafts. You decide.</div></aside><main class="main"><header class="topbar"><span class="crumb">Workspace / '+label+'</span><div class="row"><span class="pill '+(d?.x_connected?'green':'')+'">&#9679; X '+(d?.x_health?.ok===false?'problem':d?.x_connected?'connected':'not connected')+'</span><span class="pill '+(d?.ai_health?.ok?'green':'')+'">&#9679; AI '+(d?.ai_health?.ok?'connected':'not tested / problem')+'</span><span class="pill">&#9679; Scheduler '+esc(d?.scheduler||'Stopped')+'</span><strong>'+esc(d?.profile?'@'+d.profile.username:'Your workspace')+'</strong></div></header><div class="content">'+content+'</div></main></div>'}
let renderVersion=0;
async function render(){const version=++renderVersion;if(!config.onboarded){wizard();return}route=location.hash.slice(1).split('/')[0]||'home';if(!nav.some(n=>n[0]===route)&&!['x-discovery','x-watchlist','compose','approvals','topics','listener','planner','writing-memory'].includes(route))route='home';const health=await api('/api/dashboard');profile=health.profile;let html='';
if(route==='terminal')html=await terminalPage();
if(route==='automations')html=await automationPage();
if(route==='control-approvals')html=await controlApprovalsPage();
if(route==='writing-memory')html=await writingMemoryPage();
if(route==='home')html=await socialHome(health);
if(route==='feed')html=await socialFeedPage();
if(route==='x-discovery')html=feedPage((await api('/api/feed')).filter(f=>f.platform==='x'));
if(route==='queue')html=await responseInboxPage();
if(route==='approvals')html=queuePage((await api('/api/drafts')).filter(d=>d.platform==='x'),true);
if(route==='compose'){feedCache=await api('/api/feed');html=composePage()}
if(route==='schedule')html=schedulePage(await api('/api/schedule'));
if(route==='watchlist')html=await watchSocialPage();
if(route==='x-watchlist')html=watchPage(await api('/api/watchlist'));
if(route==='market')html=await watchSocialPage(true);
if(route==='trends')html=await trendPage();
if(route==='create')html=await createPage();
if(route==='ideas')html=await ideasPage();
if(route==='media')html=await mediaPage();
if(route==='analytics')html=await analyticsPage();
if(route==='listener')html=listenerPage();
if(route==='planner')html=await plannerPage();
if(route==='topics')html=topicsPage(await api('/api/topics'));
if(route==='history')html=heading('Activity history','Your edits, approvals, API results, and manual composer actions.')+'<form id="history-filter" class="row">'+select('Action','action','',['','post','reply','quote','approved','reply_skipped','scheduled','manual_composer_opened'])+select('Status','status','',['','published','approved','skipped','failed','uncertain','opened'])+select('Channel','channel','',['','API','manual','local'])+'<button type="submit">Filter</button></form><div class="card" id="history-results">'+historyTable(await api('/api/history'))+'</div>';
if(route==='settings'){await refreshChatGPT();if(settingsTab==='ai'&&chatgptState.plan_usage&&!chatgptModels.length){try{await refreshChatGPT(true)}catch(e){toast(e.message)}}accountsCache=await api('/api/social/accounts');usageCache=await api('/api/social/usage');secretMasks=(await api('/api/settings')).secrets;html=settingsPage(await api('/api/mutes'))}
if(version===renderVersion){shell(html,health);if(route==='x-discovery')await refreshSearchStatus()}}
async function start(){const d=await api('/api/bootstrap');csrf=d.csrf;config=d.settings;profile=d.profile;await refreshChatGPT();secretMasks=(await api('/api/settings')).secrets;await render();const q=new URLSearchParams(location.search);if(q.get('error'))errorPanel(Error(q.get('error')));if(q.get('ok'))toast(q.get('ok'));history.replaceState(null,'',location.pathname+location.hash)}

const navPaths={"home": "M3 10 12 3 21 10V21H15V14H9V21H3Z", "feed": "M4 4H20V20H4ZM8 8H16M8 12H16M8 16H13", "queue": "M4 5H20M4 12H14M4 19H10M17 16L20 19L23 16", "compose": "M14 5L19 10M4 20L5 14L17 2L22 7L10 19Z", "schedule": "M4 5H20V21H4ZM4 10H20M8 2V7M16 2V7", "approvals": "M9 12L11 14L16 9M12 2L21 6V13Q20 19 12 22Q4 19 3 13V6Z", "watchlist": "M2 12Q12 -2 22 12Q12 26 2 12ZM12 8A4 4 0 1 0 12 16A4 4 0 1 0 12 8", "topics": "M12 2V22M2 12H22M12 4A8 8 0 1 0 12 20A8 8 0 1 0 12 4", "history": "M4 6A9 9 0 1 1 3 16M4 2V7H9M12 7V12L16 14", "settings": "M4 6H20M4 12H20M4 18H20M8 3V9M16 9V15M10 15V21"};
function navIcon(id){return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="'+(navPaths[id]||navPaths.feed)+'"/></svg>'}
