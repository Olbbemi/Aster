#!/usr/bin/env python3
"""Persistent checks for topic storage."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
from unittest.mock import patch

# -I excludes the script directory; only these local check helpers are added.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_support import FixedClock, RuntimeFixture, run_check, run_process


class TopicStorageChecks(RuntimeFixture):
    """topic storage checks."""

    def test_output_links_fail_without_writing_to_link_target(self):
        run = self.approved(ids=["ownership"])
        (self.repo / "knowledge-candidate").symlink_to(self.source, target_is_directory=True)
        self.assert_error("INVALID_OUTPUT_ROOT", self.command, "save-topic", run, self.detail())
        self.assertEqual({"mixed.md", "detail.rs"}, {p.name for p in self.source.iterdir()})


    def test_date_directory_link_is_rejected(self):
        run = self.approved(ids=["ownership"])
        parent = self.repo / "knowledge-candidate"
        parent.mkdir()
        (parent / "2026-10-11").symlink_to(self.source, target_is_directory=True)
        with patch.object(self.storage, "datetime", FixedClock):
            self.assert_error("INVALID_OUTPUT_ROOT", self.command, "save-topic", run, self.detail())
        self.assertFalse(list(self.source.glob("knowledge-*.md")))


    def test_same_run_lock_blocks_concurrent_command(self):
        run = self.approved(ids=["ownership"])
        with self.state_store.locked_run(str(run)):
            result = run_process([sys.executable, "-B", str(self.scripts / "run_status.py"), "--run", str(run)],
                                    capture_output=True, text=True)
        self.assertEqual(2, result.returncode)
        self.assertEqual("INVALID_STATE", json.loads(result.stdout)["error"]["code"])


    def test_timestamp_collision_and_repeat_save_preserve_existing_file(self):
        first = self.approved(ids=["ownership"])
        second = self.approved(ids=["ownership"])
        with patch.object(self.storage, "datetime", FixedClock):
            a = self.command("save-topic", first, self.detail())
            b = self.command("save-topic", second, self.detail())
        self.assertEqual("2026-10-11", Path(a["path"]).parent.name)
        self.assertEqual("knowledge-20261011-235959-rust.md", Path(a["path"]).name)
        self.assertEqual("knowledge-20261011-235959-rust-2.md", Path(b["path"]).name)
        original = Path(a["path"]).read_bytes()
        repeated = self.command("save-topic", first, self.detail())
        self.assertTrue(repeated["reused"])
        self.assertEqual(a["path"], repeated["path"])
        modified = self.detail()
        modified["concepts"][0]["explanation"] = "다른 설명"
        self.assert_error("TOPIC_CONFLICT", self.command, "save-topic", first, modified)
        self.assertEqual(original, Path(a["path"]).read_bytes())


    def test_independent_concurrent_runs_never_overwrite(self):
        runs = [self.approved(ids=["ownership"]) for _ in range(4)]
        # Each process receives its own immutable control file.
        controls = []
        for index in range(4):
            path = self.root / f"detail-{index}.json"
            path.write_text(json.dumps(self.detail(), ensure_ascii=False))
            controls.append(path)
        def invoke(pair):
            run, control = pair
            return run_process([sys.executable, "-B", str(self.scripts / "save_topic.py"), "--run", str(run),
                                   "--input", str(control)], capture_output=True, text=True)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(invoke, zip(runs, controls)))
        paths = []
        for result in results:
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            paths.append(json.loads(result.stdout)["data"]["path"])
        self.assertEqual(4, len(set(paths)))
        self.assertEqual(4, len(list((self.repo / "knowledge-candidate").rglob("*.md"))))


    def test_partial_failure_keeps_saved_and_reports_failed_topic(self):
        run = self.approved()
        saved = self.command("save-topic", run, self.detail())
        value = self.detail("postgresql")
        value["concepts"][0]["usage"] = ""
        self.assert_error("INVALID_PAYLOAD", self.command, "save-topic", run, value)
        result = self.command("status", run)
        self.assertTrue(Path(saved["path"]).is_file())
        self.assertEqual(["rust"], [item["topic_id"] for item in result["saved"]])
        self.assertEqual(["postgresql"], [item["topic_id"] for item in result["failed"]])


    def test_interrupt_after_publish_recovers_receipt_without_duplicate(self):
        run = self.approved(ids=["ownership"])
        actual = self.storage.os.link
        def publish_then_interrupt(*args, **kwargs):
            actual(*args, **kwargs)
            raise OSError("receipt interruption")
        with patch.object(self.storage.os, "link", side_effect=publish_then_interrupt):
            with self.assertRaises(OSError):
                self.command("save-topic", run, self.detail())
        result = self.command("status", run)
        self.assertEqual("completed", result["phase"])
        self.assertEqual(1, len(result["saved"]))
        self.assertTrue(self.command("save-topic", run, self.detail())["reused"])


    def test_interrupt_before_publish_is_failed_not_saved(self):
        run = self.approved(ids=["ownership"])
        with patch.object(self.storage.os, "link", side_effect=OSError("publish failed")):
            with self.assertRaises(OSError):
                self.command("save-topic", run, self.detail())
        result = self.command("status", run)
        self.assertEqual([], result["saved"])
        self.assertEqual(1, len(result["failed"]))
        self.assertFalse(list((self.repo / "knowledge-candidate").rglob("*.md")))
        self.command("save-topic", run, self.detail())


    def test_interrupted_output_mismatch_requires_recovery(self):
        run = self.approved(ids=["ownership"])
        actual = self.storage.os.link
        def publish_then_interrupt(*args, **kwargs):
            actual(*args, **kwargs)
            raise OSError("interrupted")
        with patch.object(self.storage.os, "link", side_effect=publish_then_interrupt):
            with self.assertRaises(OSError):
                self.command("save-topic", run, self.detail())
        path = next((self.repo / "knowledge-candidate").rglob("*.md"))
        path.write_text("modified")
        result = self.command("status", run)
        self.assertEqual("RECOVERY_REQUIRED", result["recovery_required"]["code"])
        self.assertEqual([], result["saved"])
        self.assert_error("RECOVERY_REQUIRED", self.command, "save-topic", run, self.detail())
        self.assertEqual("modified", path.read_text())



def main(argv=None):
    return run_check("topic-storage", TopicStorageChecks, argv)


if __name__ == "__main__":
    sys.exit(main())
