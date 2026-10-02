"""Explicit opt-in installed-app checks. Never runs as part of the test suite.
Publishing is limited to one labeled original and, only on success, self-reply/quote.
No likes, follows, DMs, third-party replies, or social media uploads.
"""
import argparse
from datetime import datetime,timedelta,timezone
import io,json,re,time
from pathlib import Path
import httpx
from PIL import Image

parser=argparse.ArgumentParser()
parser.add_argument('--allow-live-publish',action='store_true')
parser.add_argument('--expected-username',default='')
args=parser.parse_args()
report={'started_at':datetime.now(timezone.utc).isoformat(),'checks':[],'public_posts':[],'local_drafts':[]}
c=httpx.Client(base_url='http://127.0.0.1:8787',timeout=150)
boot=c.get('/api/bootstrap').json();c.headers['X-CSRF-Token']=boot['csrf']
username=(boot.get('profile') or {}).get('username','')
if args.allow_live_publish and (not args.expected_username or username.lower()!=args.expected_username.lower()):
    raise SystemExit('Publishing refused: expected username does not match the connected X account.')

def note(name,ok,**data):
    item={'check':name,'passed':ok,**data};report['checks'].append(item);print(json.dumps(item,ensure_ascii=True),flush=True)

def request(name,method,path,body=None,expected=200,**kwargs):
    r=c.request(method,path,json=body,**kwargs)
    try:value=r.json()
    except ValueError:value={}
    note(name,r.status_code==expected,http=r.status_code,**({'error':value.get('error'),'technical':value.get('technical')} if r.status_code>=400 else {}))
    return value

def terminal(text,**extra):
    r=c.post('/api/terminal/run',json={'text':text,'timezone':'Africa/Nairobi',**extra})
    events=[json.loads(line[6:]) for line in r.text.splitlines() if line.startswith('data: ')] if r.status_code==200 else []
    errors=[e['text'] for e in events if e['type']=='error']
    results=[e for e in events if e['type']=='result']
    note('terminal: '+text,r.status_code==200 and not errors and bool(results),errors=errors)
    return events

def draft(text,kind='original',feed_id=None):
    d=request('save '+kind+' draft','POST','/api/social/drafts',{'platform':'x','kind':kind,'text':text,'feed_id':feed_id})
    if 'id' not in d:raise RuntimeError('Draft save failed')
    report['local_drafts'].append(d['id']);return d

def publish(d):
    events=terminal('publish '+str(d['id']))
    previews=[e['request'] for e in events if e['type']=='approval']
    if len(previews)!=1:raise RuntimeError('No unique exact-content preview; publishing stopped')
    snap=json.loads(previews[0]['snapshot'])
    if snap['draft']['text']!=d['text']:raise RuntimeError('Draft changed; publishing stopped')
    events=terminal('yes',approval_id=previews[0]['id'],approval_checksum=previews[0]['checksum'])
    ids=[]
    for e in events:
        if e['type']=='tool_result' and e.get('data',{}).get('published'):ids.extend(e['data']['post_ids'])
    for id in ids:report['public_posts'].append({'id':id,'url':'https://x.com/'+username+'/status/'+id,'kind':d['kind']})
    return ids

try:
    for path in ['/health','/api/dashboard','/api/social/accounts','/api/social/feed','/api/social/inbox','/api/social/trends','/api/social/brief','/api/social/analytics','/api/social/watch','/api/social/market','/api/social/ideas','/api/media','/api/schedule','/api/history','/api/settings','/api/terminal/automations','/api/terminal/approvals','/api/terminal/memory']:
        request('read '+path,'GET',path)
    request('live X profile','POST','/api/health/x')
    request('live selected AI health','POST','/api/health/ai')
    request('invalid URL message','GET','/parse-tweet-url?tweet_url=invalid',expected=400)
    parsed=request('URL parsing','GET','/parse-tweet-url',params={'tweet_url':'https://x.com/example/status/123456789'})
    note('extracted tweet ID',parsed.get('tweet_id')=='123456789')
    search=request('paid search or persisted fallback','POST','/api/search',{'query':'engagement tools lang:en','max_results':10})
    note('discovery mode explained',search.get('mode') in ['api','web'],mode=search.get('mode'),message=search.get('message'))
    request('official X feed availability','POST','/api/social/sync/x',{'kind':'feed'})
    for command in ['status','is Facebook connected?','how do I connect fb','show history','show schedule','show media','show ideas','show analytics','scan trends','yes','please show my saved drafts']:
        terminal(command)
    plan=request('live weekly planner','POST','/api/social/suggest',{'task':'Weekly plan','platform':'x','timezone':'Africa/Nairobi','text':'Share useful PDF and reading workflows; introduce my open-source engagement app without inventing results.'})
    note('seven-day plan returned',bool(plan.get('text')) and plan.get('text')!='SKIP' and len(plan.get('dates',[]))==7,characters=len(plan.get('text','')))
    saved=request('planner persisted','GET','/api/social/planner')
    note('saved plan matches',saved.get('text')==plan.get('text'))
    item=request('manual text import','POST','/api/social/import',{'platform':'x','author':username,'text':'LOCAL APP TEST, not a published tweet: What helps you keep useful PDF annotations organized?'})
    response=request('live AI reply draft','POST','/api/social/analyze',{'id':item['id']})
    note('AI reply is draft or explicit skip',response.get('status')=='draft' or bool(response.get('skipped')))
    if response.get('id'):report['local_drafts'].append(response['id'])
    watches=request('read watchlist','GET','/api/social/watch')
    if not any(w.get('platform')=='x' and w.get('handle','').lower()==username.lower() for w in watches):
        request('add own account to watchlist','POST','/api/social/watch',{'platform':'x','handle':username,'topics':'app testing','enabled':False,'auto_draft':False})
        watches=request('verify watchlist saved','GET','/api/social/watch')
        for w in watches:
            if w.get('platform')=='x' and w.get('handle','').lower()==username.lower():request('remove test watch','DELETE','/api/social/watch/'+str(w['id']))
    idea=request('save idea' ,'POST','/api/social/ideas',{'title':'Acceptance test idea','text':'Explain how exact-content approval works.'})
    if idea.get('id'):request('remove test idea','DELETE','/api/social/ideas/'+str(idea['id']))
    image=Image.new('RGB',(64,64),(50,70,90));buffer=io.BytesIO();image.save(buffer,format='PNG')
    upload=request('local media upload','POST','/api/media',files={'file':('acceptance-test.png',buffer.getvalue(),'image/png')})
    if upload.get('id'):
        request('media metadata','PUT','/api/media/'+upload['id'],{'alt_text':'A plain square used for a local app test','tags':'test'})
        derivative=request('non-destructive resize','POST','/api/media/'+upload['id']+'/transform',{'width':32,'height':32})
        if derivative.get('id'):request('remove test derivative','DELETE','/api/media/'+derivative['id'])
        request('remove test media','DELETE','/api/media/'+upload['id'])
    reminder=draft('LOCAL TEST: verify schedule and cancellation; do not publish.')
    request('approve reminder draft','POST','/api/drafts/'+str(reminder['id'])+'/approve')
    request('schedule manual reminder','POST','/api/social/drafts/'+str(reminder['id'])+'/schedule',{'due_at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),'timezone':'Africa/Nairobi','delivery':'manual'})
    rows=request('read scheduled reminder','GET','/api/schedule')
    for row in rows:
        if row.get('draft_id')==reminder['id']:request('cancel test reminder','DELETE','/api/schedule/'+str(row['id']))
    for kind in ['settings','drafts','history','database']:
        r=c.get('/api/export/'+kind)
        note('export '+kind,r.status_code==200,http=r.status_code,bytes=len(r.content))
    if args.allow_live_publish:
        stamp=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
        original=draft("App test: checking my local social assistant's approval and publishing flow. Which would help you more: thoughtful reply drafts or a weekly content plan? Test "+stamp)
        ids=publish(original)
        if ids:
            source=request('import confirmed own post','POST','/api/feed/import',{'tweet_url':'https://x.com/'+username+'/status/'+ids[0],'text':original['text']})
            reply=draft('Reply test on my own post: this checks exact-content confirmation. I will remove this test later. '+stamp,'reply',source['id'])
            publish(reply)
            quote=draft('Quote workflow test for my local engagement app. This references my own test post and was explicitly approved. '+stamp,'quote',source['id'])
            publish(quote)
        else:note('self-reply and quote live tests',False,blocked='No confirmed original post. Dependent public writes were not attempted.')
    print('PUBLIC_POSTS',json.dumps(report['public_posts']),flush=True)
finally:
    report['finished_at']=datetime.now(timezone.utc).isoformat()
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/live-acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    c.close()
