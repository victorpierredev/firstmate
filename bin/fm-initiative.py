#!/usr/bin/env python3
"""Implementation of the wire contract owned by fm-initiative.sh --help."""
import base64
import contextlib
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import time
from urllib.parse import quote, urlsplit
import uuid

BIN = Path(__file__).absolute().parent
HOME = Path(os.environ['FM_HOME']).resolve(strict=True)
DATA = Path(os.environ.get('FM_DATA_OVERRIDE', HOME / 'data')).resolve()
STATE = Path(os.environ.get('FM_STATE_OVERRIDE', HOME / 'state')).resolve()
CONFIG = Path(os.environ.get('FM_CONFIG_OVERRIDE', HOME / 'config')).resolve()
STORE = DATA / 'initiatives'
MARKER = re.compile(r'<!-- firstmate:initiative v=1 id=([0-9a-f-]{36}) -->')
SHA = re.compile(r'[0-9a-f]{40}(?:[0-9a-f]{24})?\Z')

class Refusal(Exception):
    pass

def check(value, message):
    if not value:
        raise Refusal(message)

def text(value):
    check(isinstance(value, str) and value.strip() and not any(ord(c) < 32 and c not in '\n\r\t' for c in value), 'nonempty text required')
    return value

def token(value):
    check(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', value), 'invalid task or generation identity')
    return value

def uid(value):
    check(isinstance(value, str) and str(uuid.UUID(value)) == value, 'invalid UUID')
    return value

def relative(value):
    check(isinstance(value,str) and value and not any(ord(c)<32 or ord(c)==127 for c in value), 'invalid path')
    p=PurePosixPath(value)
    check(not p.is_absolute() and all(x not in ('','..','.') for x in value.split('/')) and '\\' not in value, 'path must be a contained relative path')
    return p

def digest(value):
    return hashlib.sha256(value if isinstance(value,bytes) else value.encode()).hexdigest()

def encode(value):
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()

@contextlib.contextmanager
def directory(path, create=False):
    path=Path(path)
    check(path.is_absolute(), 'absolute directory required')
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            if create:
                try: os.mkdir(part,0o700,dir_fd=fd)
                except FileExistsError: pass
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd); fd=child
        yield fd
    finally:
        os.close(fd)

def read(path, missing=False):
    path=Path(path)
    try:
        with directory(path.parent) as d:
            fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=d)
            with os.fdopen(fd,'rb') as f:
                s=os.fstat(f.fileno())
                check(stat.S_ISREG(s.st_mode) and s.st_nlink==1, 'regular unlinked file required: '+str(path))
                check(s.st_size<=8*1024*1024,'file exceeds 8 MiB bound')
                return f.read(8*1024*1024+1)
    except FileNotFoundError:
        if missing: return None
        raise

def recover_exclusive(path, transaction):
    """Retire only the journaled staging name, never an unexplained hardlink."""
    if not transaction: return
    name=transaction['staging']
    check(re.fullmatch(r'\.initiative-[0-9a-f-]{36}',name),'invalid publication staging name')
    check(digest(transaction['content'])==transaction['digest'],'invalid publication candidate digest')
    with directory(Path(path).parent) as d:
        try: fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=d)
        except FileNotFoundError: return
        with os.fdopen(fd,'rb') as f:
            staged=os.fstat(f.fileno())
            check(stat.S_ISREG(staged.st_mode) and staged.st_nlink in (1,2),'unsafe publication staging file')
            check(digest(f.read(8*1024*1024+1))==transaction['digest'],'publication staging content changed')
        if staged.st_nlink==2:
            target=os.stat(Path(path).name,dir_fd=d,follow_symlinks=False)
            check(stat.S_ISREG(target.st_mode) and target.st_nlink==2 and (target.st_dev,target.st_ino)==(staged.st_dev,staged.st_ino),'publication staging link differs from its destination')
        os.unlink(name,dir_fd=d)
        os.fsync(d)

def transaction(content, original=None):
    return {'content':content.decode(),'digest':digest(content),'original':original,'staging':'.initiative-'+str(uuid.uuid4())}

def put(path, content, exclusive=False, staging=None):
    path=Path(path)
    with directory(path.parent,True) as d:
        prior=read(path,True)
        check(not exclusive or prior is None,'destination exists: '+str(path))
        if prior==content: return
        name=staging or '.initiative-'+str(uuid.uuid4())
        fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=d)
        try:
            with os.fdopen(fd,'wb') as f:
                f.write(content); f.flush(); os.fsync(f.fileno())
            if exclusive:
                os.link(name,path.name,src_dir_fd=d,dst_dir_fd=d,follow_symlinks=False)
                os.unlink(name,dir_fd=d)
            else:
                os.replace(name,path.name,src_dir_fd=d,dst_dir_fd=d)
            os.fsync(d)
        finally:
            try: os.unlink(name,dir_fd=d)
            except FileNotFoundError: pass

@contextlib.contextmanager
def locked():
    with directory(STORE,True) as d:
        fd=os.open('.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600,dir_fd=d)
        try:
            check(os.fstat(fd).st_nlink==1,'unsafe initiative lock')
            deadline=time.monotonic()+5
            while True:
                try:
                    fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB); break
                except BlockingIOError:
                    check(time.monotonic()<deadline,'initiative publisher busy; retry')
                    time.sleep(.05)
            yield
        finally: os.close(fd)

def command(args, timeout=15):
    p=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=timeout)
    check(p.returncode==0, 'observation unavailable: '+(p.stderr.strip() or p.stdout.strip())[:500])
    return p.stdout.strip()

def source(action, value):
    return json.loads(command([BIN/'fm-initiative-source.sh',action,value]))

def config():
    c=json.loads(read(CONFIG/'initiative.json'))
    check(c['version']==1 and c['home']==str(HOME) and c['data']==str(DATA) and c['state']==str(STATE),'wrong publishing home or roots')
    return c

def marker(data):
    found=[]; fence=None
    for line in data.decode('utf-8').splitlines():
        f=re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$',line)
        if f:
            if fence is None: fence=(f[1][0],len(f[1])); continue
            if f[1][0]==fence[0] and len(f[1])>=fence[1] and not f[2].strip(): fence=None
            continue
        if fence is not None: continue
        if line.strip().startswith('<!-- firstmate:initiative'):
            m=MARKER.fullmatch(line.strip())
            check(m is not None,'malformed or unsupported initiative marker')
            found.append(uid(m[1]))
    check(len(found)==1,'exactly one initiative marker is required')
    return found[0]

def human_files(c):
    for key in ['work','archive']:
        root=Path(c['vault'])/c[key]
        with directory(root): pass
        for base,dirs,files in os.walk(root,followlinks=False):
            dirs[:]=[x for x in dirs if not (Path(base)/x).is_symlink()]
            for name in files:
                if name.lower().endswith('.md'):
                    yield Path(base)/name

def human(c,r):
    matches=[]
    for path in human_files(c):
        if path.is_symlink(): continue
        try: data=read(path); identity=marker(data)
        except (OSError,Refusal,ValueError):
            if str(path.relative_to(c['vault']))==r['note']: raise
            continue
        if identity==r['id']: matches.append((path,data))
    check(len(matches)==1,'human note is missing or its identity has conflicting copies')
    path,data=matches[0]
    r['note']=str(path.relative_to(c['vault']))
    return data

def record_path(i):
    return STORE/uid(i)/'record.json'

def load(i):
    r=json.loads(read(record_path(i)))
    check(r['version']==1 and r['home']==str(HOME) and r['id']==i,'wrong initiative owner or identity')
    return r

def records():
    if not STORE.exists(): return []
    with directory(STORE): pass
    return [load(p.name) for p in sorted(STORE.iterdir()) if not p.name.startswith('.')]

def save(r):
    path=record_path(r['id'])
    old=read(path,True)
    if old==encode(r): return
    r['revision']+=1
    put(path,encode(r))

def escape(value):
    return str(value).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('\\','\\\\').replace('|','\\|').replace('\r',' ').replace('\n',' ')

def rendered(r):
    rows=sorted((v for v in r['rows'].values() if not v.get('retired')),key=lambda v:v['order'])
    completed=[v for v in rows if v['status']=='Done']
    active=[v for v in rows if v['status']=='In progress']
    planned=[v for v in rows if v['status']=='Planned']
    blocked=[v for v in rows if v['status']=='Blocked']
    state=f'{len(completed)} of {len(rows)} tasks complete.' if rows else 'The initiative is being specified.'
    if active: state+=f' {len(active)} in progress.'
    if r['completed']: state='The initiative is complete.'
    next_action=r.get('next')
    if r.get('design_pending'): next_action='Review the changes to the plan before starting affected work.'
    elif not r.get('accepted'): next_action='Review the proposed design and agree on the tasks.'
    elif not next_action:
        if active: next_action='Continue '+active[0]['name']+'.'
        elif planned: next_action='Start '+planned[0]['name']+'.'
        elif blocked: next_action='Resolve the decision or dependency that is holding up the work.'
        elif not r['completed']: next_action='Check the completion criteria and remaining decisions.'
        else: next_action='No further implementation is planned.'
    out=[f'# {escape(r["title"])}','', '> This status note is generated. Make changes in the initiative plan.','', '## Goal','',escape(r['goal']),'',
         '## Current state','',state]
    if r.get('position'): out+=['',escape(r['position'])]
    out+=['','## Completed work','']
    out += ['- '+escape(v['name'])+': '+escape(v['explanation']) for v in completed] or ['No tasks are complete yet.']
    out+=['','## Next action','',escape(next_action)]
    blockers=r.get('blockers',[]) or ['Resolve the decision or dependency for '+v['name']+'.' for v in blocked]
    for heading,items in [('Blockers',blockers),('Decisions',r.get('decisions',[]))]:
        if items: out+=['','## '+heading,'']+['- '+escape(x) for x in items]
    out+=['','## Tasks','',f'<!-- firstmate:initiative v=1 id={r["id"]} -->','',
          '| Task | Brief explanation | Status | Commit |','| --- | --- | --- | --- |']
    for row in rows:
        commit='-'
        if row['status']=='Done':
            landing=row['landing']; sha=landing['commit']; short=sha
            try: short=command(['git','-C',row['repo'],'rev-parse','--short=12',sha])
            except (Refusal,subprocess.TimeoutExpired): pass
            check(re.fullmatch('[0-9a-f]{12,64}',short),'invalid commit abbreviation')
            commit=f'`{short}`'
            if landing.get('url'): commit=f'[{commit}]({landing["url"]})'
        out.append(f'| <!-- firstmate:task id={row["id"]} --> {escape(row["name"])} | {escape(row["explanation"])} | {row["status"]} | {commit} |')
    c=config(); link=quote(os.path.relpath(r['note'],c['generated']),safe='/')
    out+=['','## Links','',f'- [Initiative plan]({link})']
    if r.get('source'): out+=['- [Source ticket]('+r['source']+')']
    return ('\n'.join(out)+'\n').encode()

def generated_owner(c):
    root=Path(c['vault'])/c['generated']
    owner=json.loads(read(root/'.firstmate-owner.json'))
    check(owner=={'publisher':c['publisher'],'home':str(HOME)},'generated root belongs to another publisher')
    return root

def companion(c,r):
    name=r['companion']
    check(len(relative(name).parts)==1 and name.endswith('.md'),'invalid companion filename')
    return generated_owner(c)/name

def publish(c,r):
    try:
        human(c,r)
        path=companion(c,r)
        candidate=rendered(r)
        pending=r.get('pending_publication')
        if pending and pending.get('staging'): recover_exclusive(path,pending)
        current=read(path,True)
        if pending and current is not None and digest(current)==pending['digest']:
            r['published']=pending['digest']; r['published_content']=pending['content']; r['pending_publication']=None
        baseline=r.get('published')
        if current is not None and digest(current) not in (baseline,digest(candidate)):
            r.setdefault('conflicts',{})[digest(current)]=current.decode('utf-8',errors='replace')
            raise Refusal('generated companion changed; explicit recovery required')
        if current!=candidate:
            r['pending_publication']=transaction(candidate,r.get('published_content'))
            save(r)
            put(path,candidate,exclusive=current is None,staging=r['pending_publication']['staging'])
            check(read(path)==candidate,'generated publication readback failed')
        r['published']=digest(candidate); r['published_content']=candidate.decode(); r['pending_publication']=None; r['publication_error']=''
        if r.get('recovery_pending'):
            history=r.setdefault('publication_history',[])
            history.append(r.pop('recovery_pending'))
            while len(history)>8 or len(encode(history))>256*1024: history.pop(0)
            r['conflicts']={}
    except (OSError,Refusal,ValueError) as e:
        r['publication_error']=str(e)
    save(r)

def notify(r):
    issues=[r.get('publication_error','')]
    if r.get('design_pending'): issues.append('human design changed; approval required before affected dispatch')
    issues += [v.get('freshness','') for v in r['rows'].values() if not v.get('retired')]
    issue='; '.join(sorted(set(x for x in issues if x)))
    key=digest(issue) if issue else ''
    if key!=r.get('notified',''):
        if issue:
            command([BIN/'fm-initiative-source.sh','wake',r['id'],key])
        r['notified']=key; save(r)

def metadata(task):
    raw=read(STATE/(token(task)+'.meta'),True)
    if raw is None: return None
    fields={}
    for line in raw.decode().splitlines():
        k,sep,v=line.partition('=')
        if sep:
            check(k not in fields,'duplicated task metadata field')
            fields[k]=v
    check(fields.get('kind')!='secondmate' and not fields.get('remote_host'),'cross-home initiative execution is unsupported')
    token(fields.get('spawn_gen',''))
    return fields

def attempt_for(row,m):
    check(str(Path(m['project']).resolve())==row['repo'],'task repository differs from accepted binding')
    return {'generation':m['spawn_gen'],'scope':row['scope_revision'],'metadata':m}

def bindings(task):
    return [(r,row['id']) for r in records() for row in r['rows'].values() if row['task']==task and not row.get('retired')]

def git_contains(repo,commit,target):
    check(SHA.fullmatch(commit),'full commit ID required')
    command(['git','-C',repo,'cat-file','-e',commit+'^{commit}'])
    command(['git','-C',repo,'merge-base','--is-ancestor',commit,'refs/heads/'+target])

def recover_local(row,m=None):
    intent=row.get('local_intent')
    if not intent: return row.get('landing')
    check(intent['scope']==row['scope_revision'],'local intent belongs to a different scope')
    if m: check(intent['generation']==m['spawn_gen'],'local intent belongs to a different generation')
    git_contains(row['repo'],intent['commit'],row['target'])
    git_contains(row['repo'],intent['before'],row['target'])
    return {**intent,'provenance':'fm-merge-local'}

def retire_unapplied_intent(row):
    """Retire a durable intent only when the target proves Git never applied it."""
    intent=row['local_intent']
    tip=command(['git','-C',row['repo'],'rev-parse','refs/heads/'+row['target']])
    applied=subprocess.run(['git','-C',row['repo'],'merge-base','--is-ancestor',intent['commit'],tip],capture_output=True,timeout=15)
    check(tip==intent['before'] and applied.returncode!=0,'a different local landing intent requires reconciliation')
    row.setdefault('local_intent_history',[]).append(intent); row['local_intent']=None

def remember_landing(row,landing):
    if landing not in row['landing_history']: row['landing_history'].append(copy.deepcopy(landing))
    row.update(landing=landing,obligation=None,local_intent=None)

def verified_delivery(row,m,current):
    check(re.match(r'^state: done .*source: run-step(?:\s|$)',current),'selected no-mistakes delivery has not been verified')
    return {'generation':m['spawn_gen'],'scope':row['scope_revision'],'observation':current,'head':command(['git','-C',m['worktree'],'rev-parse','HEAD'])}

def cleanup_evidence(row,m):
    if m.get('mode')=='local-only':
        receipt=recover_local(row,m)
        check(receipt is not None,'local landing evidence is missing; retain task before cleanup')
        remember_landing(row,receipt)
    if m.get('mode')=='no-mistakes':
        proof=row.get('delivery_verified') or {}
        check(proof.get('generation')==m['spawn_gen'] and proof.get('scope')==row['scope_revision'],'verified delivery evidence is missing; retain task before cleanup')
        check(proof.get('head')==command(['git','-C',m['worktree'],'rev-parse','HEAD']),'task code changed after delivery verification; retain task before cleanup')

def capture(c,q):
    task=token(q['task']); event=q['event']
    check(event in ('spawn','merge','local-intent','local','local-retry','delivery','teardown','discard'),'unknown lifecycle event')
    observed_meta=None; observed_head=None; current=None; landed=False; unlanded=False
    # Read the execution owner before the initiative lock and, at the caller,
    # before cleanup takes any destructive-operation locks.
    if event=='delivery' and bindings(task):
        observed_meta=metadata(task)
        if observed_meta and observed_meta.get('mode')=='no-mistakes':
            observed_head=command(['git','-C',observed_meta['worktree'],'rev-parse','HEAD'])
            current=source('task',task)['current']
    with locked():
        for r,rid in bindings(task):
            row=r['rows'][rid]; m=metadata(task)
            check(m is not None,'task metadata required before evidence capture')
            proposed=attempt_for(row,m)
            if event=='delivery':
                check(m==observed_meta,'task generation changed during delivery observation')
                if m.get('mode')=='no-mistakes' and not row.get('landing'):
                    proof=verified_delivery(row,m,current)
                    check(proof['head']==observed_head,'task code changed during delivery observation')
                    row['delivery_verified']=proof
                save(r); continue
            if event=='spawn':
                check(m['spawn_gen'] not in row.get('retired_generations',[]),'reopened scope requires a new dispatch generation')
                if row.get('attempt')!=proposed:
                    if row.get('attempt'): row['attempt_history'].append(row['attempt'])
                    row['attempt']=proposed
                row['started']=True
            else:
                check(row.get('attempt') and row['attempt']['generation']==proposed['generation'] and row['attempt']['scope']==proposed['scope'],'stale attempt generation or scope')
                row['attempt']=proposed
                if not row.get('landing'):
                    previous=row.get('obligation') or {}
                    row['obligation']={**previous,'event':event,'attempt':copy.deepcopy(proposed)}
                if event=='merge':
                    identity=source('pr',q['pr'])
                    check(not m.get('pr') or m['pr']==identity['url'],'stale PR identity for this attempt')
                    if not row.get('landing'): row['obligation']['pr']=identity['url']
                if event=='local-retry':
                    if row.get('landing'): git_contains(row['repo'],row['landing']['commit'],row['target'])
                    if row.get('local_intent'):
                        check(row['local_intent']['generation']==m['spawn_gen'],'local intent belongs to a different generation')
                        try: remember_landing(row,recover_local(row,m))
                        except Refusal: pass
                    landed=bool(row.get('landing'))
                    if landed and q.get('tip'):
                        check(SHA.fullmatch(q['tip']),'full commit ID required')
                        contained=subprocess.run(['git','-C',row['repo'],'merge-base','--is-ancestor',q['tip'],'refs/heads/'+row['target']],capture_output=True,timeout=15)
                        unlanded=unlanded or contained.returncode!=0
                if event in ('local-intent','local'):
                    check(m.get('mode')=='local-only' and q['target']==row['target'],'wrong local landing mode or target')
                    git_contains(row['repo'],q['before'],row['target'])
                    check(SHA.fullmatch(q['after']),'full commit ID required')
                    command(['git','-C',row['repo'],'merge-base','--is-ancestor',q['before'],q['after']])
                    expected=q['before'] if event=='local-intent' else q['after']
                    check(command(['git','-C',row['repo'],'rev-parse','refs/heads/'+row['target']])==expected,'local receipt must be captured at the exact serialized target update')
                    receipt={'commit':q['after'],'before':q['before'],'repo':row['repo'],'target':row['target'],'scope':row['scope_revision'],'generation':m['spawn_gen']}
                    if event=='local-intent':
                        check(q['before']!=q['after'],'no new local integration result to record')
                        if row.get('local_intent') and row['local_intent']!=receipt: retire_unapplied_intent(row)
                        row['local_intent']=receipt
                    else:
                        check(not row.get('local_intent') or row['local_intent']==receipt,'local receipt differs from its durable intent')
                        remember_landing(row,{**receipt,'provenance':'fm-merge-local'})
                if event in ('teardown','discard') and not row.get('landing'):
                    try: cleanup_evidence(row,m)
                    except Refusal as e:
                        if event!='discard': raise
                        row.setdefault('abandoned',[]).append({'attempt':copy.deepcopy(proposed),'reason':str(e)})
                        row['started']=False
                        if row.get('local_intent'):
                            try: retire_unapplied_intent(row)
                            except Refusal: pass
            save(r)
    check(not unlanded,'task branch has commits beyond its recorded landing; reopen the row with the newly accepted scope before merging again')
    return {'captured':task,'event':event,'landed':landed}

def github(path):
    # gh-axi renders ordinary JSON as TOON. Base64 is an explicit lossless body
    # transport; refuse truncated/unknown envelopes rather than guessing fields.
    out=command(['gh-axi','api',path,'--jq','. | tojson | @base64','--full'])
    match=re.fullmatch(r'api_response:\n  body: ([A-Za-z0-9+/=]+)\n  truncated: false',out)
    check(match is not None,'unsupported gh-axi API response envelope')
    return json.loads(base64.b64decode(match[1],validate=True))

def forge_landing(row):
    coverage=row.get('coverage') or {}
    check(coverage.get('scope')==row['scope_revision'],'explicit accepted task coverage is missing')
    identity=source('pr',coverage['pr'])
    check(identity['provider']=='github','final-object verification is unavailable for this provider; retain the landing obligation')
    origin=command(['git','-C',row['repo'],'remote','get-url','origin'])
    canonical=origin.replace('git@github.com:','https://github.com/').removesuffix('.git')
    check(canonical=='https://github.com/'+identity['path'],'forge repository differs from the bound repository')
    base='/repos/'+identity['path']
    pr=github(base+'/pulls/'+identity['number'])
    check(pr.get('html_url')==identity['url'],'provider returned a different pull request')
    if pr.get('merged') is False: return None
    check(pr.get('merged') is True,'merge state is unavailable')
    check(pr['base']['ref']==row['target'] and pr['base']['repo']['full_name']==identity['path'],'merged delivery targets a different integration branch or repository')
    commit=pr.get('merge_commit_sha','')
    check(SHA.fullmatch(commit or ''),'provider did not supply a final integrated object')
    obj=github(base+'/git/commits/'+commit)
    check(obj.get('sha')==commit,'final commit object is unavailable')
    comparison=github(base+'/compare/'+commit+'...'+quote(row['target'],safe=''))
    check(comparison.get('status') in ('ahead','identical') and comparison.get('merge_base_commit',{}).get('sha')==commit,'final commit is not on the intended integration history')
    attempt=row.get('attempt') or (row.get('obligation') or {}).get('attempt')
    check(attempt and attempt['scope']==row['scope_revision'],'landing attempt scope is unproven')
    mode=attempt['metadata'].get('mode')
    check(mode in ('direct-PR','no-mistakes'),'forge delivery mode is unproven')
    if row.get('obligation',{}):
        observed_pr=row['obligation'].get('pr')
        check(not observed_pr or observed_pr==identity['url'],'observed merge has different accepted coverage')
    if mode=='no-mistakes':
        proof=row.get('delivery_verified') or {}
        check(proof.get('generation')==attempt['generation'] and proof.get('scope')==row['scope_revision'],'selected no-mistakes delivery has not been verified')
    return {'commit':commit,'repo':row['repo'],'target':row['target'],'scope':row['scope_revision'],'pr':identity['url'],'url':canonical+'/commit/'+commit,'provenance':'github-rest-merged-object','generation':attempt['generation']}

def landing_still_present(row):
    landing=row['landing']
    if landing['provenance']=='fm-merge-local':
        command(['git','-C',row['repo'],'cat-file','-e',landing['commit']+'^{commit}'])
        p=subprocess.run(['git','-C',row['repo'],'merge-base','--is-ancestor',landing['commit'],'refs/heads/'+row['target']],capture_output=True,timeout=15)
        check(p.returncode in (0,1),'integration history unavailable')
        return p.returncode==0
    identity=source('pr',landing['pr'])
    comparison=github('/repos/'+identity['path']+'/compare/'+landing['commit']+'...'+quote(row['target'],safe=''))
    return comparison.get('status') in ('ahead','identical') and comparison.get('merge_base_commit',{}).get('sha')==landing['commit']

def observe(row, allow_landing=True):
    if row.get('landing'):
        check(row['landing']['scope']==row['scope_revision'],'landing scope differs')
        if not landing_still_present(row):
            return {'status':'Blocked','freshness':'accepted landing was removed from the integration history; scope reconciliation required'}
        return {'status':'Done','freshness':'','obligation':None}
    if row.get('local_intent') and allow_landing:
        landing=recover_local(row,metadata(row['task']))
        return {'status':'Done','freshness':'','landing':landing,'landing_history':row['landing_history']+[landing],'local_intent':None,'obligation':None}
    attempt=row.get('attempt') or {}
    can_verify=attempt.get('metadata',{}).get('mode')!='no-mistakes' or row.get('delivery_verified')
    if allow_landing and row.get('coverage') and attempt and can_verify:
        landing=forge_landing(row)
        if landing:
            return {'status':'Done','freshness':'','landing':landing,'landing_history':row['landing_history']+[landing],'obligation':None}
    before_meta=metadata(row['task'])
    before_head=command(['git','-C',before_meta['worktree'],'rev-parse','HEAD']) if before_meta and before_meta.get('mode')=='no-mistakes' else None
    o=source('task',row['task'])
    check(o['result']=='found','work item unavailable; retaining last verified status')
    parts=o['state'].split()
    check(len(parts)==3 and parts[0] in ('queued','in_flight','done','held'),'unknown structured backlog state')
    state,held,blocked=parts
    check(held in ('yes','no') and blocked in ('yes','no'),'unknown structured blocker flags')
    m=metadata(row['task'])
    check(m==before_meta,'task generation changed during observation; retry')
    result={'freshness':''}
    if m:
        if m['spawn_gen'] in row.get('retired_generations',[]):
            return {'status':'Planned','freshness':'reopened scope awaits a new dispatch generation'}
        a=attempt_for(row,m)
        if state=='in_flight':
            result['attempt']=a; result['started']=True
        if row.get('attempt') and row['attempt']['generation']!=m['spawn_gen']:
            check(state=='in_flight','replacement attempt has not committed dispatch')
    current=o['current']
    if m and re.match(r'^state: done .*source: run-step',current):
        result['delivery_verified']=verified_delivery(row,m,current)
        check(before_head is None or result['delivery_verified']['head']==before_head,'task code changed during delivery observation')
    prevents=held=='yes' or blocked=='yes' or state=='held' or bool(re.match(r'^state: (blocked|paused|failed)\b',current))
    result['status']='Blocked' if prevents else ('In progress' if row['started'] or state=='in_flight' else 'Planned')
    if allow_landing and result.get('delivery_verified') and row.get('coverage'):
        try:
            landing=forge_landing({**row,**result})
            if landing: result.update(status='Done',landing=landing,landing_history=row['landing_history']+[landing],obligation=None)
        except (Refusal,OSError,ValueError,subprocess.TimeoutExpired) as e:
            result['freshness']=str(e)
    return result

def reconcile(c, selected=None):
    snapshots=[load(selected)] if selected else records()
    reconciled=0
    for snapshot in snapshots:
        if not selected and (snapshot['completed'] or snapshot['archived']):
            if snapshot.get('pending_publication') or snapshot.get('publication_error'):
                with locked():
                    r=load(snapshot['id'])
                    if r['revision']==snapshot['revision']: publish(c,r); notify(r)
                reconciled+=1
            continue
        reconciled+=1
        updates={}
        try:
            design_pending=bool(snapshot.get('accepted') and digest(human(c,snapshot))!=snapshot['accepted']['digest'])
        except (OSError,Refusal,ValueError):
            design_pending=True
        for rid,row in snapshot['rows'].items():
            if row.get('retired'): continue
            try: updates[rid]=observe(row,not design_pending)
            except (OSError,Refusal,ValueError,subprocess.TimeoutExpired) as e: updates[rid]={'freshness':str(e)}
        with locked():
            r=load(snapshot['id'])
            if r['revision']!=snapshot['revision']: continue
            for rid,update in updates.items(): r['rows'][rid].update(update)
            if r.get('completed') and any(v['status']!='Done' for v in r['rows'].values() if not v.get('retired')):
                r.setdefault('completion_history',[]).append(r['completed'])
                r['completed']=False
            try: r['design_pending']=bool(r.get('accepted') and digest(human(c,r))!=r['accepted']['digest'])
            except (OSError,Refusal,ValueError) as e: r['publication_error']=str(e)
            save(r); publish(c,r); notify(r)
    return {'reconciled':reconciled}

def configure(q):
    vault=Path(text(q['vault'])).resolve(strict=True)
    check(vault.is_dir(),'vault is not a directory')
    check(not any(p.is_relative_to(vault) for p in (DATA,STATE,CONFIG)),'private operational roots must be outside the vault')
    roots={k:str(relative(q[k])) for k in ('work','archive','generated')}
    for a,v in roots.items():
        for b,w in roots.items():
            check(a==b or not (PurePosixPath(v).is_relative_to(w) or PurePosixPath(w).is_relative_to(v)),'human and generated roots must be disjoint')
        with directory(vault/v): pass
    c={'version':1,'home':str(HOME),'data':str(DATA),'state':str(STATE),'vault':str(vault),**roots,'publisher':str(uuid.uuid4())}
    with locked():
        prior=read(CONFIG/'initiative.json',True)
        if prior:
            old=json.loads(prior); c['publisher']=old['publisher']
            pending=old.pop('owner_pending',None)
            check(old==c,'reconfiguration requires explicit migration of existing bindings')
            if pending: c['owner_pending']=pending
        root=vault/roots['generated']; owner=root/'.firstmate-owner.json'
        ownership=encode({'publisher':c['publisher'],'home':str(HOME)})
        if c.get('owner_pending'):
            check(c['owner_pending']['content']==ownership.decode(),'wrong owner receipt candidate')
            recover_exclusive(owner,c['owner_pending'])
        existing=read(owner,True)
        if existing: check(existing==ownership,'generated directory already owned')
        else:
            check(not list(root.iterdir()),'generated directory must be empty at opt-in')
            c['owner_pending']=transaction(ownership)
            put(CONFIG/'initiative.json',encode(c))
            put(owner,ownership,True,staging=c['owner_pending']['staging'])
        c.pop('owner_pending',None)
        put(CONFIG/'initiative.json',encode(c))
    return c

def draft(q):
    title=text(q['title']); identity=str(uuid.uuid4())
    return '\n'.join([f'# {title}','',f'<!-- firstmate:initiative v=1 id={identity} -->','',*sum(([f'## {h}','','Proposed: describe and approve the design.' if h=='Implementation design' else '', ''] for h in ['Objective','Scope','Current behavior','Implementation design','Important decisions','Completion criteria','Current position','Tasks','Sources']),[])])

def main(action,q):
    if action=='configure': return configure(q)
    if action=='draft': return draft(q)
    if action=='verify-provider':
        row={'repo':str(Path(q['repo']).resolve(strict=True)),'target':q['target'],'scope_revision':'capability-check','coverage':{'pr':q['pr'],'scope':'capability-check'},'attempt':{'scope':'capability-check','generation':'capability-check','metadata':{'mode':'direct-PR'}}}
        return forge_landing(row)
    if action=='list':
        if read(CONFIG/'initiative.json',True) is None: return {'configured':False,'initiatives':[]}
        config()
        return {'configured':True,'initiatives':[{k:r[k] for k in ('id','title','source')} | {'state':'archived' if r['archived'] else 'completed' if r['completed'] else 'active'} for r in records()]}
    c=config()
    if action=='capture': return capture(c,q)
    if action=='reconcile': return reconcile(c,q.get('id'))
    if action=='resolve':
        query=q.get('query','').casefold().strip(); rs=records()
        exact=[r for r in rs if query in (r['id'].casefold(),r['title'].casefold(),r.get('source','').casefold())] if query else []
        matches=exact or [r for r in rs if not query or r['title'].casefold().startswith(query)]
        check(len(matches)==1,'select one registered initiative; unbound legacy folders are neither executed nor migrated')
        return matches[0]
    if action=='show': return load(q['id'])
    if action=='brief':
        r=load(q['id']); row=r['rows'][uid(q['row'])]
        check(r.get('accepted'),'approved design required')
        return {'initiative':r['id'],'row':row['id'],'design':r['accepted'],'scope':row['scope'],'scope_revision':row['scope_revision'],'instruction':'Execute only this accepted scope. Do not write the initiative vault.'}
    if action=='dispatch-check':
        for r,rid in bindings(token(q['task'])):
            check(r.get('accepted') and not r.get('completed') and not r.get('archived'),'approved active initiative required')
            check(digest(human(c,r))==r['accepted']['digest'],'human design changed; reconcile before dispatch')
            check(not r['rows'][rid].get('landing'),'completed row must be explicitly reopened before dispatch')
        return {'dispatch':'approved'}
    with locked():
        if action=='register':
            note=str(relative(q['note'])); path=Path(c['vault'])/note
            check(PurePosixPath(note).is_relative_to(c['work']),'register an active-work human note')
            data=read(path); identity=marker(data)
            check(not read(CONFIG/'backlog-backend',True) or read(CONFIG/'backlog-backend').strip()!=b'manual','automatic tracking requires structured tasks-axi, not manual backend')
            src=q.get('source','')
            if src: check(urlsplit(src).scheme=='https' and bool(urlsplit(src).hostname) and not any(x in src for x in '\r\n<>'),'invalid source URL')
            for existing in records():
                if existing['id']==identity or (src and src==existing.get('source')):
                    check(existing['id']==identity and existing['note']==note,'source or identity already registered; continue that initiative')
                    human(c,existing); return existing
            title=text(q['title'])
            stem=' '.join(re.sub(r'[\\/:*?"<>|#^\[\]]',' ',title).split()).strip('. ')[:120].rstrip('. ')
            check(stem,'initiative title needs a readable filename')
            name=stem+' - Status.md'
            check(not any(p.name.casefold()==name.casefold() for p in generated_owner(c).iterdir()) and not any(r['companion'].casefold()==name.casefold() for r in records()),'companion name already reserved; use a distinct initiative title')
            r={'version':1,'home':str(HOME),'id':identity,'title':text(q['title']),'goal':text(q['goal']),'note':note,'source':src,'revision':0,'rows':{},'accepted':None,'design_history':[],'design_pending':False,'published':None,'pending_publication':None,'publication_error':'','completed':False,'archived':False}
            r['companion']=name
            human(c,r); save(r)
        else:
            r=load(uid(q['id'])); authority=text(q.get('authority',''))
            check(not r['archived'] or action=='recover','archived initiative cannot be mutated')
            if action=='accept':
                data=human(c,r)
                accepted={'revision':text(q['revision']),'digest':digest(data),'text':data.decode(),'authority':authority}
                r['design_history'].append(accepted); r['accepted']=accepted; r['design_pending']=False
            elif action=='bind':
                check(r.get('accepted') and digest(human(c,r))==r['accepted']['digest'],'accepted current design required')
                task=token(q['task']); o=source('task',task)
                check(o['result']=='found','bind an existing exact structured backlog item')
                check(not bindings(task),'work item already has an initiative row')
                repo=Path(text(q['repo'])).resolve(strict=True)
                check(command(['git','-C',repo,'rev-parse','--show-toplevel'])==str(repo),'repository root required')
                target=text(q['target']); command(['git','check-ref-format','refs/heads/'+target])
                rid=str(uuid.uuid4()); scope=text(q['scope'])
                r['rows'][rid]={'id':rid,'task':task,'repo':str(repo),'target':target,'scope':scope,'scope_revision':digest(scope),'authority':authority,'name':text(q['name']),'explanation':text(q['explanation']),'order':len(r['rows']),'status':'Planned','started':False,'freshness':'','attempt':None,'attempt_history':[],'landing':None,'landing_history':[],'obligation':None,'retired':False}
            elif action=='position':
                r['position']=text(q['text']); r['position_authority']=authority
                check(len(r['position'])<=1200,'current state must be a concise paragraph')
                if 'next' in q: r['next']=text(q['next'])
                for key in ('blockers','decisions'):
                    if key in q:
                        check(isinstance(q[key],list) and len(q[key])<=3,'at most three concise '+key+' allowed')
                        r[key]=[text(x) for x in q[key]]
                        check(all(len(x)<=300 for x in r[key]),'summarize '+key+' in plain language')
            elif action in ('edit-row','retire','reopen','cover'):
                row=r['rows'][uid(q['row'])]
                if action=='edit-row':
                    for key in ('name','explanation'):
                        if key in q: row[key]=text(q[key])
                    if 'order' in q: check(isinstance(q['order'],int),'integer order required'); row['order']=q['order']
                elif action=='retire': row['retired']=True
                elif action=='reopen':
                    if row.get('attempt'): row.setdefault('retired_generations',[]).append(row['attempt']['generation'])
                    if row.get('local_intent'): row.setdefault('local_intent_history',[]).append(row['local_intent'])
                    scope=text(q['scope']); row.update(scope=scope,scope_revision=str(uuid.uuid4()),landing=None,attempt=None,coverage=None,obligation=None,local_intent=None,delivery_verified=None,started=False,status='Planned',retired=False)
                    r['completed']=False
                else:
                    pr=source('pr',q['pr']); row['coverage']={'pr':pr['url'],'scope':row['scope_revision'],'authority':authority}
                row['authority']=authority
            elif action=='complete':
                check(all(v['retired'] or v['status']=='Done' for v in r['rows'].values()),'in-scope rows have not all landed')
                check(r.get('accepted') and digest(human(c,r))==r['accepted']['digest'],'current design must be accepted')
                check(not r['publication_error'] and not any(v.get('freshness') or v.get('obligation') for v in r['rows'].values() if not v['retired']),'reconciliation remains outstanding')
                r['completed']={'criteria':text(q['criteria']),'disposition':text(q['disposition']),'authority':authority}
            elif action=='archive':
                check(r['completed'],'completion criteria must be accepted before archive')
                check(digest(human(c,r))==r['accepted']['digest'],'archive source changed after accepted completion')
                check(PurePosixPath(r['note']).is_relative_to(c['archive']),'move the human note into the archive in your editor first')
                r['archived']={'authority':authority}
            elif action=='recover':
                path=companion(c,r)
                pending=r.get('pending_publication')
                if pending and pending.get('staging'): recover_exclusive(path,pending)
                current=read(path,True)
                if current is not None: r.setdefault('conflicts',{})[digest(current)]=current.decode('utf-8',errors='replace')
                r['recovery_pending']={'authority':authority,'original':r.get('published_content'),'candidate':pending,'conflicts':copy.deepcopy(r.get('conflicts',{}))}
                r['published']=digest(current) if current is not None else None
                r['recovery_authority']=authority
            else: raise Refusal('unknown initiative command')
            save(r)
        publish(c,r); notify(r)
        return {'id':r['id'],'row':rid} if action=='bind' else r

if __name__=='__main__':
    try:
        action=sys.argv[1]
        if action in ('capture-task','check-task'):
            q={'task':sys.argv[2]}
            if action=='check-task': action='dispatch-check'
            else:
                action='capture'; q['event']=sys.argv[3]
                if q['event']=='merge': q['pr']=sys.argv[4]
                if q['event']=='local-retry' and len(sys.argv)>4: q['tip']=sys.argv[4]
                if q['event'] in ('local-intent','local'): q.update(before=sys.argv[4],after=sys.argv[5],target=sys.argv[6])
        else:
            q=json.loads(sys.stdin.read() if len(sys.argv)>2 and sys.argv[2]=='-' else Path(sys.argv[2]).read_text()) if len(sys.argv)>2 else {}
        check(isinstance(q,dict),'JSON request object required')
        result=main(action,q)
        print(result if isinstance(result,str) else json.dumps(result,ensure_ascii=False))
    except (Refusal,OSError,ValueError,KeyError,IndexError,subprocess.TimeoutExpired) as e:
        print('fm-initiative: '+str(e),file=sys.stderr); sys.exit(2)
