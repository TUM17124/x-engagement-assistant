const fs=require('fs'),vm=require('vm'),assert=require('assert');
const listeners={},nodes={};const context={console,FormData,URLSearchParams,URL,Date,Intl,AbortController,TextDecoder,crypto:require('crypto').webcrypto,setTimeout:()=>0,clearTimeout(){},document:{addEventListener(k,v){(listeners[k]??=[]).push(v)},querySelector(s){return nodes[s]||null},createElement(){return {append(){},textContent:''}}},window:{addEventListener(){}},location:{hash:''}};
vm.createContext(context);for(const name of ['app','terminal','terminal-interactive'])vm.runInContext(fs.readFileSync('app/static/'+name+'.js','utf8'),context);
(async()=>{
let sent=0,prevented=0;const input={id:'terminal-input',value:'hello',selectionStart:2,selectionEnd:2,focus(){},setSelectionRange(){},form:{requestSubmit(){sent++}}};nodes['#terminal-input']=input;
const key=async(k,extra={})=>{for(const fn of listeners.keydown)await fn({target:input,key:k,preventDefault(){prevented++},...extra})};
await key('Enter');assert.equal(sent,1);await key('Enter',{shiftKey:true});assert.equal(sent,1);await key('Enter',{isComposing:true});assert.equal(sent,1);
vm.runInContext("terminalHistory=['older command'];terminalHistoryIndex=1",context);await key('ArrowUp');assert.equal(input.value,'hello');input.selectionStart=0;input.selectionEnd=0;await key('ArrowUp');assert.equal(input.value,'older command');input.selectionStart=input.selectionEnd=input.value.length;await key('ArrowDown');assert.equal(input.value,'hello');
input.value='line one\nline two';input.selectionStart=input.selectionEnd=0;await key('ArrowUp');assert.equal(input.value,'line one\nline two');
let cancelled=0,aborted=0;context.cancelled=()=>cancelled++;context.aborted=()=>aborted++;vm.runInContext("route='terminal';terminalCommandId='active';terminalAbort={abort:aborted};api=async()=>{cancelled();return {cancelled:true}}",context);await key('c',{ctrlKey:true});await new Promise(r=>setImmediate(r));assert.equal(cancelled,1);assert.equal(aborted,1);
vm.runInContext("terminalCommandId=null;terminalPendingApproval={id:'exact',checksum:'x'}",context);assert.equal(vm.runInContext("resolveTerminalChoice('1')",context),'yes');assert.equal(vm.runInContext("resolveTerminalChoice('2')",context),'no');
vm.runInContext("terminalOutput=()=>{}",context);assert.equal(vm.runInContext("resolveTerminalChoice('3')",context),null);
vm.runInContext("terminalPendingApproval=null;terminalChoices=[{label:'Yes, report',command:'trend report'}]",context);assert.equal(vm.runInContext("resolveTerminalChoice('1')",context),'trend report');assert.equal(vm.runInContext("resolveTerminalChoice('yes')",context),'trend report');
assert(!vm.runInContext("questionHTML('<script>',[{label:'<img>',command:'status'}])",context).includes('<script>'));
context.responses={'/api/terminal/history':[],'/api/chatgpt/status':{},'/api/terminal/context':{tips:[{label:'Radar',command:'scan trends',reason:'Find relevant topics'}]},'/api/terminal/approvals':[]};vm.runInContext("api=async p=>responses[p];config={ai_provider:'gemini'};terminalDraftInput='Editable long draft'",context);
const html=await vm.runInContext('terminalPage()',context);assert(html.includes('<textarea'));assert(!html.includes('maxlength="4000"'));assert(html.includes('Editable long draft'));assert(html.includes('Shift+Enter'));
console.log('Interactive terminal passed: Enter, multiline editing, IME, history caret, Ctrl+C, numbered choices, escaping and retained input.');
})().catch(e=>{console.error(e);process.exit(1)});
