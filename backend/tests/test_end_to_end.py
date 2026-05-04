"""The whole loop through the HTTP seam, with only the LLM faked."""

import json
from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models import State
from app.worker import claim, process_job
from tests.conftest import Account
from tests.test_stream import data, events, stream
from tests.test_upload import make_project, upload

HANDBOOK = b"""# Support

## Escalation

Page the on-call engineer after fifteen minutes without an acknowledgement.
"""


def test_upload_to_cited_answer(
    client: TestClient, signup: Callable[..., Account], fakellm: list[str]
) -> None:
    account = signup()
    projectid = make_project(client, account)
    documentid = upload(client, account, projectid, "support.md", HANDBOOK).json()["id"]

    jobid = claim()
    assert jobid is not None
    process_job(jobid)

    status = client.get(f"/documents/{documentid}/status", headers=account.headers).json()
    assert status["state"] == State.indexed

    body = stream(client, account, projectid, "When do we page the on-call engineer?")
    assert events(body)[0] == "message_start"
    assert events(body)[-1] == "message_end"

    cited = json.loads(data(body, "citation")[0])
    assert cited["document_id"] == documentid
    assert cited["document_name"] == "support.md"
    assert "fifteen minutes" in cited["snippet"]
