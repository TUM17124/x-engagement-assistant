let updateState=null,updatePollTimer=null,updateWorkId=null,updateLastJob='';
function updatesPage(){
 const d=updateState||{},r=d.release||{},j=d.installation||{};
 const message=d.release_message||r.error||r.message||(r.available?'Published version '+r.version+' is available.':'No successful GitHub release check has completed yet.');
 return '<h2>App updates</h2><p>Installed version: '+esc(d.current_version||'Unknown')+'</p><div class="notice '+(r.error?'warning':'')+'">'+esc(message)+'</div>'+
 '<div class="row"><button type="button" data-update="check">Check for updates</button>'+
 (r.available?(d.desktop&&r.signed?'<button type="button" data-update="install">Update to '+esc(r.version)+'</button>':link('Download installer for this device',r.download_url)):'')+
 link('GitHub releases',(d.repository||'https://github.com/TUM17124/x-engagement-assistant')+'/releases')+'</div>'+
 (r.checked_at?'<p class="hint">Last checked: '+esc(fmt(r.checked_at))+'</p>':'')+
 (r.notes?'<details><summary>Release notes</summary><p class="post-text">'+esc(r.notes)+'</p></details>':'')+
 (j.message?'<div class="notice" id="update-install-status">'+esc(j.message)+'</div>':'<div id="update-install-status"></div>')+
 '<p class="hint">Updates check published GitHub releases only. Editing this repository or building an installer does not update the installed app. A local build must be installed separately; it will not appear on GitHub until published. The installer is signature-checked and asks for your approval. The app closes during installation; saved accounts and drafts are retained. No Git, Python or terminal is needed.</p>'+
 platformDownloads(r)+
 '<form id="update-settings-form">'+check('Check GitHub for updates while this app is running','check_updates',d.settings?.check_updates??true)+'<p class="hint">Checks run at most once every six hours. No update installs automatically.</p><button type="submit">Save update preference</button></form>'+
 '<hr class="divider"><h2>Free email updates</h2><p>Get a release email even while this app is closed. No API key, sender setup, or GitHub account is needed.</p>'+
 '<button type="button" data-update="email">Get free email updates</button>'+
 '<p>Opens Blogtrottr with this app\'s GitHub release feed already selected. Enter your email there, submit, and complete any email or browser verification it requests.</p>'+
 '<p class="hint">Blogtrottr is an independent, ad-supported service. It receives your email and chosen public feed; this app does not collect your email or claim to know your subscription status. Unsubscribe using the link in its emails. Free delivery timing is controlled by Blogtrottr.</p>'+
 '<div class="row">'+link('Privacy and service details','https://blogtrottr.com/about')+link('GitHub email alternative','https://github.com/TUM17124/x-engagement-assistant')+'</div>'+
 '<p class="hint">GitHub users can choose Watch &rarr; Custom &rarr; Releases and enable email notifications in GitHub settings.</p>';
}
async function pollUpdateStatus(){
 try{
  updateState=await api('/api/updates');
  const r=updateState.release||{},j=updateState.installation||{};
  const top=document.querySelector('[data-update="open"]');if(top)top.textContent=r.available?'Update available':'Updates';
  const active=['queued','downloading','installing'].includes(j.state);
  if(active){
   if(!updateWorkId)updateWorkId=beginWork('App update');
   const amount=j.total?' '+Math.min(100,Math.floor(j.downloaded/j.total*100))+'%':'';
   progressWork(updateWorkId,j.message+amount);
   const box=$('#update-install-status');if(box)box.textContent=j.message+amount;
  }else if(j.id&&updateLastJob!==j.id+':'+j.state&&['completed','failed','interrupted'].includes(j.state)){
   const result={state:j.state==='completed'?'completed':'failed',message:j.message,suggestions:[{label:'Open update settings',url:'#settings'}]};
   if(updateWorkId){finishWork(updateWorkId,result);updateWorkId=null}else reportWork(result);
   updateLastJob=j.id+':'+j.state;
  }
 }catch(e){
  // Windows closes the local server during installation; do not falsely call that a download failure.
  if(updateWorkId)progressWork(updateWorkId,'The app is restarting for the update. Reopen it if Windows finishes without reopening it.');
 }finally{updatePollTimer=setTimeout(pollUpdateStatus,updateWorkId?1500:60000)}
}
function startUpdateStatus(){if(!updatePollTimer)updatePollTimer=setTimeout(pollUpdateStatus,1000)}
document.addEventListener('click',async e=>{
 const button=e.target.closest('[data-update]');if(!button)return;
 await runUIAction(button,async()=>{
  const action=button.dataset.update;
  if(action==='open'){settingsTab='updates';location.hash='settings';return render()}
  if(action==='check'){
   updateState=await api('/api/updates/check','POST');const r=updateState.release||{};
   if(r.error)throw Error(r.error);
   reportWork({state:'completed',message:r.available?'Version '+r.version+' is ready for your review. Choose Update when convenient.':updateState.release_message||r.message||'No successful GitHub release check has completed yet.'});
   return render();
  }
  if(action==='email'){
   if(!updateState)updateState=await api('/api/updates');
   openExternal(updateState.email_signup_url);
   reportWork({state:'waiting',message:'Free email signup opened in your browser. Enter your email and complete the provider verification. Subscription is not confirmed by this app.'});
  }
  if(action==='install'){
   const version=updateState?.release?.version;
   if(!version)throw Error('Check for updates first.');
   if(!confirm('Install version '+version+'? Save edits first. The app will close during installation; a local database backup is created. Scheduled posts require the app to restart.'))return;
   await api('/api/updates/install','POST',{version,confirmed:true});
   if(updatePollTimer)clearTimeout(updatePollTimer);
   await pollUpdateStatus();
  }
 });
});

function platformDownloads(release){
 const fallback=[['windows-x64','Windows 10/11 (64-bit)'],['macos-arm64','macOS (Apple Silicon)'],['macos-x64','macOS (Intel)'],['linux-deb','Linux Ubuntu/Debian (64-bit)'],['linux-appimage','Linux AppImage (64-bit)']].map(([id,name])=>({id,name}));
 const downloads=release.downloads||fallback;
 return '<section class="card"><h3>Download for another computer</h3><p>Download the installer, then open it and approve installation. Your browser cannot install software silently.</p>'+downloads.map(d=>'<p><strong>'+esc(d.name)+'</strong> '+(d.available&&d.url?link('Download installer',d.url):'<span class="hint">'+(release.downloads?'Installer not published in this release':'Check for updates to see availability')+'</span>')+'</p>').join('')+'<details><summary>Why might I see an installation warning?</summary><p><strong>Windows:</strong> This project has no Windows Authenticode publisher certificate yet. SmartScreen may flag a new or unsigned download. An updater signature checks our release, but is separate from Microsoft publisher reputation.</p><p><strong>macOS:</strong> An app without Apple Developer ID signing and notarization may be blocked because Apple cannot verify the developer or check notarization. Only use the app-specific Open Anyway option if you trust the source.</p><p><strong>Linux:</strong> Downloaded packages may be described as third-party/untrusted because they are outside your distribution repository. AppImage files may need permission to execute, set in file Properties.</p><p>Download only from this project\'s GitHub releases. Do not disable antivirus, SmartScreen or Gatekeeper globally. A malware or damaged-file warning needs investigation; do not assume every warning is harmless.</p><div class="row">'+link('Microsoft signing guidance','https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation')+link('Apple installation guidance','https://support.apple.com/102445')+link('AppImage guide','https://docs.appimage.org/introduction/quickstart.html')+'</div></details></section>';
}
