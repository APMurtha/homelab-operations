import copy
import json
import multiprocessing
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from github import Denied, OWNER, REPO, REPO_ID, Unavailable
from single_submission import DOMAIN, LABEL, MARKER, PREFIX, Inbox, InboxStore, canonical, poll
from submit_operations import submit
from single_submission import enabled_tick

VECTOR=json.loads(Path(__file__).with_name('fixtures').joinpath('operations-signature.json').read_text())
START=VECTOR['grant']['issued']
STAMP='2027-01-15T08:00:00Z'
COMMENT=7112000001


class GitHubFixture(Inbox):
    def __init__(self):
        super().__init__(VECTOR['grant']['task']['host_key'],copy.deepcopy(VECTOR['policy']))
        self.actor=OWNER
        self.repository=REPO_ID
        self.base_sha=VECTOR['grant']['task']['base']
        self.issue=dict(number=8,id=self.p['issue_id'],body=MARKER,user={'id':OWNER},state='open',
                        labels=[dict(name=LABEL,id=self.p['label_id'])],node_id='issue-node')
        self.events=[dict(id=self.p['event'],actor={'id':OWNER},event='labeled',label={'name':LABEL},
                          created_at='2027-01-14T00:00:00Z')]
        self.comments=[]
        self.node_patch={}
        self.anchor_patch={}
        self.errors=False
        self.posts=0
        self.interrupt=False

    def append(self, body):
        n=COMMENT+len(self.comments)
        c=dict(user=dict(id=OWNER),id=n,created_at=STAMP,updated_at=STAMP,node_id=str(n),
               issue_url=f'https://api.github.com/repos/{REPO}/issues/8',body=body)
        self.comments.append(c)
        return c

    def api(self,path,method='GET',data=None):
        if path=='user':
            return {'id':self.actor}
        if path=='repos/'+REPO:
            return dict(id=self.repository,owner=dict(id=OWNER),full_name=REPO,default_branch='main')
        assert path=='graphql' and method=='POST'
        node=data['variables']['id']
        if node=='issue-node':
            result=dict(fullDatabaseId=str(self.issue['id']),body=self.issue['body'],lastEditedAt=None,
                        repository=dict(databaseId=REPO_ID)) | self.anchor_patch
        else:
            c=next(c for c in self.comments if c['node_id']==node)
            result=dict(__typename='IssueComment',id=node,fullDatabaseId=str(c['id']),body=c['body'],
                        lastEditedAt=None,createdAt=c['created_at'],author=dict(databaseId=c['user']['id']),
                        issue=dict(fullDatabaseId=str(self.p['issue_id']),number=8,repository=dict(databaseId=REPO_ID)))
            result.update(self.node_patch)
        response={'data':{'node':result}}
        if self.errors:
            response['errors']=[{}]
        return response

    def get(self,path,method='GET',data=None):
        if path=='issues/8':
            return self.issue
        if path.startswith('issues/8/events?'):
            return self.events
        if path.startswith('issues/8/comments?'):
            return self.comments
        if path.startswith('issues/comments/'):
            n=int(path.rsplit('/',1)[1])
            for c in self.comments:
                if c['id']==n:
                    return c
            raise Unavailable('missing-comment')
        if path=='git/ref/heads/main':
            return dict(object=dict(sha=self.base_sha))
        assert (method,path)==('POST','issues/8/comments')
        self.posts+=1
        comment=self.append(data['body'])
        if self.interrupt:
            self.interrupt=False
            raise Unavailable('lost-response')
        return comment


def race_claim(path, event, queue, n):
    store=InboxStore(Path(path))
    event.wait(10)
    try:
        queue.put(store.claim(n,dict(proof=[0,0,n,VECTOR['grant']['nonce']])))
    finally:
        store.db.close()


class SingleSubmission(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.api=GitHubFixture()
        self.clock=patch('time.time',return_value=START).start()
        self.addCleanup(patch.stopall)
        self.envelope=dict(grant=copy.deepcopy(VECTOR['grant']),signature=VECTOR['signature'])
        self.calls=0

    def post(self):
        return self.api.append(PREFIX+canonical(self.envelope))

    def run_tick(self,read=None):
        def observe(d):
            self.calls+=1
            return read(d) if read else b'{"relay":"running","backend":"running"}'
        try:
            poll(self.root,self.api,observe)
        except Denied:
            pass

    def record(self,n=COMMENT):
        s=InboxStore(self.root/DOMAIN)
        try:
            return s.get(n)
        finally:
            s.db.close()

    def test_single_write_submit_and_result(self):
        sign=lambda m:VECTOR['signature']
        path=self.root/'intent'
        n=submit(self.api,self.envelope['grant']['task'],sign,path,self.envelope['grant']['nonce'])
        self.assertEqual((n,self.api.posts,path.stat().st_mode & 0o777),(COMMENT,1,0o600))
        self.assertEqual(path.read_text(),self.api.comments[0]['body'])
        with self.assertRaises(FileExistsError):
            submit(self.api,self.envelope['grant']['task'],sign,path,self.envelope['grant']['nonce'])
        self.run_tick()
        self.run_tick()
        self.assertEqual((self.calls,self.api.posts,self.record()['phase']),(1,2,'published'))
        self.assertIn('Submission comment '+str(n),self.api.comments[1]['body'])

    def test_ambiguous_submission_never_auto_retries(self):
        self.api.interrupt=True
        path=self.root/'intent'
        with self.assertRaises(Unavailable):
            submit(self.api,self.envelope['grant']['task'],lambda _:VECTOR['signature'],path,VECTOR['grant']['nonce'])
        self.assertTrue(path.exists())
        self.assertEqual(self.api.posts,1)

    def test_connector_can_submit_only_signed_bytes_in_signed_context(self):
        for field,value in [('owner_id',1),('repository','other'),('repository_id',1),('issue',9),
                            ('issue_id',121),('label_id',2),('label_event',0),('nonce','ab'*32),
                            ('digest','0'*64),('issued',START-1),('protocol','wrong')]:
            with self.subTest(field=field):
                self.api.comments.clear()
                self.envelope['grant']=VECTOR['grant'] | {field:value}
                self.post()
                self.run_tick()
                self.assertIsNone(self.record())
        self.assertEqual(self.calls,0)

    def test_rehashing_or_reserializing_tampered_scope_fails(self):
        from github import sha
        for delta in [dict(attempts=2),dict(bytes=300),dict(seconds=5),dict(expires=START+299),
                      dict(observations=['logs']),dict(base='f'*40),dict(host_key='wrong'),dict(target='other')]:
            self.api.comments.clear()
            task=VECTOR['grant']['task'] | delta
            self.envelope['grant']=VECTOR['grant'] | dict(task=task,digest=sha(canonical(task)))
            self.post()
            self.run_tick()
        self.assertEqual((self.calls,self.api.posts),(0,0))

    def test_edited_same_second_and_provider_mismatch(self):
        self.post()
        for delta in [dict(lastEditedAt=STAMP),dict(body='changed'),dict(author=dict(databaseId=1)),
                      dict(id='different'),dict(fullDatabaseId='1'),dict(issue={}),dict(createdAt='other')]:
            self.api.node_patch=delta
            self.run_tick()
        self.api.node_patch={}
        self.api.anchor_patch=dict(lastEditedAt=STAMP)
        self.run_tick()
        self.api.anchor_patch={}
        self.api.errors=True
        self.run_tick()
        self.assertEqual(self.calls,0)

    def test_actor_epoch_and_base_rechecked(self):
        c=self.post()
        self.api.actor=1; self.run_tick()
        self.api.actor=OWNER;self.api.repository=1; self.run_tick()
        self.api.repository=REPO_ID
        c['user']['id']=2;self.run_tick();c['user']['id']=OWNER
        self.api.events[0]['actor']['id']=1;self.run_tick();self.api.events[0]['actor']['id']=OWNER
        self.api.events.append(self.api.events[0] | dict(event='unlabeled'))
        self.api.events.append(self.api.events[0] | dict(id=self.api.p['event']+2))
        self.run_tick()
        self.api.events=self.api.events[:1]+[dict(event='closed'),dict(event='reopened')]
        self.run_tick()
        self.api.events=self.api.events[:1]
        self.api.issue['labels'][0]['id']=2;self.run_tick()
        self.api.issue['labels'][0]['id']=self.api.p['label_id']
        self.api.base_sha='d'*40;self.run_tick()
        self.assertEqual(self.calls,0)

    def test_malformed_signature_duplicates_and_times(self):
        c=self.post()
        for body in [PREFIX+'{"grant":{},"grant":{},"signature":""}',PREFIX+'x'*4097,
                     PREFIX+canonical(self.envelope|dict(signature='forged')),
                     PREFIX+canonical(self.envelope|dict(extra=1))]:
            c['body']=body;self.run_tick()
        c['body']=PREFIX+canonical(self.envelope)
        for moment in (START-1,START+300,START+301):
            self.clock.return_value=moment
            self.run_tick()
        self.assertEqual(self.calls,0)

    def test_cancel_revokes_nonce_across_deletion_restart_and_repost(self):
        self.post()
        self.api.append('cancel '+DOMAIN+' '+VECTOR['grant']['nonce'])
        self.run_tick()
        self.api.comments.pop()
        self.post()
        self.run_tick()
        self.assertEqual((self.calls,self.api.posts),(0,0))

    def test_midflight_cancellation_and_expiry(self):
        self.post()
        def revoke(_):
            self.api.append('cancel '+DOMAIN+' '+VECTOR['grant']['nonce'])
            return b'{"relay":"running","backend":"running"}'
        self.run_tick(revoke)
        self.assertEqual((self.record()['phase'],self.api.posts),('cancelled',0))

    def test_expiry_during_read(self):
        self.post()
        def late(_):
            self.clock.return_value=START+300
            return b'{"relay":"running","backend":"running"}'
        self.run_tick(late)
        self.assertEqual((self.record()['phase'],self.api.posts),('escalated',0))

    def test_uncertain_publication_and_replayed_comment(self):
        self.post();self.post()
        self.api.interrupt=True
        self.run_tick()
        self.assertEqual(self.record()['phase'],'posting')
        self.run_tick()
        self.assertEqual((self.api.posts,self.calls,self.record()['phase']),(1,1,'published'))
        self.assertIsNone(self.record(COMMENT+1))

    def test_crash_after_read_intent_consumes_attempt(self):
        self.post()
        with self.assertRaises(SystemExit):
            self.run_tick(lambda _: (_ for _ in ()).throw(SystemExit()))
        self.run_tick()
        self.assertEqual((self.calls,self.api.posts,self.record()['phase']),(1,0,'escalated'))

    def test_two_processes_race_for_one_nonce(self):
        path=self.root/'race';store=InboxStore(path);store.db.close()
        ctx=multiprocessing.get_context('fork')
        event,queue=ctx.Event(),ctx.Queue()
        procs=[ctx.Process(target=race_claim,args=(str(path),event,queue,COMMENT+i)) for i in range(2)]
        for proc in procs:proc.start()
        event.set()
        self.assertEqual(sorted(queue.get(timeout=5) for _ in procs),[False,True])
        for proc in procs:
            proc.join(5);self.assertEqual(proc.exitcode,0)

    def test_overlapping_polls_and_foreign_cancel(self):
        self.post()
        c=self.api.append('cancel '+DOMAIN+' '+VECTOR['grant']['nonce'])
        c['user']['id']=1
        def nested(_):
            self.run_tick()
            return b'{"relay":"running","backend":"running"}'
        self.run_tick(nested)
        self.assertEqual((self.calls,self.api.posts),(1,1))

    def test_epoch_rechecked_after_durable_claim_before_read(self):
        self.post()
        original=InboxStore.claim
        def raced(store,n,t):
            ok=original(store,n,t)
            self.api.events.append(self.api.events[0] | dict(event='unlabeled'))
            return ok
        with patch.object(InboxStore,'claim',raced):
            self.run_tick()
        self.assertEqual((self.calls,self.api.posts,self.record()['phase']),(0,0,'cancelled'))

    def test_local_pin_rotation_during_read_blocks_report(self):
        self.post()
        def rotate(_):
            self.api.read_policy=lambda:self.api.p | dict(event=900)
            return b'{"relay":"running","backend":"running"}'
        self.run_tick(rotate)
        self.assertEqual((self.calls,self.api.posts,self.record()['phase']),(1,0,'cancelled'))

    def test_host_pin_rotation_before_publication(self):
        self.post()
        def rotate(_):
            self.api.read_pin=lambda:'different'
            return b'{"relay":"running","backend":"running"}'
        self.run_tick(rotate)
        self.assertEqual((self.calls,self.api.posts,self.record()['last']),(1,0,'host-policy'))

    def test_deleted_original_after_claim_refuses_copy(self):
        self.post()
        def removed(_):
            self.post()
            self.api.comments.pop(0)
            return b'{"relay":"running","backend":"running"}'
        self.run_tick(removed)
        self.run_tick()
        self.assertEqual((self.calls,self.api.posts),(1,0))

    def test_nonce_and_claim_roll_back_together(self):
        store=InboxStore(self.root/'atomic')
        self.addCleanup(store.db.close)
        store.db.execute("CREATE TRIGGER broken BEFORE INSERT ON receipts BEGIN SELECT RAISE(ABORT,'fault'); END")
        t=dict(proof=[0,0,COMMENT,VECTOR['grant']['nonce']])
        self.assertFalse(store.claim(COMMENT,t))
        self.assertIsNone(store.get(COMMENT))
        self.assertFalse(store.consumed(t['proof'][3]))
        store.db.execute('DROP TRIGGER broken')
        self.assertTrue(store.claim(COMMENT,t))

    def test_host_pin_and_provider_budget(self):
        api=Inbox(self.api.pin,self.api.p)
        with patch('subprocess.run') as proc:
            proc.return_value.returncode=0
            proc.return_value.stdout=b'{}'
            api.api('user')
            self.assertIn('github.com',proc.call_args.args[0])
            api.remaining=0
            with self.assertRaises(Unavailable):
                api.api('user')
            self.assertEqual(proc.call_count,1)

    def test_opt_in_and_fallback_are_independent(self):
        for operations,single,expected in [('','enabled',0),('enabled','',0),('enabled','enabled',1)]:
            with patch.dict(os.environ,{'SAMWISE_OPERATIONS_V1':operations,'SAMWISE_OPERATIONS_SINGLE':single}), \
                 patch('operations.poll') as legacy,patch('single_submission.poll') as newer,patch('os.getuid',return_value=1000):
                enabled_tick(self.root)
                self.assertEqual((legacy.call_count,newer.call_count),(0,expected))
