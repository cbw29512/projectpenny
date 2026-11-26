"""Shared memory lifecycle helpers on the migration-complete test database."""
from uuid import uuid4

from database_fixture import DSN, DatabaseFixture
from penny.memory.intake import submit_review
from penny.memory.review import approve
from penny.scheduler.outcomes import complete

CONTENT = "Measure outcomes first."


class ReviewFixture(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer = uuid4()

    def candidate(self, key="a", content=CONTENT):
        import json
        receipt = submit_review(self.store,key,"Observed result")
        claim = self.store.claim()
        self.assertTrue(complete(self.dsn,claim.task_id,claim.fence,success=True,
                                 result=json.dumps({"kind":"lesson","content":content})))
        return receipt.task_id

    def approve(self, source, content=CONTENT, **kwargs):
        args = dict(reviewer_id=self.reviewer,review_ref="review/1",
                    evidence=b"independently reviewed material",expected_content=content,
                    retention_seconds=3600)
        args.update(kwargs)
        return approve(self.dsn,source,**args)

    def claim(self, member=None):
        from penny.memory.task import submit_informed
        if member is None:
            submit_informed(self.store,uuid4().hex,"Measure outcomes")
        else:
            self.store.submit(member,str(uuid4()),"Measure outcomes")
        return self.store.claim()

