#!/usr/bin/env python3
"""Persistent checks for candidate approval."""

from pathlib import Path
import sys

# -I excludes the script directory; only these local check helpers are added.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_support import RuntimeFixture, run_check


class CandidateApprovalChecks(RuntimeFixture):
    """candidate approval checks."""

    def test_cannot_save_before_batch_approval(self):
        run = self.begin()
        self.assert_error("INVALID_STATE", self.command, "save-topic", run, self.detail())
        self.command("propose", run, self.proposal)
        self.assert_error("INVALID_STATE", self.command, "save-topic", run, self.detail())


    def test_approval_requires_current_digest_and_known_unique_ids(self):
        run = self.begin()
        proposed = self.command("propose", run, self.proposal)
        value = {"proposal_digest": proposed["proposal_digest"], "selected_ids": ["ownership"],
                 "user_response": "소유권만"}
        self.assert_error("APPROVAL_MISMATCH", self.command, "approve", run, dict(value, proposal_digest="old"))
        self.assert_error("APPROVAL_MISMATCH", self.command, "approve", run, dict(value, selected_ids=["unknown"]))
        self.assert_error("INVALID_PAYLOAD", self.command, "approve", run, dict(value, selected_ids=["ownership"] * 2))
        self.command("approve", run, value)
        self.assert_error("INVALID_STATE", self.command, "propose", run, self.proposal)


    def test_empty_candidates_and_all_excluded_create_no_output(self):
        run = self.begin()
        self.assertEqual("empty", self.command("propose", run, {"topics": []})["phase"])
        run = self.approved(ids=[])
        self.assertEqual("excluded", self.command("status", run)["phase"])
        self.assertFalse((self.repo / "knowledge-candidate").exists())


    def test_topic_contains_exact_approved_candidates_only(self):
        run = self.approved()
        value = self.detail()
        value["concepts"][0]["candidate_id"] = "matching"
        self.assert_error("APPROVAL_MISMATCH", self.command, "save-topic", run, value)
        value["concepts"] = []
        self.assert_error("INVALID_PAYLOAD", self.command, "save-topic", run, value)
        self.command("save-topic", run, self.detail())
        self.command("save-topic", run, self.detail("postgresql"))
        result = self.command("status", run)
        self.assertEqual("completed", result["phase"])
        self.assertEqual(2, len(result["saved"]))



def main(argv=None):
    return run_check("candidate-approval", CandidateApprovalChecks, argv)


if __name__ == "__main__":
    sys.exit(main())
