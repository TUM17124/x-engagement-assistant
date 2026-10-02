async function doAction(a,id,el){
if(a.startsWith('ms-'))return msAction(a.slice(3),id,el);
if(a.startsWith('social-'))return socialAccountAction(a,id);
if(a==='onboard-back'){onStep--;wizard();return}
if(a==='reveal'){const d=await api('/api/secrets/'+id+'/reveal','POST'),target=$('#mask-'+id);target.textContent=d.value;setTimeout(()=>{if(target.isConnected)target.textContent=secretMasks[id]||'Not saved'},15000);return}
if(a==='delete-secret'){if(!confirm('Delete this saved credential?'))return;await api('/api/secrets/'+id,'DELETE');secretMasks[id]='';$('#mask-'+id).textContent='Not saved';toast('Credential deleted');return}
if(a==='connect-x'){const f=el.closest('form');if(f)await saveX(f);openExternal('/auth/login');toast('Complete X authorization in your browser, then test the connection here.');return}
if(a==='test-x'){const d=await api('/api/health/x','POST');profile=d.profile;if($('#connection-result'))$('#connection-result').textContent='Connected as @'+profile.username;toast('Connected as @'+profile.username);return}
if(a==='test-ai'){const f=el.closest('form');if(f?.elements.ai_provider)await saveAI(f);await api('/api/health/ai','POST');toast('AI connection and selected model verified');return}
if(a==='disconnect'){await api('/auth/logout','POST');profile=null;return render()}
if(a==='settings-tab'){settingsTab=id;return render()}
if(a==='approval-tab'){approvalTab=id;return render()}
if(a==='schedule-view'){scheduleMode=id;return render()}
if(a==='calendar-month'){calendarOffset+=Number(id);return render()}
if(a==='web-search'){openExternal('https://x.com/search?'+new URLSearchParams({q:webQuery(searchValues($('#search-form'))),src:'typed_query',f:'live'}));return}
if(a==='rank-search'){const d=await api('/api/search/rank','POST',{ids:lastSearchIds.slice(0,5)});toast(d.message);location.hash='queue';return render()}
if(a==='retry-search'){await api('/api/search/retry-access','POST');toast('The next search will test access again.');return}
if(a==='fetch-import'){await api('/api/feed/import','POST',{...values($('#import-form')),fetch:true});toast('Post imported');return render()}
if(a==='import-draft'){const post=await api('/api/feed/import','POST',values($('#import-form')));const d=await api('/api/generate/reply','POST',{feed_id:post.id});toast(d.skipped?'AI chose to skip this post.':'Draft ready for review');location.hash='queue';return render()}
if(a==='generate-reply'){const d=await api('/api/generate/reply','POST',{feed_id:id});toast(d.skipped?'AI chose to skip this post.':'Draft ready for review');location.hash='queue';return render()}
if(['save-feed','unsave-feed','ignore-feed'].includes(a)){await api('/api/feed/'+id+'/'+a.split('-')[0],'POST');return render()}
if(a==='save-draft'){await saveEdited(id);toast('Saved. Edited content needs approval again.');return render()}
if(a==='approve'){await saveEdited(id);await api('/api/drafts/'+id+'/approve','POST');toast('Exact content approved. Choose a publishing action when ready.');return render()}
if(a==='publish'){await saveEdited(id);if(!confirm('Publish this exact approved content to X now?'))return;await api('/api/drafts/'+id+'/publish','POST');toast('Published to X');return render()}
if(a==='manual'){await saveEdited(id);const d=await api('/api/drafts/'+id+'/manual','POST');openExternal(d.url);toast(d.note);return}
if(a==='skip-draft'){await api('/api/drafts/'+id+'/skip','POST');return render()}
if(a==='quote-draft'){const d=await saveEdited(id);await api('/api/drafts/'+id,'PUT',{kind:'quote',feed_id:d.feed_id,text:d.text});toast('Quote draft ready for approval.');approvalTab='quote';location.hash='approvals';return render()}
if(a==='regenerate'){const d=await saveEdited(id),style=$('#style-'+id).value;await api('/api/generate/reply','POST',{feed_id:d.feed_id,draft_id:Number(id),style:style==='Regenerate'?'':style});return render()}
if(a==='mute-author'||a==='mute-topic'){const d=draftCache.find(x=>x.id===Number(id));await api('/api/mute/'+(a==='mute-author'?'author':'topic'),'POST',{value:a==='mute-author'?d.username:d.topic});toast('Muted');return render()}
if(a==='unmute'){await api('/api/unmute/'+el.dataset.kind,'POST',{value:id});return render()}
if(a==='schedule-draft'){await saveEdited(id);const card=el.closest('article');if(card.querySelector('.schedule-form'))return;const f=document.createElement('form');f.className='schedule-form notice';f.dataset.draft=id;f.innerHTML=input('Local date and time','due','','datetime-local','required')+'<p class="hint">Timezone: '+esc(Intl.DateTimeFormat().resolvedOptions().timeZone)+'. Keep the app running.</p><button type="submit">Schedule this approved post</button>';card.append(f);return}
if(a==='edit-schedule'){inboxTab='scheduled';location.hash='queue';return render()}
if(a==='legacy-edit-schedule'){composing=(await api('/api/drafts')).find(d=>d.id===Number(id));composingGenerated=composing?.generated_text||'';location.hash='compose';return render()}
if(a==='cancel-schedule'){if(confirm('Cancel this scheduled post?'))await api('/api/schedule/'+id,'DELETE');return render()}
if(a==='new-draft'){if($('#compose-form').elements.text.value.trim()&&!confirm('Start a new draft? Save any current changes first.'))return;composing=null;composingGenerated='';return render()}
if(a==='compose-review'){const d=await submitCompose($('#compose-form'));approvalTab=d.kind;composing=null;composingGenerated='';location.hash='approvals';return render()}
if(a==='compose-ai'){const f=$('#compose-form'),operation=$('[name="compose-operation"]').value,text=f.elements.text.value;if(!text.trim())throw Error('Write a brief or some text first.');const d=await api('/api/generate/compose','POST',{text,operation,kind:f.elements.kind.value});const suggestions=operation==='Generate 3 alternatives'?d.text.split(/\n\s*---\s*\n/):[d.text];$('#compose-suggestion').innerHTML=suggestions.map((s,i)=>'<div class="card"><div class="preview" id="suggestion-'+i+'">'+esc(s)+'</div>'+(operation!=='Check repetitive wording'?btn('Use this suggestion','use-suggestion',i):'')+'</div>').join('');return}
if(a==='use-suggestion'){const f=$('#compose-form').elements.text;f.value=$('#suggestion-'+id).textContent;composingGenerated=f.value;f.dispatchEvent(new Event('input',{bubbles:true}));return}
if(a==='resume-discovery'){await api('/api/discovery/resume','POST');config.monitoring=true;toast('Monitoring resumed; rate-limit backoff remains.');return render()}
if(a==='edit-watch'){editingWatch=(await api('/api/watchlist')).find(x=>x.id===Number(id));return render()}
if(a==='delete-watch'){if(confirm('Remove this watched account?'))await api('/api/watchlist/'+id,'DELETE');return render()}
if(a==='refresh-watch'){const d=await api('/api/watchlist/'+id+'/refresh','POST');toast(d.items.length+' new posts imported');return render()}
if(a==='edit-topic'){editingTopic=(await api('/api/topics')).find(x=>x.id===Number(id));return render()}
if(a==='delete-topic'){if(confirm('Remove this topic?'))await api('/api/topics/'+id,'DELETE');return render()}
if(a==='refresh-topic'){const d=await api('/api/topics/'+id+'/refresh','POST');toast(d.items.length+' new posts imported. Check topic status if access is unavailable.');return render()}
if(a==='topic-ai'){const f=$('#topic-form'),d=values(f);d.enabled=f.elements.enabled.checked;f.elements.query.value=(await api('/api/topics/suggest/query','POST',d)).query;return}
throw Error('This action is unavailable in this app version. Reopen the app and try again.');
}
document.addEventListener('click',async e=>{const b=e.target.closest('[data-action]');if(!b)return;await runUIAction(b,()=>doAction(b.dataset.action,b.dataset.id,b))});

document.addEventListener('click',e=>{const a=e.target.closest('a[target="_blank"]');if(a&&window.__XEA_DESKTOP__){e.preventDefault();openExternal(a.href)}});
