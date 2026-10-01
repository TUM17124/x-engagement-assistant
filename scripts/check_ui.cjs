const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const files=['app','settings','feed','screens','actions','accounts','social','social-actions','forms'];
for(const file of files)new vm.Script(fs.readFileSync(path.join('app/static',file+'.js'),'utf8'),{filename:file+'.js'});
const context={console,URLSearchParams,FormData,Date,setTimeout,clearTimeout,
document:{addEventListener(){},querySelector(){return null}},window:{addEventListener(){}},location:{hash:''}};
vm.createContext(context);
for(const file of files.slice(0,-1))vm.runInContext(fs.readFileSync(path.join('app/static',file+'.js'),'utf8'),context);
vm.runInContext(`
settingsTab='x';
config={ai_provider:'gemini',ai_model:'test-model',interests:[],theme:'dark',default_query:'PDF',discovery_mode:'automatic',daily_search_limit:20};
if(!settingsPage({authors:[],topics:[]}).includes('Discovery Mode'))throw Error('Discovery Mode missing');
if(!settingsPage({authors:[],topics:[]}).includes('daily_search_limit'))throw Error('Search cap missing');
if(!feedPage([]).includes('Search inside app'))throw Error('API search UI missing');
if(!feedPage([]).includes('Open Search on X'))throw Error('Web fallback missing');
if(esc('<img src=x onerror=alert(1)>').includes('<img'))throw Error('Escaping failed');
const d={id:1,kind:'reply',username:'test',status:'draft',text:'A reply',score:90,source_text:'<script>alert(1)</script>',reason:'Specific',topic:'PDF'};
const html=draftCard(d);
if(html.includes('<script>'))throw Error('Untrusted source was not escaped');
if(!html.includes('Approve exact content')||!html.includes('Reply Manually on X'))throw Error('Approval workflow missing');
if(!schedulePage([]).includes('Keep the app running'))throw Error('Scheduler limitation missing');
if(!composePage().includes('Generate 3 alternatives'))throw Error('Composer tool missing');
if(!topicsPage([]).includes('Suggest query with AI'))throw Error('Topic AI tool missing');
`,context);
console.log('UI syntax and rendering contracts passed (no browser automation).');
