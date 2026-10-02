const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes=[],listeners={};
function element(){return {append(){},dataset:{},disabled:false,textContent:'Generate plan',attributes:{},setAttribute(k,v){this.attributes[k]=v},removeAttribute(k){delete this.attributes[k]},prepend(v){nodes.push(v)},remove(){this.removed=true},scrollIntoView(){},focus(){},closest(){return null}}}
const root=element();
const ctx={console,FormData,URLSearchParams,URL,AbortController,TypeError,TextDecoder,crypto:require("crypto").webcrypto,setTimeout,clearTimeout,Intl,
 document:{addEventListener(k,v){(listeners[k]??=[]).push(v)},querySelector(s){return s==='#page-error'?nodes.findLast(n=>n.id==='page-error'&&!n.removed)||null:root},createElement:element},
 window:{addEventListener(){}},location:{hash:''},fetch:async()=>({ok:true,status:200,json:async()=>({ok:true})})};
vm.createContext(ctx);
for(const f of ['app','actions','terminal'])vm.runInContext(fs.readFileSync('app/static/'+f+'.js','utf8'),ctx);
vm.runInContext(fs.readFileSync('app/static/forms.js','utf8').replace('start().catch(errorPanel);',''),ctx);
(async()=>{
 for(const status of [401,402,403,404,413,422,429,500,502]){
  ctx.fetch=async()=>({ok:false,status,json:async()=>({error:'Clear failure '+status,technical:'X HTTP '+status})});
  await assert.rejects(vm.runInContext("api('/test','POST',{})",ctx),e=>e.message.includes('Clear failure')&&e.technical==='X HTTP '+status);
 }
 ctx.fetch=async()=>({ok:false,status:422,json:async()=>({detail:[{loc:['body','due_at'],msg:'Field required',input:'never echo input'}]})});
 await assert.rejects(vm.runInContext("api('/test')",ctx),e=>e.message.includes('due_at')&&!e.message.includes('never echo'));
 ctx.fetch=async()=>({ok:false,status:500,json:async()=>{throw Error('<html>private server content</html>')}});
 await assert.rejects(vm.runInContext("api('/test')",ctx),e=>e.message.includes('unreadable')&&!e.message.includes('private'));
 ctx.fetch=async()=>{throw new TypeError('Failed to fetch')};
 await assert.rejects(vm.runInContext("api('/api/drafts/1/publish','POST',{})",ctx),e=>e.hint.includes('not retried automatically'));
 ctx.fetch=async(path,opts)=>new Promise((resolve,reject)=>opts.signal.addEventListener('abort',()=>{const e=Error();e.name='AbortError';reject(e)}));
 await assert.rejects(vm.runInContext("api('/test','GET',undefined,{timeoutMs:5})",ctx),e=>e.message.includes('too long'));
 let calls=0;ctx.button=element();ctx.work=async()=>{calls++;throw Error('Provider needs attention')};
 await vm.runInContext('runUIAction(button,work)',ctx);
 assert.equal(calls,1);assert.equal(ctx.button.disabled,false);assert.equal(ctx.button.dataset.busy,undefined);
 assert(nodes.some(n=>n.id==='page-error'&&n.innerHTML.includes('Generate plan could not finish')&&n.innerHTML.includes('Provider needs attention')));
 ctx.button.dataset.busy='true';await vm.runInContext('runUIAction(button,work)',ctx);assert.equal(calls,1);delete ctx.button.dataset.busy;
 // Dispatch actual click/form listeners, including terminal control buttons, through the shared boundary.
 vm.runInContext("doAction=async()=>{throw Error('X needs credits')};submit=async()=>{throw Error('Choose a valid date')};api=async()=>{throw Error('ChatGPT needs reconnect')}",ctx);
 for(const [kind,marker] of [['click','data-action'],['click','data-control'],['submit',null]]){
  const b=element();b.dataset.action='test-x';b.dataset.control='chatgpt-retry';
  const event={target:{closest(s){return s==='['+marker+']'?b:null}},submitter:b,preventDefault(){}};
  for(const listener of listeners[kind])await listener(event);
  assert.equal(b.disabled,false);
 }
 for(const f of ['actions','forms','terminal'])assert(fs.readFileSync('app/static/'+f+'.js','utf8').includes('runUIAction('));
 // Real terminal stream parser binds yes to one displayed request, never to model prose.
 const output=element();output.append=()=>{};output.insertAdjacentHTML=()=>{};output.replaceChildren=()=>{};
 ctx.document.querySelector=()=>output;
 vm.runInContext("terminalOutput=()=>({textContent:''});actionCard=()=>'';terminalToolResult=()=>{};terminalCommandId=null",ctx);
 const request={id:'preview-one',checksum:'a'.repeat(64)};let sent;
 ctx.fetch=async(path,options)=>{sent=JSON.parse(options.body);let delivered=false;return {ok:true,body:{getReader(){return {read:async()=>delivered?{done:true}:(delivered=true,{done:false,value:Buffer.from('data: '+JSON.stringify({type:'approval',request})+'\n\n')})}}}}};
 await vm.runInContext("runTerminal('publish 1')",ctx);
 ctx.fetch=async(path,options)=>{sent=JSON.parse(options.body);return {ok:true,body:{getReader(){return {read:async()=>({done:true})}}}}};
 await vm.runInContext("runTerminal('yes')",ctx);
 assert.equal(sent.approval_id,'preview-one');assert.equal(sent.approval_checksum,'a'.repeat(64));
 await vm.runInContext("runTerminal('yes')",ctx);assert.equal(sent.approval_id,undefined);
 let delivered=false;
 ctx.fetch=async()=>({ok:true,body:{getReader(){return {read:async()=>delivered?{done:true}:(delivered=true,{done:false,value:Buffer.from([request,{id:'preview-two',checksum:'b'.repeat(64)}].map(r=>'data: '+JSON.stringify({type:'approval',request:r})+'\n\n').join(''))})}}}});
 await vm.runInContext("runTerminal('prepare two actions')",ctx);
 assert.equal(vm.runInContext('terminalPendingApproval',ctx),null);

 // Work stays tracked independently of page rendering and ends with a grounded report.
 const work=vm.runInContext("beginWork('Draft reply')",ctx);ctx.workId=work;
 vm.runInContext("progressWork(workId,'Waiting for ChatGPT');finishWork(workId,{state:'completed',message:'Draft is waiting in Response Inbox',suggestions:[{label:'Review',url:'#queue'}]})",ctx);
 assert.equal(vm.runInContext('activeWork.size',ctx),0);
 assert(vm.runInContext('workReports[0].message',ctx).includes('Response Inbox'));
 assert.equal(vm.runInContext('workReports[0].suggestions[0].url',ctx),'#queue');
 console.log('Action feedback passed: HTTP errors, validation, malformed responses, network loss, timeout, duplicate click prevention, and click/form/control boundaries.');
})().catch(e=>{console.error(e);process.exitCode=1});
