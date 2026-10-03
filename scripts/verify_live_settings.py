"""Opt-in live local Settings audit. Never publishes, deletes, or changes credentials.
Run propose first, inspect the private preview, then apply approved profile fields.
"""
import argparse,json,os
from pathlib import Path
import httpx

parser=argparse.ArgumentParser()
parser.add_argument('mode',choices=['propose','apply','check','controls'])
args=parser.parse_args()
private=Path(os.environ['LOCALAPPDATA'])/'XEngagementAssistant'/'backups'
private.mkdir(parents=True,exist_ok=True)
record=private/'settings-repair-review.json'
c=httpx.Client(base_url='http://127.0.0.1:8787',timeout=180)
boot=c.get('/api/bootstrap');boot.raise_for_status();c.headers['X-CSRF-Token']=boot.json()['csrf']
sections=('my_profile','brand_voice','voice','product')
def read():
    r=c.get('/api/settings');r.raise_for_status();return r.json()['settings']
def terminal(text,**kw):
    response=c.post('/api/terminal/run',json={'text':text,'timezone':'Africa/Nairobi',**kw});response.raise_for_status()
    events=[json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
    errors=[e['text'] for e in events if e['type']=='error']
    if errors:raise RuntimeError('; '.join(errors))
    result=next((e for e in events if e['type']=='result'),None)
    if not result:raise RuntimeError('No completion receipt received')
    return result
if args.mode=='propose':
    before=read()
    # The backup excludes credentials and stays in the private application directory.
    backup=c.get('/api/export/database');backup.raise_for_status()
    (private/'before-settings-repair.sqlite3').write_bytes(backup.content)
    result=terminal('Please fill missing fields in My Profile, Brand Voice, Writing Voice and My Product using my saved profile and product information. Use settings.updateContext to prepare ONE exact review containing all four sections. Preserve all existing nonempty values. Draft sensible voice preferences consistent with natural, useful, non-spam engagement; do not invent experiences, customers, revenue or a website. Leave unknown factual fields empty. Do not change any other settings, accounts, safety limits or automations. Show which sections need approval, not a claim that they were already saved.')
    actions=result.get('actions',[])
    if len(actions)!=1 or actions[0]['tool']!='settings.updateContext':raise RuntimeError('AI did not produce one profile-only preview; nothing approved')
    proposed=json.loads(actions[0]['arguments'])
    if set(proposed)!=set(sections):raise RuntimeError('AI omitted a requested section; nothing approved')
    for section,fields in proposed.items():
        for key,value in fields.items():
            old=before[section].get(key)
            if old and old!=value:raise RuntimeError('AI tried to overwrite existing information; nothing approved')
    record.write_text(json.dumps({'before':{k:before[k] for k in sections},'other_settings':{k:v for k,v in before.items() if k not in sections},'action':actions[0],'writes_before':c.get('/api/dashboard').json()['today_writes']},indent=2),encoding='utf-8')
    print(json.dumps({'state':result['report']['state'],'sections':{k:list(v) for k,v in proposed.items()},'review_file':str(record)}))
elif args.mode=='apply':
    review=json.loads(record.read_text(encoding='utf-8'));action=review['action']
    if action['tool']!='settings.updateContext':raise RuntimeError('Not a profile-only approval')
    result=terminal('yes',approval_id=action['id'],approval_checksum=action['checksum'])
    actual=read();receipt=result['data'][0]['result']
    assert receipt.get('verified') is True
    proposed=json.loads(action['arguments'])
    for section,fields in proposed.items():
        for key,value in fields.items():assert actual[section][key]==value
    for section,fields in review['before'].items():
        for key,value in fields.items():
            if value:assert actual[section][key]==value
    assert {k:v for k,v in actual.items() if k not in sections}==review['other_settings']
    assert c.get('/api/dashboard').json()['today_writes']==review['writes_before']
    review['verified']=True;review['after']={k:actual[k] for k in sections}
    record.write_text(json.dumps(review,indent=2),encoding='utf-8')
    print(json.dumps({'verified':True,'populated_fields':{k:sum(bool(v) for v in actual[k].values()) for k in sections},'public_writes_added':0}))
else:
    actual=read()
    review=json.loads(record.read_text(encoding='utf-8')) if args.mode=='check' else {'verified':True,'after':{k:actual[k] for k in sections},'writes_before':c.get('/api/dashboard').json()['today_writes']}
    assert review['verified'] and {k:actual[k] for k in sections}==review['after']
    paths=['/health','/','/api/dashboard','/api/profile','/api/settings','/api/social/accounts','/api/social/feed','/api/social/inbox','/api/social/trends','/api/social/brief','/api/social/analytics','/api/social/watch','/api/social/market','/api/social/ideas','/api/media','/api/schedule','/api/history','/api/terminal/automations','/api/terminal/approvals','/api/terminal/memory','/api/topics','/api/mutes','/api/social/usage','/api/social/planner']
    for path in paths:c.get(path).raise_for_status()
    # Exercise the exact Settings save endpoints using retained, real values.
    c.put('/api/profile',json=actual['my_profile']).raise_for_status()
    for section in ('brand_voice','voice','product'):
        c.put('/api/settings',json={section:actual[section]}).raise_for_status()
    memory=c.get('/api/terminal/memory').json()
    value=next((m['value'] for m in memory if m['key']=='tone'),actual['voice'].get('tone','Useful, natural engagement without spam; respond to specific points and do not invent personal experiences.'))
    if not value:raise RuntimeError('No real tone preference is available')
    r=c.post('/api/terminal/request',json={'tool':'memory.savePreference','arguments':{'key':'tone','value':value}});r.raise_for_status()
    assert r.json()['data'][0]['result']['verified']
    for command in ['show profile','show context','show settings','show limits','accounts','show drafts','show schedule','show history','show media','show ideas','show analytics','show topics','show approvals','show automations','show memory']:
        assert terminal(command).get('success')
    assert {k:read()[k] for k in sections}==review['after']
    assert c.get('/api/dashboard').json()['today_writes']==review['writes_before']
    print(json.dumps({'dashboard_endpoints':len(paths),'read_commands':15,'profile_save_buttons':4,'visible_preference_save':True,'saved_values_preserved':True,'public_writes_added':0}))
