const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes={};const ctx={console,URLSearchParams,FormData,Date,setTimeout,clearTimeout,URL,crypto:require('crypto').webcrypto,location:{hash:''},window:{addEventListener(){}},document:{addEventListener(){},querySelector(s){return nodes[s]||null}},confirm:()=>true};vm.createContext(ctx);
for(const name of ['app','settings','social','ai-providers','trends','video'])vm.runInContext(fs.readFileSync('app/static/'+name+'.js','utf8'),ctx);
(async()=>{await vm.runInContext(`(async()=>{
const calls=[];values=f=>f.payload;toast=()=>{};reportWork=()=>{};render=async()=>{};
radarState={sources:[{id:'mastodon',name:'Mastodon'}],items:[{id:'mastodon:1',source:'mastodon',title:'<script>bad</script>',text:'A useful AI discussion',tags:['ai'],author:'Person',url:'https://mastodon.social/test',metrics:{replies:3},scope:'Local community',media:[{kind:'audio',url:'https://files.mastodon.social/test.mp3'}],matched_interests:['ai'],reason:'Matches ai',relevance:25,saved:false,ignored:false}]};
let html=radarResults();if(html.includes('<script>bad'))throw Error('Source XSS');if(!html.includes('Load media preview'))throw Error('Missing media action');if(html.includes('<audio'))throw Error('Media loaded without a click');
radarFilters.scope='matched';if(!radarResults().includes('useful AI'))throw Error('Interest filter');radarFilters.kind='video';if(radarResults().includes('useful AI'))throw Error('Media filter');radarFilters.kind='';
api=async(path,method,body)=>{calls.push({path,method,body});return {draft:{id:4,text:'An original draft'},message:'Draft ready in Response Inbox'}};
const result={innerHTML:''};await radarSubmit({id:'',payload:{task:'Post',platform:'x',angle:'My experience'},dataset:{id:'mastodon:1'},parentElement:{querySelector:()=>result}});
if(calls.at(-1).body.item_id!=='mastodon:1'||!result.innerHTML.includes('Response Inbox'))throw Error('Draft dispatch/report');
await radarAction('radar-save','mastodon:1',{});if(calls.at(-1).body.saved!==true)throw Error('Save action');
videoSettings={config:{provider:'grok',model:'video-model'},providers:[{id:'grok',name:'xAI',note:'API only',docs:'https://docs.x.ai',key_mask:'masked',key_url:'https://console.x.ai',pricing_url:'https://docs.x.ai',privacy_url:'https://x.ai'}]};
if(!videoSettingsPage().includes('video-provider-form'))throw Error('Video settings missing');
const form={id:'video-generation-form',dataset:{},elements:{prompt:{value:'A forest scene'}}};let count=calls.length;confirm=()=>false;await videoSubmit(form);if(calls.length!==count)throw Error('Unconfirmed generation');confirm=()=>true;await videoSubmit(form);if(calls.at(-1).body.confirmed!==true||calls.at(-1).body.prompt!=='A forest scene')throw Error('Video request mismatch');
const first=form.dataset.requestId;await videoSubmit(form);if(form.dataset.requestId!==first)throw Error('Retry lost request identity');
const fake={payload:{name:'Local',base_url:'http://localhost:1234/v1',manual_model_id:'mine'},elements:{manual_model:{checked:true},local:{checked:true},enabled:{checked:true}}};if(aiConnectionValues(fake).model!=='mine')throw Error('Custom model mismatch');
})()`,ctx);console.log('Radar/video UI passed: escaped evidence, interest/media filters, lazy previews, draft reports, save action, explicit paid confirmation and stable retry identity.');})().catch(e=>{console.error(e);process.exit(1)});
