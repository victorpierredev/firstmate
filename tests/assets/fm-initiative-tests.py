import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import uuid

ROOT, TEMP = map(Path, sys.argv[1:3])
sys.argv = [sys.argv[0]]

class Initiative(unittest.TestCase):
    def setUp(self):
        self.root = TEMP / self._testMethodName
        self.home = self.root / 'home'
        self.vault = self.root / 'vault'
        self.code = self.root / 'code' / 'bin'
        self.fake = self.root / 'fakebin'
        for p in [self.home/'data', self.home/'state', self.home/'config', self.vault/'Work', self.vault/'Archive', self.vault/'Generated', self.code, self.fake]:
            p.mkdir(parents=True)
        for p in (ROOT/'bin').iterdir():
            if p.is_file():
                (self.code/p.name).symlink_to(p)
        self.env = dict(os.environ, FM_HOME=str(self.home), PATH=str(self.fake)+os.pathsep+os.environ['PATH'])
        for k in ['FM_TASK_ID', 'FM_ROOT_OVERRIDE', 'FM_STATE_OVERRIDE', 'FM_DATA_OVERRIDE', 'FM_CONFIG_OVERRIDE', 'FM_SUPERVISION_ACTOR', 'TASKS_AXI_FILE', 'TASKS_AXI_BACKEND']:
            self.env.pop(k, None)
        self.env['FM_GATE_REFUSE_BYPASS'] = '1'
        self.rows = self.root/'rows.json'
        self.rows.write_text(json.dumps({'task-1':{'state':'queued','held':'no','blocked':'no'}}))
        self.env['INITIATIVE_FIXTURE_ROWS'] = str(self.rows)
        self.tool('tasks-axi', '''import json,os,sys
args=sys.argv[1:]
if args==['--version']: print('tasks-axi 0.9.0')
elif '--help' in args: print('--archive-body [<id>...]')
elif args[0]=='show':
 rows=json.load(open(os.environ['INITIATIVE_FIXTURE_ROWS']))
 if args[1] not in rows: print('code: NOT_FOUND'); sys.exit(1)
 print('task:'); print('  id: '+args[1])
 for k,v in rows[args[1]].items(): print('  '+k+': '+v)
else: sys.exit(2)
''')
        (self.home/'.tasks.toml').write_text('backend = "markdown"\n')
        (self.home/'data/backlog.md').write_text('## In flight\n\n## Queued\n\n## Done\n')
        self.iid = str(uuid.uuid4())
        self.note = self.vault/'Work/Example.md'
        self.original = ('---\r\ntitle: Éxample\r\n---\r\n<!-- firstmate:initiative v=1 id='+self.iid+' -->\r\n\r\n# Human words\r\n`code|span` and escaped \\| pipe.\r\n\r\n```md\r\n<!-- firstmate:initiative v=9 id=example -->\r\n```\r\n').encode()
        self.note.write_bytes(self.original)
        self.repo = self.root/'repo'
        self.repo.mkdir()
        self.git('init','-q','-b','main')
        self.git('config','user.email','test@example.test')
        self.git('config','user.name','Test')
        (self.repo/'file').write_text('initial')
        self.git('add','file'); self.git('commit','-qm','initial')
        self.before=self.git('rev-parse','HEAD')

    def tool(self, name, code):
        p=self.fake/name
        p.write_text('#!/usr/bin/env python3\n'+code); p.chmod(0o755)

    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.repo),*args],env=self.env,text=True).strip()

    def call(self, action, request=None, good=True, env=None):
        p=self.root/'request.json'; p.write_text(json.dumps(request or {}))
        r=subprocess.run(['bash',str(self.code/'fm-initiative.sh'),action,str(p)],env=env or self.env,text=True,capture_output=True)
        if good: self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        else: self.assertNotEqual(r.returncode,0,r.stdout+r.stderr)
        return json.loads(r.stdout) if good and r.stdout.strip() else r

    def configure(self):
        return self.call('configure',dict(vault=str(self.vault),work='Work',archive='Archive',generated='Generated'))

    def register(self):
        self.configure()
        return self.call('register',dict(title='Example',goal='Make account imports reliable for support teams.',note='Work/Example.md',source='https://example.test/ticket/1'))

    def bind(self):
        self.register()
        self.call('accept',dict(id=self.iid,revision='Accepted design',authority='explicit test approval'))
        return self.call('bind',dict(id=self.iid,task='task-1',repo=str(self.repo),target='main',name='Build | feature',explanation='Handle `x|y` safely',scope='Implement the accepted feature.',authority='accepted breakdown'))['row']

    def record(self):
        return self.call('show',dict(id=self.iid))

    def test_configure_register_and_human_bytes(self):
        self.register()
        r=self.record()
        self.assertEqual(r['id'],self.iid)
        self.assertEqual(self.note.read_bytes(),self.original)
        self.assertTrue((self.vault/'Generated'/f'{self.iid}.md').is_file())
        self.call('reconcile',{})
        self.assertEqual(self.note.read_bytes(),self.original)

    def test_roots_must_be_disjoint(self):
        self.call('configure',dict(vault=str(self.vault),work='Work',archive='Archive',generated='Work/Generated'),False)
        self.assertEqual(self.note.read_bytes(),self.original)

    def test_registration_rejects_traversal_symlinks_and_hardlinks(self):
        self.configure()
        for name in ['../outside.md','Work/../Example.md','Work/evil\n.md']:
            self.call('register',dict(title='Example',note=name),False)
        alias=self.vault/'Work/alias.md'; alias.symlink_to(self.root/'outside.md')
        self.call('register',dict(title='Example',note='Work/alias.md'),False)
        os.link(self.note,self.vault/'Work/linked.md')
        self.call('register',dict(title='Example',note='Work/Example.md'),False)
        self.assertEqual(self.note.read_bytes(),self.original)

    def test_duplicate_and_malformed_markers_refuse(self):
        self.configure()
        (self.vault/'Work/Copy.md').write_bytes(self.original)
        self.call('register',dict(title='Example',note='Work/Example.md'),False)
        (self.vault/'Work/Copy.md').unlink()
        for raw in [self.original.replace(b'v=1',b'v=2'), self.original+self.original, self.original.replace(b'firstmate:initiative',b'firstmate:initiativex',1)]:
            self.note.write_bytes(raw)
            self.call('register',dict(title='Example',note='Work/Example.md'),False)

    def test_source_deduplication_and_prefix_resolution(self):
        self.register()
        self.assertEqual(self.call('resolve',dict(query='exa'))['id'],self.iid)
        self.assertEqual(self.call('resolve',dict(query='https://example.test/ticket/1'))['id'],self.iid)
        self.call('resolve',dict(query='execute unknown'),False)
        self.call('resolve',dict(query='Work/Legacy'),False)
        self.call('register',dict(title='Example',goal='Make account imports reliable for support teams.',note='Work/Example.md',source='https://example.test/ticket/1'))

    def test_planned_blocked_resumed_and_started(self):
        row=self.bind()
        self.assertEqual(self.record()['rows'][row]['status'],'Planned')
        self.rows.write_text(json.dumps({'task-1':{'state':'queued','held':'yes','blocked':'no'}}))
        self.call('reconcile',{})
        self.assertEqual(self.record()['rows'][row]['status'],'Blocked')
        self.rows.write_text(json.dumps({'task-1':{'state':'queued','held':'no','blocked':'no'}}))
        self.call('reconcile',{})
        self.assertEqual(self.record()['rows'][row]['status'],'Planned')
        self.meta()
        self.rows.write_text(json.dumps({'task-1':{'state':'in_flight','held':'no','blocked':'no'}}))
        self.call('capture',dict(task='task-1',event='spawn'))
        self.call('reconcile',{})
        self.assertEqual(self.record()['rows'][row]['status'],'In progress')
        self.assertEqual(self.note.read_bytes(),self.original)

    def meta(self,gen='generation-1',mode='local-only'):
        (self.home/'state/task-1.meta').write_text(f'kind=ship\nspawn_gen={gen}\nproject={self.repo}\nworktree={self.repo}\nmode={mode}\nbranch=feature\n')

    def test_unapproved_changes_prevent_dispatch_only(self):
        self.bind()
        self.call('dispatch-check',dict(task='task-1'))
        changed=self.original+b'New scope\r\n'; self.note.write_bytes(changed)
        self.call('dispatch-check',dict(task='task-1'),False)
        self.call('reconcile',{})
        self.assertEqual(self.note.read_bytes(),changed)
        self.assertTrue(self.record()['design_pending'])

    def test_missing_note_and_manual_backend_refuse(self):
        self.configure()
        self.call('register',dict(title='Missing',note='Work/Missing.md'),False)
        self.assertFalse((self.vault/'Work/Missing.md').exists())
        (self.home/'config/backlog-backend').write_text('manual\n')
        self.call('register',dict(title='Example',note='Work/Example.md'),False)

    def test_local_receipt_survives_teardown_and_target_advance(self):
        row=self.bind(); self.meta()
        self.call('capture',dict(task='task-1',event='spawn'))
        (self.repo/'file').write_text('landed'); self.git('commit','-qam','landed')
        landed=self.git('rev-parse','HEAD')
        self.call('capture',dict(task='task-1',event='local',before=self.before,after=landed,target='main'))
        self.call('capture',dict(task='task-1',event='teardown'))
        (self.home/'state/task-1.meta').unlink(); self.rows.write_text('{}')
        (self.repo/'file').write_text('later'); self.git('commit','-qam','later')
        self.call('reconcile',{})
        r=self.record()['rows'][row]
        self.assertEqual(r['status'],'Done'); self.assertEqual(r['landing']['commit'],landed)
        self.assertEqual(self.note.read_bytes(),self.original)

    def test_unknown_observation_retains_verified_status(self):
        row=self.bind(); self.rows.write_text('{}')
        self.call('reconcile',{})
        self.assertEqual(self.record()['rows'][row]['status'],'Planned')
        self.assertTrue(self.record()['rows'][row]['freshness'])

    def test_generation_and_wrong_target_refuse_receipt(self):
        self.bind(); self.meta(); self.call('capture',dict(task='task-1',event='spawn'))
        self.meta('replacement')
        self.call('capture',dict(task='task-1',event='local',before=self.before,after=self.before,target='main'),False)
        self.meta()
        self.call('capture',dict(task='task-1',event='local',before=self.before,after=self.before,target='staging'),False)

    def test_generated_conflict_keeps_both_documents(self):
        self.register()
        generated=self.vault/'Generated'/f'{self.iid}.md'
        changed=generated.read_bytes()+b'Unexpected human edit\n'; generated.write_bytes(changed)
        self.call('position',dict(id=self.iid,text='A material change.',authority='accepted update'))
        self.assertEqual(generated.read_bytes(),changed)
        self.assertEqual(self.note.read_bytes(),self.original)
        self.assertTrue(self.record()['publication_error'])

    def test_wrong_home_actor_and_worker_refuse(self):
        self.register()
        env=dict(self.env,FM_SUPERVISION_ACTOR='branch')
        self.call('position',dict(id=self.iid,text='bad',authority='bad'),False,env)
        env=dict(self.env,FM_TASK_ID='worker')
        self.call('position',dict(id=self.iid,text='bad',authority='bad'),False,env)
        cfg=self.home/'config/initiative.json'; data=json.loads(cfg.read_text()); data['home']=str(self.root/'other'); cfg.write_text(json.dumps(data))
        self.call('reconcile',{},False)
        self.assertEqual(self.note.read_bytes(),self.original)

    def test_move_and_archive_are_read_only(self):
        self.register()
        self.call('complete',dict(id=self.iid,authority='accepted',criteria='met',disposition='no remaining calls'),False)
        self.call('accept',dict(id=self.iid,revision='Accepted',authority='explicit approval'))
        moved=self.vault/'Work/Renamed.md'; self.note.rename(moved)
        self.call('reconcile',{})
        self.assertEqual(self.record()['note'],'Work/Renamed.md')
        self.assertEqual(moved.read_bytes(),self.original)
        self.call('complete',dict(id=self.iid,authority='accepted',criteria='met',disposition='no remaining calls'))
        moved.rename(self.vault/'Archive/Example.md')
        self.call('archive',dict(id=self.iid,authority='archive accepted'))
        self.assertTrue(self.record()['archived'])
        self.assertEqual((self.vault/'Archive/Example.md').read_bytes(),self.original)

    def test_wake_ack_automatically_reconciles(self):
        row=self.bind(); self.meta()
        self.rows.write_text(json.dumps({'task-1':{'state':'in_flight','held':'no','blocked':'no'}}))
        subprocess.run(['bash','-c','. "$1/fm-wake-lib.sh"; fm_wake_append check test "check: fixture"','_',str(self.code)],env=self.env,check=True)
        presented=subprocess.run(['bash',str(self.code/'fm-wake-drain.sh')],env=self.env,capture_output=True,text=True)
        match=re.search(r'--ack-through (\d+) --recovery-generation ([A-Za-z0-9._-]+)',presented.stderr)
        self.assertIsNotNone(match,presented.stdout+presented.stderr)
        r=subprocess.run(['bash',str(self.code/'fm-wake-drain.sh'),'--ack-through',match[1],'--recovery-generation',match[2]],env=self.env,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(self.record()['rows'][row]['status'],'In progress')
        self.assertEqual(self.note.read_bytes(),self.original)

    def test_scope_history_reopen_retire_and_wording(self):
        row=self.bind(); self.meta(); self.call('capture',dict(task='task-1',event='spawn'))
        (self.repo/'file').write_text('landed'); self.git('commit','-qam','landed')
        landed=self.git('rev-parse','HEAD')
        self.call('capture',dict(task='task-1',event='local',before=self.before,after=landed,target='main'))
        self.call('reconcile',{})
        self.call('edit-row',dict(id=self.iid,row=row,name='Renamed',explanation='Changed wording',order=9,authority='cosmetic approval'))
        self.assertEqual(self.record()['rows'][row]['landing']['commit'],landed)
        self.call('reopen',dict(id=self.iid,row=row,scope='Explicitly reopened incomplete scope',authority='approved reopening'))
        r=self.record()['rows'][row]
        self.assertEqual(r['status'],'Planned'); self.assertIsNone(r['landing']); self.assertEqual(len(r['landing_history']),1)
        self.call('retire',dict(id=self.iid,row=row,authority='approved removal'))
        self.assertTrue(self.record()['rows'][row]['retired'])
        self.assertNotIn('Renamed',(self.vault/'Generated'/f'{self.iid}.md').read_text())

    def forge(self, merged=True, target='main', mode='direct-PR'):
        row=self.bind(); self.meta(mode=mode)
        self.git('remote','add','origin','https://github.com/example/repo.git')
        self.call('capture',dict(task='task-1',event='spawn'))
        pr='https://github.com/example/repo/pull/7'
        self.call('cover',dict(id=self.iid,row=row,pr=pr,authority='this delivery covers the accepted scope'))
        self.rows.write_text(json.dumps({'task-1':{'state':'in_flight','held':'no','blocked':'no'}}))
        (self.repo/'file').write_text('final integrated change'); self.git('commit','-qam','landed')
        sha=self.git('rev-parse','HEAD')
        payload={'html_url':pr,'merged':merged,'merge_commit_sha':sha,'base':{'ref':target,'repo':{'full_name':'example/repo'}},'head':{'sha':'a'*40}}
        self.tool('gh-axi', 'import base64,json,sys\ndef emit(x): print("api_response:\\n  body: "+base64.b64encode(json.dumps(x).encode()).decode()+"\\n  truncated: false")\np='+repr(payload)+"\nurl=sys.argv[2]\nif '/pulls/' in url: emit(p)\nelif '/compare/' in url: emit({'status':'ahead','merge_base_commit':{'sha':p['merge_commit_sha']}})\nelif '/git/commits/' in url: emit({'sha':p['merge_commit_sha']})\nelse: sys.exit(2)\n")
        self.call('capture',dict(task='task-1',event='merge',pr=pr))
        return row,sha

    def test_forge_uses_landed_object_not_head(self):
        row,sha=self.forge()
        self.call('reconcile',{})
        r=self.record()['rows'][row]
        self.assertEqual(r['status'],'Done'); self.assertEqual(r['landing']['commit'],sha)
        self.assertNotEqual(r['landing']['commit'],'a'*40)
        self.call('capture',dict(task='task-1',event='teardown'))
        (self.home/'state/task-1.meta').unlink(); self.rows.write_text('{}')
        self.call('reconcile',{})
        self.assertEqual(self.record()['rows'][row]['status'],'Done')

    def test_wrong_target_never_completes(self):
        row,_=self.forge(target='staging')
        self.call('reconcile',{})
        self.assertNotEqual(self.record()['rows'][row]['status'],'Done')
        self.assertIsNone(self.record()['rows'][row]['landing'])

    def test_unmerged_green_pr_and_unproven_delivery_never_complete(self):
        row,_=self.forge(merged=False)
        self.call('reconcile',{})
        self.assertNotEqual(self.record()['rows'][row]['status'],'Done')
        self.assertIsNone(self.record()['rows'][row]['landing'])

    def test_rewritten_landing_withholds_commit(self):
        row=self.bind(); self.meta(); self.call('capture',dict(task='task-1',event='spawn'))
        (self.repo/'file').write_text('landed'); self.git('commit','-qam','landed')
        sha=self.git('rev-parse','HEAD')
        self.call('capture',dict(task='task-1',event='local',before=self.before,after=sha,target='main'))
        self.call('reconcile',{})
        self.call('complete',dict(id=self.iid,authority='completed scope accepted',criteria='criteria met',disposition='no remaining calls'))
        self.git('reset','--hard',self.before)
        self.call('reconcile',{})
        self.assertFalse(self.record()['completed'])
        self.assertEqual(self.record()['rows'][row]['status'],'Blocked')
        self.assertNotIn(sha[:12],(self.vault/'Generated'/f'{self.iid}.md').read_text())
        self.assertEqual(self.record()['rows'][row]['landing']['commit'],sha)

    def test_render_is_useful_concise_and_deterministic(self):
        self.bind()
        self.call('position',dict(id=self.iid,text='The design is approved and implementation can begin.',next='Start the account import.',blockers=[],decisions=[],authority='accepted summary'))
        p=self.vault/'Generated'/f'{self.iid}.md'; first=p.read_bytes()
        rendered=first.decode()
        self.assertIn('Make account imports reliable for support teams.',rendered)
        self.assertIn('Start the account import.',rendered)
        self.assertIn('[Initiative plan]',rendered)
        self.assertLess(rendered.index('## Goal'),rendered.index('## Current state'))
        self.assertLess(rendered.index('## Current state'),rendered.index('## Completed work'))
        self.assertLess(rendered.index('## Completed work'),rendered.index('## Next action'))
        self.assertNotIn('## Blockers',rendered)
        visible=re.sub(r'<!--.*?-->','',rendered)
        for value in [str(self.home),'spawn_gen','generation-1','worktree','endpoint','no-mistakes','task-1']:
            self.assertNotIn(value,visible)
        self.assertLess(len(rendered),2200)
        self.call('reconcile',{})
        self.assertEqual(first,p.read_bytes())
        self.assertEqual(self.note.read_bytes(),self.original)

    def test_unconfigured_hooks_are_inert(self):
        self.call('capture',dict(task='not-registered',event='teardown'))
        self.call('dispatch-check',dict(task='not-registered'))
        self.call('reconcile',{})
        self.assertFalse((self.home/'data/initiatives').exists())

    def test_generated_symlink_and_hardlink_never_write_human(self):
        self.register(); generated=self.vault/'Generated'/f'{self.iid}.md'
        generated.unlink(); generated.symlink_to(self.note)
        self.call('position',dict(id=self.iid,text='Changed',authority='accepted'))
        self.assertEqual(self.note.read_bytes(),self.original)
        generated.unlink(); os.link(self.note,generated)
        self.call('position',dict(id=self.iid,text='Changed again',authority='accepted'))
        self.assertEqual(self.note.read_bytes(),self.original)
        self.assertTrue(self.record()['publication_error'])

    def test_other_home_cannot_adopt_generated_root(self):
        self.register()
        other=self.root/'other'
        for d in ['config','data','state']: (other/d).mkdir(parents=True,exist_ok=True)
        env=dict(self.env,FM_HOME=str(other))
        self.call('configure',dict(vault=str(self.vault),work='Work',archive='Archive',generated='Generated'),False,env)
        self.assertEqual(self.note.read_bytes(),self.original)

    def test_offline_vault_retains_landing_before_cleanup(self):
        row=self.bind(); self.meta(); self.call('capture',dict(task='task-1',event='spawn'))
        (self.repo/'file').write_text('landed'); self.git('commit','-qam','landed')
        sha=self.git('rev-parse','HEAD')
        offline=self.root/'offline'; self.vault.rename(offline)
        self.call('capture',dict(task='task-1',event='local',before=self.before,after=sha,target='main'))
        self.call('capture',dict(task='task-1',event='teardown'))
        (self.home/'state/task-1.meta').unlink(); self.rows.write_text('{}')
        self.call('reconcile',{})
        self.assertEqual(self.record()['rows'][row]['status'],'Done')
        self.assertTrue(self.record()['publication_error'])
        offline.rename(self.vault); self.call('reconcile',{})
        self.assertFalse(self.record()['publication_error'])
        self.assertIn(sha[:12],(self.vault/'Generated'/f'{self.iid}.md').read_text())

    def test_same_generation_metadata_enrichment_is_safe(self):
        row=self.bind(); self.meta(); self.call('capture',dict(task='task-1',event='spawn'))
        p=self.home/'state/task-1.meta'; p.write_text(p.read_text()+'pr=https://github.com/example/repo/pull/7\n')
        self.call('capture',dict(task='task-1',event='teardown'))
        self.assertEqual(self.record()['rows'][row]['obligation']['attempt']['metadata']['pr'],'https://github.com/example/repo/pull/7')

    def test_unverified_no_mistakes_delivery_stays_pending(self):
        row,_=self.forge(mode='no-mistakes')
        self.call('reconcile',{})
        self.assertNotEqual(self.record()['rows'][row]['status'],'Done')
        self.assertIsNone(self.record()['rows'][row]['landing'])

    def test_recovery_keeps_conflict_evidence(self):
        self.register(); p=self.vault/'Generated'/f'{self.iid}.md'
        changed=p.read_text()+'Unexpected edit\n'; p.write_text(changed)
        self.call('reconcile',{})
        self.call('recover',dict(id=self.iid,authority='regenerate the machine-owned note'))
        self.assertNotEqual(p.read_text(),changed)
        self.assertIn(changed,self.record()['conflicts'].values())
        self.assertEqual(self.note.read_bytes(),self.original)

    def test_interrupted_publication_acknowledges_candidate_without_rewrite(self):
        self.register(); r=self.record(); old=r['published']
        self.call('position',dict(id=self.iid,text='Approved design is ready.',authority='accepted'))
        r=self.record(); p=self.vault/'Generated'/f'{self.iid}.md'; candidate=p.read_bytes(); before=p.stat().st_mtime_ns
        r['pending_publication']={'digest':hashlib.sha256(candidate).hexdigest(),'content':candidate.decode()}; r['published']=old
        record=self.home/'data/initiatives'/self.iid/'record.json'; record.write_text(json.dumps(r))
        self.call('reconcile',{})
        self.assertIsNone(self.record()['pending_publication'])
        self.assertEqual(p.stat().st_mtime_ns,before)
        self.assertEqual(self.note.read_bytes(),self.original)

    def test_two_rows_share_only_explicit_coverage(self):
        row,sha=self.forge()
        rows=json.loads(self.rows.read_text()); rows['task-2']={'state':'queued','held':'no','blocked':'no'}; self.rows.write_text(json.dumps(rows))
        second=self.call('bind',dict(id=self.iid,task='task-2',repo=str(self.repo),target='main',name='Second task',explanation='Separate accepted delivery',scope='Second accepted scope',authority='accepted'))['row']
        self.call('reconcile',{})
        self.assertEqual(self.record()['rows'][row]['status'],'Done')
        self.assertEqual(self.record()['rows'][second]['status'],'Planned')
        self.assertIsNone(self.record()['rows'][second]['landing'])

    def test_local_merge_owner_captures_exact_result(self):
        row=self.bind(); self.meta(); self.call('capture',dict(task='task-1',event='spawn'))
        self.git('checkout','-qb','fm/task-1')
        (self.repo/'file').write_text('landed by the approved merge owner'); self.git('commit','-qam','landed')
        sha=self.git('rev-parse','HEAD'); self.git('checkout','-q','main')
        r=subprocess.run(['bash',str(self.code/'fm-merge-local.sh'),'task-1'],env=self.env,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(self.git('rev-parse','HEAD'),sha)
        receipt=self.record()['rows'][row]['landing']
        self.assertEqual(receipt['before'],self.before); self.assertEqual(receipt['commit'],sha)
        self.call('reconcile',{})
        self.assertEqual(self.record()['rows'][row]['status'],'Done')
        self.assertEqual(self.note.read_bytes(),self.original)

    def test_deferred_reconciliation_keeps_captured_home_authority(self):
        self.register()
        classifier=self.code/'fm-session-lock-lib.sh'; classifier.unlink()
        classifier.write_text('fm_session_lock_foreign_owner_live() { FM_SESSION_LOCK_FOREIGN_OWNER_PID=12345; return 0; }\n')
        self.call('reconcile',{},False)
        self.call('reconcile',{},False,dict(self.env,FM_BOOTSTRAP_NETWORK_LOCK_PID='12344'))
        self.call('reconcile',{},env=dict(self.env,FM_BOOTSTRAP_NETWORK_LOCK_PID='12345'))
        self.call('position',dict(id=self.iid,text='unauthorized',authority='none'),False,dict(self.env,FM_BOOTSTRAP_NETWORK_LOCK_PID='12345'))
        self.assertEqual(self.note.read_bytes(),self.original)

    def test_reopened_scope_cannot_reuse_old_attempt(self):
        row=self.bind(); self.meta(); self.call('capture',dict(task='task-1',event='spawn'))
        previous=self.record()['rows'][row]['scope_revision']
        self.call('reopen',dict(id=self.iid,row=row,scope='Implement the accepted feature.',authority='accepted reopening'))
        self.call('reconcile',{})
        current=self.record()['rows'][row]
        self.assertEqual(current['status'],'Planned')
        self.assertNotEqual(current['scope_revision'],previous)
        self.call('capture',dict(task='task-1',event='spawn'),False)
        self.meta('generation-2')
        self.call('capture',dict(task='task-1',event='spawn'))
        self.assertEqual(self.record()['rows'][row]['attempt']['generation'],'generation-2')

if __name__=='__main__': unittest.main()
