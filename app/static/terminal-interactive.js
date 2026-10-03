/* Conversation surface and keyboard controls; all actions still use the command bus. */
let terminalChoices=[],terminalDraftInput='',terminalScratch='',terminalTipIndex=0,terminalTipTimer=null;
async function terminalPage(){
 const [history,status,context,pending]=await Promise.all([api('/api/terminal/history'),api('/api/chatgpt/status'),api('/api/terminal/context'),api('/api/terminal/approvals')]);
 chatgptState=status;terminalHistory=history.map(h=>h.raw_input).reverse();terminalHistoryIndex=terminalHistory.length;
 let last={};try{last=JSON.parse(history[0]?.result||'{}')}catch{}
 const previews=pending.filter(a=>(last.actions||[]).some(x=>x.id===a.id));
 terminalPendingApproval=previews.length===1?{id:previews[0].id,checksum:previews[0].checksum}:null;terminalChoices=previews.length?[]:(last.choices||[]);
 scheduleTerminalTips();
 const tips=context.tips||[],tip=tips.length?tips[terminalTipIndex++%tips.length]:null;
 return heading('AI Terminal','Talk to your workspace. Review exact actions before anything becomes public.')+'<div class="row">'+link('Approval Center','#control-approvals','btn ghost')+link('Automations','#automations','btn ghost')+'<span class="pill">&#9679; '+esc(config.ai_provider||'Choose an AI provider')+'</span></div>'+
 '<section class="terminal-shell terminal-interactive"><div id="terminal-run-state" class="terminal-state" role="status">'+(terminalCommandId?'Working in the background ? Ctrl+C stops the current command':'Ready ? Enter sends, Shift+Enter adds a line')+'</div><div id="terminal-output" class="terminal-output" role="log" aria-live="polite"><div class="terminal-entry">What would you like to do? Ask about drafts, connections, limits or Trend Radar.</div>'+history.slice(0,8).reverse().map(h=>'<div class="terminal-entry"><strong>&gt; '+esc(h.raw_input)+'</strong><small> '+esc(h.status)+'</small><pre>'+esc(historySummary(h))+'</pre></div>').join('')+'</div>'+
 '<div id="terminal-approvals">'+previews.map(actionCard).join('')+'</div><div id="terminal-choices">'+(previews.length===1?approvalChoicesHTML():questionHTML(last.question,terminalChoices))+'</div>'+
 '<form id="terminal-form" class="terminal-prompt"><span aria-hidden="true">&gt;</span><textarea name="command" id="terminal-input" rows="3" aria-label="Terminal prompt" autocomplete="off" spellcheck="true" placeholder="Ask a question or type a command. Shift+Enter for another line.">'+esc(terminalDraftInput)+'</textarea><button type="submit" class="terminal-send" aria-label="Send command">Enter &#8629;</button></form>'+
 '<div class="terminal-toolbar">'+cgButton('Stop ? Ctrl+C','terminal-stop')+cgButton('Help','terminal-help')+cgButton('Clear display','terminal-clear')+cgButton('Copy output','terminal-copy')+'</div><div class="terminal-tip">'+(tip?'Try <button type="button" class="ghost tiny" data-terminal-fill="'+esc(tip.command)+'">'+esc(tip.label)+'</button> '+esc(tip.reason):'Type help for available commands.')+'</div></section><p class="hint">Edit freely; no silent text truncation. Requests above 64,000 characters show an error and stay editable. History stays local. Never paste credentials. All operations use the same services and approvals as the GUI.</p>';
}
function approvalChoicesHTML(){return '<div class="terminal-options"><p>Review the exact preview. Choose or type:</p><button type="button" data-terminal-choice="1">1 ? Yes, execute this action</button><button type="button" data-terminal-choice="2">2 ? No, cancel it</button><button type="button" data-terminal-choice="3">3 ? Type changes / another request</button></div>'}
function questionHTML(question,choices){if(!choices?.length)return '';return '<div class="terminal-options"><p>'+esc(question||'What would you like to do next?')+'</p>'+choices.map((c,i)=>'<button type="button" data-terminal-choice="'+(i+1)+'">'+(i+1)+' ? '+esc(c.label)+'</button>').join('')+'<button type="button" data-terminal-fill="">Type another response</button></div>'}
function terminalFill(text){terminalDraftInput=text;const input=$('#terminal-input');if(input){input.value=text;input.focus?.();input.setSelectionRange?.(text.length,text.length)}}
function resolveTerminalChoice(text){if(!terminalPendingApproval&&terminalChoices.length){const word=text.trim().toLowerCase();if(["yes","no"].includes(word)){const matches=terminalChoices.filter(c=>c.label.toLowerCase().startsWith(word));if(matches.length===1)return matches[0].command}}const n=Number(text.trim());if(!Number.isInteger(n)||n<1)return text;if(terminalPendingApproval){if(n===1)return 'yes';if(n===2)return 'no';if(n===3){terminalFill('');terminalOutput('Type the changes you want. The pending action has not executed; a revised action needs a fresh preview.');return null}throw Error('Choose 1 for yes, 2 for no, or 3 to type changes.')}if(terminalChoices.length){const choice=terminalChoices[n-1];if(!choice)throw Error('Choose a displayed number or type your own request.');return choice.command}return text}
async function stopTerminal(){if(!terminalCommandId)return;const id=terminalCommandId;try{await api('/api/terminal/cancel/'+id,'POST')}finally{terminalAbort?.abort()}}
document.addEventListener('keydown',e=>{
 if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='c'&&typeof route!=='undefined'&&route==='terminal'&&terminalCommandId){e.preventDefault();stopTerminal().catch(errorPanel);return}
 if(e.target.id!=='terminal-input'||e.isComposing)return;
 if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();e.target.form.requestSubmit();return}
 if(!['ArrowUp','ArrowDown'].includes(e.key)||e.shiftKey||e.target.selectionStart!==e.target.selectionEnd)return;
 const input=e.target;if(input.value.includes('\n'))return;
 if((e.key==='ArrowUp'&&input.selectionStart!==0)||(e.key==='ArrowDown'&&input.selectionStart!==input.value.length))return;
 e.preventDefault();if(terminalHistoryIndex===terminalHistory.length)terminalScratch=input.value;
 terminalHistoryIndex=Math.max(0,Math.min(terminalHistory.length,terminalHistoryIndex+(e.key==='ArrowUp'?-1:1)));
 terminalFill(terminalHistoryIndex===terminalHistory.length?terminalScratch:terminalHistory[terminalHistoryIndex]||'');
});
document.addEventListener('input',e=>{if(e.target.id==='terminal-input')terminalDraftInput=e.target.value});
document.addEventListener('click',async e=>{
 const choice=e.target.closest('[data-terminal-choice]'),fill=e.target.closest('[data-terminal-fill]');
 if(fill){terminalFill(fill.dataset.terminalFill);return}
 if(choice)await runUIAction(choice,()=>runTerminal(choice.dataset.terminalChoice),'Terminal choice',{track:false});
});

function scheduleTerminalTips(){if(terminalTipTimer)clearTimeout(terminalTipTimer);terminalTipTimer=setTimeout(async()=>{terminalTipTimer=null;if(typeof route==='undefined'||route!=='terminal')return;try{if(!terminalCommandId){const d=await api('/api/terminal/context'),tip=d.tips?.[terminalTipIndex++%d.tips.length],box=$('.terminal-tip');if(tip&&box)box.innerHTML='Try <button type="button" class="ghost tiny" data-terminal-fill="'+esc(tip.command)+'">'+esc(tip.label)+'</button> '+esc(tip.reason)}}catch{}finally{scheduleTerminalTips()}},30000)}
