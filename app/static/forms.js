async function submit(f){
if(["terminal-form","automation-form","memory-form"].includes(f.id))return terminalSubmit(f);
const d=values(f);
if(isSocialForm(f))return msSubmit(f);
if(f.classList.contains('social-account-form')||f.classList.contains('social-callback-form'))return socialAccountSubmit(f);
if(f.id==='onboarding-form'){
 if(onStep===1)await saveX(f);
 if(onStep===2)await saveAI(f);
 if(onStep===3){const interests=[...new FormData(f).getAll('interest'),...d.custom_interests.split(',').map(x=>x.trim()).filter(Boolean)];await api('/api/settings','PUT',{interests});config.interests=interests;const old=await api('/api/topics');for(const t of interests)if(!old.some(x=>x.name===t))await api('/api/topics','POST',{name:t,keywords:t})}
 if(onStep===4){const old=await api('/api/watchlist');for(const u of d.favorite_accounts.split(',').map(x=>x.trim().replace(/^@/,'')).filter(Boolean))if(!old.some(x=>x.username.toLowerCase()===u.toLowerCase()))await api('/api/watchlist','POST',{username:u})}
 if(onStep===5){await saveSafety(f);await api('/api/onboarding/finish','POST');config.onboarded=true;return render()}
 onStep++;return wizard();
}
if(f.id==='search-form')return submitSearch(f);
if(f.id==='import-form'){await api('/api/feed/import','POST',d);toast('Post added to your feed');return render()}
if(f.id==='watch-form'){d.enabled=f.elements.enabled.checked;d.ai_drafting=f.elements.ai_drafting.checked;d.notifications=f.elements.notifications.checked;await api('/api/watchlist'+(editingWatch?'/'+editingWatch.id:''),editingWatch?'PUT':'POST',d);editingWatch=null;return render()}
if(f.id==='topic-form'){d.enabled=f.elements.enabled.checked;await api('/api/topics'+(editingTopic?'/'+editingTopic.id:''),editingTopic?'PUT':'POST',d);editingTopic=null;return render()}
if(f.id==='compose-form')return submitCompose(f);
if(f.classList.contains('schedule-form')){const time=new Date(d.due);if(!Number.isFinite(time.getTime()))throw Error('Choose a valid date and time.');await api('/api/drafts/'+f.dataset.draft+'/schedule','POST',{due_at:time.toISOString(),timezone:Intl.DateTimeFormat().resolvedOptions().timeZone});toast('Approved post scheduled. Keep the app running.');location.hash='schedule';return render()}
if(f.id==='history-filter'){$('#history-results').innerHTML=historyTable(await api('/api/history?'+new URLSearchParams(d)));return}
if(f.id==='x-form')await saveX(f);
if(f.id==='ai-form')await saveAI(f);
if(f.id==='safety-form')await saveSafety(f);
if(f.id==='profile-form'){const type=f.dataset.type;await api('/api/settings','PUT',{[type]:d});config[type]=d}
if(f.id==='appearance-form'){const next={theme:d.theme,notifications:f.elements.notifications.checked,notify_priority:f.elements.notify_priority.checked,notify_mentions:f.elements.notify_mentions.checked,notify_connections:f.elements.notify_connections.checked,tray_enabled:f.elements.tray_enabled.checked};await api('/api/settings','PUT',next);Object.assign(config,next)}
if(f.id==='discovery-form'){const next={discovery_mode:d.discovery_mode,daily_search_limit:Number(d.daily_search_limit),read_access:f.elements.read_access.checked,monitoring:f.elements.monitoring.checked,poll_minutes:Number(d.poll_minutes)};await api('/api/settings','PUT',next);Object.assign(config,next)}
if(f.id==='restore-form'){if(!confirm('Replace your workspace with this backup? Export the current workspace first if needed. Restored schedules will not publish automatically.'))return;const result=await api('/api/restore','POST',new FormData(f));toast(result.note);config=(await api('/api/settings')).settings;return render()}
if(f.id==='legacy-form'){const result=await api('/api/import/legacy','POST',new FormData(f));toast(result.note);return render()}
if(f.id==='settings-import-form'){const file=f.elements.file.files[0];if(file.size>100000)throw Error('Settings file is too large.');await api('/api/import/settings','POST',JSON.parse(await file.text()));config=(await api('/api/settings')).settings}
toast('Settings saved');return render();
}
document.addEventListener('submit',async e=>{e.preventDefault();await runUIAction(e.submitter,()=>submit(e.target),e.submitter?.textContent||'Save form')});
document.addEventListener('change',async e=>{
if(e.target.name==='ai_provider')await runUIAction(e.target,async()=>{const previous=config.ai_provider;try{await api('/api/settings','PUT',{ai_provider:e.target.value});config.ai_provider=e.target.value;config.ai_base_url=config.ai_provider==='ollama'?'http://127.0.0.1:11434':'';config.ai_model=config.ai_provider==='gemini'?'gemini-2.5-flash':'';secretMasks=(await api('/api/settings')).secrets;if(!config.onboarded)wizard();else await render()}catch(error){e.target.value=previous;throw error}},'Change AI provider');
if(e.target.name==='tweet_url'){const value=e.target.value;try{const d=await api('/parse-tweet-url?'+new URLSearchParams({tweet_url:value}));if(e.target.value!==value)return;e.target.form.elements.username.value=d.author_username;$('#url-status').textContent='@'+d.author_username+' / Tweet ID '+d.tweet_id}catch(error){if($('#url-status'))$('#url-status').textContent=error.message}}
});
document.addEventListener('input',e=>{if(e.target.tagName!=='TEXTAREA')return;const n=e.target.name,c=n==='text'?$('#compose-count'):document.querySelector('[data-count="'+n.replace('draft-','')+'"]');if(c){c.textContent=e.target.value.length+' characters';c.classList.toggle('over',e.target.value.length>280)}});
document.addEventListener('visibilitychange',()=>{if(document.hidden)for(const n of Object.keys(secretMasks)){const el=$('#mask-'+n);if(el)el.textContent=secretMasks[n]||'Not saved'}});
window.addEventListener('hashchange',()=>render().catch(errorPanel));
start().catch(errorPanel);
