const fs=require('fs'),vm=require('vm'),assert=require('assert');
const ctx={console,URLSearchParams,FormData,URL,Date,setTimeout,clearTimeout,document:{addEventListener(){},querySelector(){return null}},window:{addEventListener(){}},location:{hash:''}};
vm.createContext(ctx);
for(const file of ['app','settings','feed','screens','actions','accounts','social','social-actions','terminal','updates','forms']){
 let code=fs.readFileSync('app/static/'+file+'.js','utf8');if(file==='forms')code=code.replace('start().catch(errorPanel);','');vm.runInContext(code,ctx);
}
(async()=>{
 await vm.runInContext(`(async()=>{
 config={onboarded:true,my_profile:{name:'Saved name',bio:'<unsafe>'},brand_voice:{Tone:'Casual'},ai_provider:'grok',interests:[]};
 settingsTab='memory';const html=extendedSettings();
 if(!html.includes('id="structured-profile-form"')||!html.includes('name="name"')||!html.includes('Saved name')||html.includes('<unsafe>'))throw Error('Profile rendering failed');
 if(!writingMemoryPage.toString().includes('writing-preference-form'))throw Error('Writing preference form must have its own ID');
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
 for(const k of ['grok','claude','kimi','deepseek']){config.ai_provider=k;if(!aiFields().includes('API billing is separate'))throw Error('Provider disclosure missing')}
 })()`,ctx);
 console.log('Profile form rendering, real submit dispatch, validation failure, brand voice separation and provider UI passed.');
})().catch(error=>{console.error(error);process.exit(1)});
