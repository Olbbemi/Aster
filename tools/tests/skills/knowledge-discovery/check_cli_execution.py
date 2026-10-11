#!/usr/bin/env python3
"""Persistent checks for cli execution."""

import json
from pathlib import Path
import shutil
import sys

# -I excludes the script directory; only these local check helpers are added.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_support import ENTRYPOINTS, RuntimeFixture, run_check, run_process


class CliExecutionChecks(RuntimeFixture):
    """cli execution checks."""

    def test_missing_inputs_return_json_error(self):
        for command, module in ENTRYPOINTS.items():
            with self.subTest(command=command):
                result = run_process([sys.executable, "-B", str(self.scripts / (module + ".py"))],
                                        cwd=self.source, capture_output=True, text=True, timeout=10)
                self.assertEqual(2, result.returncode, result.stderr)
                response = json.loads(result.stdout)
                self.assertFalse(response["ok"])
                self.assertIsNone(response["command"])
                self.assertEqual("MISSING_INPUT", response["error"]["code"])
                self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.repo / "knowledge-candidate").exists())


    def test_cli_reports_actual_read_error_with_exit_three(self):
        run = self.begin()
        result = run_process([sys.executable, "-B", str(self.scripts / "propose_candidates.py"), "--run", str(run),
                                 "--input", str(self.root / "missing.json")], capture_output=True, text=True)
        self.assertEqual(3, result.returncode)
        self.assertEqual("IO_ERROR", json.loads(result.stdout)["error"]["code"])


    def test_incomplete_state_is_json_error_without_traceback(self):
        run = self.begin()
        (run / "state.json").write_text('{"schema_version": 1}')
        result = run_process([sys.executable, "-B", str(self.scripts / "run_status.py"), "--run", str(run)],
                                capture_output=True, text=True)
        self.assertEqual(2, result.returncode)
        self.assertEqual("INVALID_STATE", json.loads(result.stdout)["error"]["code"])
        self.assertNotIn("Traceback", result.stderr)


    def test_cli_completes_run_from_unrelated_working_directory(self):
        def invoke(command, *args):
            result = run_process(
                [sys.executable, "-B", str(self.scripts / (ENTRYPOINTS[command] + ".py")), *args],
                cwd=self.source, capture_output=True, text=True, timeout=10)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            response = json.loads(result.stdout)
            self.assertTrue(response["ok"])
            self.assertEqual(command, response["command"])
            return response["data"]

        inspected = invoke("inspect", "--target", str(self.source), "--output-root", str(self.repo))
        self.assertEqual(str(self.repo), inspected["output_root"])
        started = invoke("start", "--input", self.control(self.request))
        run = started["run"]
        self.addCleanup(shutil.rmtree, run, True)
        read = invoke("read", "--run", run, "--file", str(self.first))
        self.assertEqual(self.first.read_text(), read["text"])
        proposed = invoke("propose", "--run", run, "--input", self.control(self.proposal))
        approval = {"proposal_digest": proposed["proposal_digest"],
                    "selected_ids": ["ownership"], "user_response": "소유권만"}
        approved = invoke("approve", "--run", run, "--input", self.control(approval))
        self.assertEqual(["ownership"], approved["selected_ids"])
        saved = invoke("save-topic", "--run", run, "--input", self.control(self.detail()))
        result = invoke("status", "--run", run)
        self.assertEqual("completed", result["phase"])
        self.assertEqual([{"topic_id": "rust", "path": saved["path"]}], result["saved"])
        self.assertEqual([], result["failed"])
        self.assertEqual([], result["pending"])
        self.assertIsNone(result["recovery_required"])
        self.assertTrue(Path(saved["path"]).is_file())



def main(argv=None):
    return run_check("cli-execution", CliExecutionChecks, argv)


if __name__ == "__main__":
    sys.exit(main())
