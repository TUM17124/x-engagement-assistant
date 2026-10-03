const fs=require('fs'),vm=require('vm'),assert=require('assert');
const ctx={console,URLSearchParams,FormData,URL,Date,setTimeout,clearTimeout,document:{addEventListener(){},querySelector(){return null}},window:{addEventListener(){}},location:{hash:''}};
vm.createContext(ctx);
for(const file of ['app','settings','feed','screens','actions','accounts','social','social-actions','terminal','terminal-interactive','updates','ai-providers','forms']){
 let code=fs.readFileSync('app/static/'+file+'.js','utf8');if(file==='forms')code=code.replace('start().catch(errorPanel);','');vm.runInContext(code,ctx);
}
(async()=>{
 await vm.runInContext(`(async()=>{
 config={onboarded:true,my_profile:{name:'Saved name',bio:'<unsafe>'},brand_voice:{Tone:'Casual'},ai_provider:'grok',interests:[]};
 settingsTab='memory';const html=extendedSettings();
 if(!html.includes('id="structured-profile-form"')||!html.includes('name="name"')||!html.includes('Saved name')||html.includes('<unsafe>'))throw Error('Profile rendering failed');
 if(!writingMemoryPage.toString().includes('writing-preference-form'))throw Error('Writing preference form must have its own ID');
 const realTerminalSubmit=terminalSubmit;
 let calls=[],messages=[];values=f=>f.payload;api=async(...args)=>{calls.push(args);return args[2]};toast=s=>messages.push(s);reportWork=()=>{};render=async()=>{};
 terminalSubmit=()=>{throw Error('Profile was routed to individual memory preference!')};
 const f={id:'structured-profile-form',dataset:{kind:'my_profile'},classList:{contains:()=>false},payload:{name:'Ada',role:'Founder',bio:'',industry:'',expertise:'Code',products:'App',audience:'Creators',goals:'Help people'}};
 await submit(f);
 if(calls[0][0]!='/api/profile'||calls[0][1]!=='PUT')throw Error('Wrong endpoint');
 if(calls[0][2].Name!==undefined||calls[0][2].name!=='Ada')throw Error('Wrong schema');
 if(messages[0]!=='Profile saved'||config.my_profile.name!=='Ada')throw Error('Success state missing');
 f.dataset.kind='brand_voice';f.payload={Tone:'Friendly'};await submit(f);
 if(calls[1][0]!='/api/settings'||calls[1][2].brand_voice.Tone!=='Friendly')throw Error('Brand voice routed incorrectly');
 api=async()=>{throw Error('Validation failed')};messages=[];
 try{await submit(f);throw Error('Should reject')}catch(error){if(error.message!=='Validation failed')throw error}
 if(messages.length)throw Error('Invalid save must never report success');
 terminalSubmit=realTerminalSubmit;
 // Exercise each normal Settings save control with representative retained values.
 const saved=[];api=async(path,method,body)=>{saved.push({path,method,body});return {settings:config,secrets:{},providers:aiCatalog,policy:aiPolicy}};
 const form=(id,payload,elements={})=>({id,payload,elements,classList:{contains:()=>false},dataset:{provider:'gemini'}});
 for(const type of ['voice','product']){const f=form('profile-form',type==='voice'?{who:'Founder',tone:'Practical'}:{name:'Reader',description:'PDF tools'});f.dataset.type=type;await submit(f);if(saved.at(-1).body[type]!==f.payload)throw Error('Context save mismatch')}
 await submit(form('appearance-form',{theme:'dark'},Object.fromEntries(['notifications','notify_priority','notify_mentions','notify_connections','tray_enabled'].map(k=>[k,{checked:false}]))));
 await submit(form('safety-form',Object.fromEntries(['daily_reply_limit','daily_post_limit','daily_write_cap','hourly_write_limit','daily_ai_limit','same_account_limit'].map(k=>[k,'5']))));
 if(saved.at(-1).body.require_approval!==true)throw Error('Safety save weakened approval');
 await submit(form('discovery-form',{discovery_mode:'web',daily_search_limit:'10',poll_minutes:'30'},{read_access:{checked:false},monitoring:{checked:false}}));
 await submit(form('x-form',{x_client_id:'public-client-id',x_redirect_uri:'http://127.0.0.1:8787/auth/callback'},{}));
 aiEditing='gemini';await submit(form('provider-config-form',{name:'Gemini',model:'test-model',base_url:'https://generativelanguage.googleapis.com/v1beta'},{enabled:{checked:true},api_key:{value:''}}));
 for(const tab of ['memory','brand','ai','x','voice','product','appearance','safety','data','usage','accounts','updates']){
 settingsTab=tab;usageCache={};accountsCache=[];updateState={current_version:'0.3.1',release:{},settings:{check_updates:false}};
 if(!settingsPage({authors:[],topics:[]}).includes('Settings'))throw Error('Settings tab failed: '+tab)
 }
 try{await submit(form('missing-form',{}));throw Error('Unknown form reported success')}catch(e){if(e.message==='Unknown form reported success')throw e}
 // Drive the actual preference form handler with invalid and long realistic text.
 let preferenceCalls=[];api=async(...args)=>{preferenceCalls.push(args);return {data:[]}};
 values=f=>f.payload;
 const pref={id:'writing-preference-form',payload:{key:'tone',value:'   '}};
 for(const value of ['   ','x'.repeat(4001)]){pref.payload.value=value;try{await terminalSubmit(pref);throw Error('Invalid preference accepted')}catch(e){if(e.message==='Invalid preference accepted')throw e}}
 if(preferenceCalls.length)throw Error('Invalid preference sent to backend');
 pref.payload.value='Thoughtful, practical replies. '.repeat(60);await terminalSubmit(pref);
 if(preferenceCalls[0][2].tool!=='memory.savePreference'||preferenceCalls[0][2].arguments.value!==pref.payload.value.trim())throw Error('Preference payload mismatch');
 terminalOutput=()=>{};
 terminalToolResult({tool:'settings.updateContext',data:{settings:{brand_voice:{Tone:'Direct'},voice:{tone:'Friendly'}}}});
 if(config.brand_voice.Tone!=='Direct'||config.voice.tone!=='Friendly')throw Error('Verified result did not refresh Settings');
 if(!providerSettingsPage().includes('does not require one specific AI company'))throw Error('Neutral disclosure missing');
 })()`,ctx);
 console.log('Profile form rendering, real submit dispatch, validation failure, brand voice separation and provider UI passed.');
})().catch(error=>{console.error(error);process.exit(1)});
