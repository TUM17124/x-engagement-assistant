'use strict';
let csrf='',config={},secretMasks={},profile=null,route='home',onStep=0,editingWatch=null,editingTopic=null;
let draftCache=[],feedCache=[],scheduleMode='queue',approvalTab='reply',settingsTab='x',composing=null;
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
async function api(path,method='GET',body){const multi=body instanceof FormData;const r=await fetch(path,{method,headers:{...(!multi?{'Content-Type':'application/json'}:{}),'X-CSRF-Token':csrf},...(body!==undefined?{body:multi?body:JSON.stringify(body)}:{})});const d=await r.json();if(!r.ok){const e=Error(d.error||(typeof d.detail==='string'?d.detail:'Check the supplied fields.'));e.technical=d.technical;throw e}return d}
function errorPanel(e){$('#page-error')?.remove();const el=document.createElement('div');el.id='page-error';el.className='error-box';el.innerHTML=esc(e.message)+(e.technical?'<details><summary>Technical details</summary>'+esc(e.technical)+'</details>':'');($('.content')||$('.onboarding')||$('#app')).prepend(el)}
function values(f){return Object.fromEntries(new FormData(f))}
function openExternal(u){if(window.__XEA_DESKTOP__){window.location.href=u}else{window.open(u,'_blank','noopener,noreferrer')}}
const nav=[['home','','Home'],['feed','','Feed'],['queue','','Engagement Queue'],['compose','','Compose'],['schedule','','Schedule'],['approvals','','Approval Center'],['watchlist','','Watchlist'],['topics','','Topic Radar'],['history','','History'],['settings','','Settings']];
function heading(t,s,a=''){return '<div class="row between toolbar"><div><div class="eyebrow">YOUR ENGAGEMENT WORKSPACE</div><h1>'+t+'</h1><p>'+s+'</p></div>'+a+'</div>'}
function shell(content,d){document.body.classList.toggle('dim',config.theme==='dim');const label=nav.find(n=>n[0]===route)?.[2]||'Home';$('#app').innerHTML='<div class="app-shell"><aside class="sidebar"><a class="brand" href="#home"><img src="/static/icon.svg" alt=""><div>X Engagement<small>ASSISTANT</small></div></a><nav class="nav">'+nav.map(([id,icon,t])=>'<a href="#'+id+'" class="'+(id===route?'active':'')+'"><span class="nav-icon">'+navIcon(id)+'</span>'+t+'</a>').join('')+'</nav><div class="sidebar-bottom"><strong>Human in the loop. Always.</strong>Local workspace &middot; v0.2.0<br>AI drafts. You decide.</div></aside><main class="main"><header class="topbar"><span class="crumb">Workspace / '+label+'</span><div class="row"><span class="pill '+(d?.x_connected?'green':'')+'">&#9679; X '+(d?.x_health?.ok===false?'problem':d?.x_connected?'connected':'not connected')+'</span><span class="pill '+(d?.ai_health?.ok?'green':'')+'">&#9679; AI '+(d?.ai_health?.ok?'connected':'not tested / problem')+'</span><span class="pill">&#9679; Scheduler '+esc(d?.scheduler||'Stopped')+'</span><strong>'+esc(d?.profile?'@'+d.profile.username:'Your workspace')+'</strong></div></header><div class="content">'+content+'</div></main></div>'}
let renderVersion=0;
async function render(){const version=++renderVersion;if(!config.onboarded){wizard();return}route=location.hash.slice(1).split('/')[0]||'home';if(!nav.some(n=>n[0]===route))route='home';const health=await api('/api/dashboard');profile=health.profile;let html='';
if(route==='home')html=homePage(health);
if(route==='feed')html=feedPage(await api('/api/feed'));
if(['queue','approvals'].includes(route))html=queuePage(await api('/api/drafts'),route==='approvals');
if(route==='compose'){feedCache=await api('/api/feed');html=composePage()}
if(route==='schedule')html=schedulePage(await api('/api/schedule'));
if(route==='watchlist')html=watchPage(await api('/api/watchlist'));
if(route==='topics')html=topicsPage(await api('/api/topics'));
if(route==='history')html=heading('Activity history','Your edits, approvals, API results, and manual composer actions.')+'<form id="history-filter" class="row">'+select('Action','action','',['','post','reply','quote','approved','reply_skipped','scheduled','manual_composer_opened'])+select('Status','status','',['','published','approved','skipped','failed','uncertain','opened'])+select('Channel','channel','',['','API','manual','local'])+'<button type="submit">Filter</button></form><div class="card" id="history-results">'+historyTable(await api('/api/history'))+'</div>';
if(route==='settings'){secretMasks=(await api('/api/settings')).secrets;html=settingsPage(await api('/api/mutes'))}
if(version===renderVersion){shell(html,health);if(route==='feed')await refreshSearchStatus()}}
async function start(){const d=await api('/api/bootstrap');csrf=d.csrf;config=d.settings;profile=d.profile;secretMasks=(await api('/api/settings')).secrets;await render();const q=new URLSearchParams(location.search);if(q.get('error'))errorPanel(Error(q.get('error')));if(q.get('ok'))toast(q.get('ok'));history.replaceState(null,'',location.pathname+location.hash)}

const navPaths={"home": "M3 10 12 3 21 10V21H15V14H9V21H3Z", "feed": "M4 4H20V20H4ZM8 8H16M8 12H16M8 16H13", "queue": "M4 5H20M4 12H14M4 19H10M17 16L20 19L23 16", "compose": "M14 5L19 10M4 20L5 14L17 2L22 7L10 19Z", "schedule": "M4 5H20V21H4ZM4 10H20M8 2V7M16 2V7", "approvals": "M9 12L11 14L16 9M12 2L21 6V13Q20 19 12 22Q4 19 3 13V6Z", "watchlist": "M2 12Q12 -2 22 12Q12 26 2 12ZM12 8A4 4 0 1 0 12 16A4 4 0 1 0 12 8", "topics": "M12 2V22M2 12H22M12 4A8 8 0 1 0 12 20A8 8 0 1 0 12 4", "history": "M4 6A9 9 0 1 1 3 16M4 2V7H9M12 7V12L16 14", "settings": "M4 6H20M4 12H20M4 18H20M8 3V9M16 9V15M10 15V21"};
function navIcon(id){return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="'+navPaths[id]+'"/></svg>'}
