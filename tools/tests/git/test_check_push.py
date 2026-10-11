"""Exercise skill selection and rejection through real pushes to local remotes."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


TOOLS = Path(__file__).resolve().parents[2]
SKILL = ".agents/skills/skill-lifecycle"
REGISTRATION = "tools/tests/skills/skill-lifecycle/checks.json"
VALIDATOR = "tools/tests/skills/skill-lifecycle/check_skill_lifecycle.py"
PUSH_CHECKS = TOOLS / "scripts/git/operations/check_push.py"


class PushChecksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aster-push-checks-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.remote = self.root / "remote.git"
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_TERMINAL_PROMPT="0", GIT_CEILING_DIRECTORIES=str(self.root), LC_ALL="C")
        self.git("init", "--bare", "--initial-branch=main", str(self.remote), cwd=self.root)
        self.git("init", "--initial-branch=main", str(self.repo), cwd=self.root)
        self.git("config", "user.name", "Push Check Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("remote", "add", "origin", str(self.remote))
        for path in ("scripts/git/pre-push", "scripts/git/operations/check_push.py",
                     "scripts/git/operations/check_plugin_versions.py",
                     "tests/skills/skill-lifecycle/check_skill_lifecycle.py",
                     "tests/skills/skill-lifecycle/checks.json"):
            self.write("tools/" + path, (TOOLS / path).read_text())
        (self.repo / "tools/scripts/git/pre-push").chmod(0o755)
        self.skill_fixture()
        self.write("README.md", "original\n")
        self.base = self.commit()
        self.git("push", "origin", "main")
        hook = self.repo / ".git/hooks/pre-push"
        hook.write_text('#!/bin/sh\nset -eu\nrepo_root=$(git rev-parse --show-toplevel)\n'
                        'exec "$repo_root/tools/scripts/git/pre-push" "$@"\n')
        hook.chmod(0o755)

    def git(self, *args, cwd=None, check=True):
        result = subprocess.run(["git", "-C", str(cwd or self.repo), *args], env=self.env,
                                capture_output=True, text=True, timeout=30)
        if check:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result.stdout.strip()
        return result

    def write(self, path, text):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def skill_fixture(self):
        self.write(SKILL + "/SKILL.md", "---\nname: skill-lifecycle\ndescription: 생명 주기\n---\n# Skill\n")
        self.write(SKILL + "/references/lifecycle.md",
                   "# 운영\n\n## 생명 주기 순서\n\n1. `first` (첫째)\n\n"
                   "## 단계 정의 공통 항목\n\n- 진입 조건\n- 수행 작업\n- 완료 조건\n- 허용 전이\n- 산출물\n")
        self.write(SKILL + "/references/stages/first.md",
                   "# first (첫째)\n\n## 단계 운영 규칙\n\n"
                   + "".join("### " + name + "\n\n" for name in
                             ("진입 조건", "수행 작업", "완료 조건", "허용 전이", "산출물"))
                   + "## 명세서 기록 항목\n\n### 결과\n")
        self.write(SKILL + "/references/records/specification.md",
                   "# 형식\n\n### `operation` (작업 유형)\n\n- `create`: 생성\n")
        self.write(SKILL + "/assets/lifecycle-template.md",
                   "---\nname: <이름>\ntarget_path: <경로>\noperation: <create>\n"
                   "current_stage: first\nin_review: false\n---\n# <제목>\n\n"
                   "## first (첫째)\n\n### 진입 조건 확인\n\n### 결과\n\n"
                   "### 완료 조건 확인\n\n### 단계 이동 기록\n")

    def commit(self):
        self.git("add", "--all")
        self.git("commit", "-qm", "Fixture change")
        return self.git("rev-parse", "HEAD")

    def change_skill(self, invalid=False):
        self.write(SKILL + "/SKILL.md", "invalid\n" if invalid else
                   "---\nname: skill-lifecycle\ndescription: 변경된 생명 주기\n---\n# Skill\n")
        return self.commit()

    def push(self, *refs, success=True):
        result = self.git("push", "origin", *(refs or ("main",)), check=False)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def remote_tip(self, ref="main"):
        return self.git("rev-parse", "refs/heads/" + ref, cwd=self.remote)

    def another_check(self, name, passed=True):
        self.write(f".agents/skills/{name}/SKILL.md", "fixture\n")
        self.write(f"tools/tests/skills/{name}/checks.json", '{"scripts": ["check_contract.py"]}\n')
        self.write(f"tools/tests/skills/{name}/check_contract.py",
                   "import json\nimport sys\nprint(json.dumps({'passed': " + repr(passed)
                   + "}))\nsys.exit(" + ("0" if passed else "1") + ")\n")

    def test_valid_skill_change_is_checked_and_pushed(self):
        target = self.change_skill()
        output = self.push()
        self.assertIn("OK skill-lifecycle/check_skill_lifecycle.py", output)
        self.assertEqual(self.remote_tip(), target)

    def test_invalid_skill_change_is_rejected_without_remote_update(self):
        self.change_skill(invalid=True)
        output = self.push(success=False)
        self.assertIn("skill_metadata", output)
        self.assertEqual(self.remote_tip(), self.base)

    def test_readme_only_does_not_run_skill_checks(self):
        self.write(VALIDATOR, "raise RuntimeError('must not run')\n")
        self.write("README.md", "changed\n")
        self.commit()
        self.assertNotIn("CHECK skill-lifecycle/", self.push())

    def test_records_with_skill_name_do_not_select_skill(self):
        self.write("records/internal/skill-lifecycle/specification.md", "invalid\n")
        self.commit()
        self.assertNotIn("CHECK skill-lifecycle/", self.push())

    def test_uncommitted_fix_does_not_hide_committed_failure(self):
        self.change_skill(invalid=True)
        self.skill_fixture()
        self.git("add", SKILL)
        before = self.git("status", "--porcelain")
        self.push(success=False)
        self.assertEqual(self.remote_tip(), self.base)
        self.assertEqual(self.git("status", "--porcelain"), before)

    def test_invalid_worktree_does_not_affect_valid_commit(self):
        target = self.change_skill()
        self.write(SKILL + "/SKILL.md", "invalid worktree\n")
        self.push()
        self.assertEqual(self.remote_tip(), target)

    def test_sent_commit_is_checked_when_head_is_different(self):
        target = self.change_skill(invalid=True)
        self.git("switch", "--detach", self.base)
        self.push(target + ":refs/heads/main", success=False)
        self.assertEqual(self.remote_tip(), self.base)

    def test_new_branch_uses_published_boundary(self):
        self.change_skill(invalid=True)
        self.push("HEAD:refs/heads/new", success=False)
        self.assertNotEqual(self.git("rev-parse", "--verify", "refs/heads/new",
                                     cwd=self.remote, check=False).returncode, 0)

    def test_annotated_tag_checks_the_tagged_skill_commit(self):
        self.change_skill(invalid=True)
        self.git("tag", "-a", "invalid-skill", "-m", "Tagged invalid skill")
        self.assertIn("skill_metadata", self.push("refs/tags/invalid-skill", success=False))

    def test_published_commit_new_ref_and_ref_deletion_skip_skill_check(self):
        output = self.push("HEAD:refs/heads/new")
        self.assertNotIn("CHECK skill-lifecycle/", output)
        self.assertNotIn("CHECK skill-lifecycle/", self.push(":refs/heads/new"))

    def test_first_push_to_empty_remote_checks_all_registered_skills(self):
        empty = self.root / "empty.git"
        self.git("init", "--bare", str(empty), cwd=self.root)
        self.change_skill(invalid=True)
        result = self.git("push", str(empty), "main", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("skill_metadata", result.stderr)

    def test_multiple_ref_failure_blocks_all_updates(self):
        bad = self.change_skill(invalid=True)
        self.push(self.base + ":refs/heads/good", bad + ":refs/heads/main", success=False)
        self.assertEqual(self.remote_tip(), self.base)
        self.assertNotEqual(self.git("rev-parse", "--verify", "refs/heads/good",
                                     cwd=self.remote, check=False).returncode, 0)

    def test_same_commit_for_two_refs_runs_each_skill_once(self):
        self.change_skill()
        output = self.push("HEAD:refs/heads/one", "HEAD:refs/heads/two")
        self.assertEqual(output.count("CHECK skill-lifecycle/check_skill_lifecycle.py @"), 1)

    def test_multiple_skills_are_checked_even_after_failure(self):
        self.another_check("alpha", passed=False)
        self.another_check("zeta")
        self.change_skill()
        output = self.push(success=False)
        for label in ("alpha/check_contract.py", "skill-lifecycle/check_skill_lifecycle.py",
                      "zeta/check_contract.py"):
            self.assertIn("CHECK " + label, output)

    def test_missing_registration_is_reported_as_unregistered(self):
        self.write(".agents/skills/unregistered/SKILL.md", "changed\n")
        self.commit()
        self.assertIn("SKIP unregistered: no registered skill checks", self.push())

    def test_legacy_tests_are_not_inferred_from_filenames(self):
        self.write("tools/tests/skills/skill-lifecycle/test_legacy.py", "raise RuntimeError('must not run')\n")
        self.change_skill()
        self.assertIn("OK skill-lifecycle/check_skill_lifecycle.py", self.push())

    def test_broken_registration_blocks_push(self):
        for value in ('{', '{"scripts": []}', '{"scripts": ["missing.py"]}',
                      '{"scripts": ["../escape.py"]}', '{"scripts": ["a.py", "a.py"]}',
                      '{"scripts": ["a.py"], "scripts": ["b.py"]}', '{"scripts": [7]}'):
            with self.subTest(value=value):
                self.write(REGISTRATION, value)
                self.change_skill()
                self.assertIn("ERROR skill-lifecycle", self.push(success=False))

    def test_symlink_script_and_registration_are_errors(self):
        validator = self.repo / VALIDATOR
        validator.rename(validator.with_name("real.py"))
        validator.symlink_to("real.py")
        self.change_skill()
        self.assertIn("registered script is missing or not a regular file", self.push(success=False))
        manifest = self.repo / REGISTRATION
        manifest.rename(manifest.with_name("real.json"))
        manifest.symlink_to("real.json")
        self.assertIn("registration must not use symlinks", self.push(success=False))

    def test_execution_error_and_invalid_output_block_push(self):
        sources = ("raise RuntimeError('execution failed')\n", "print('true')\n",
                   "print('{\"passed\": \"true\"}')\n",
                   "print('{\"passed\": false}')\n",
                   "import sys\nprint('{\"passed\": true}')\nsys.exit(1)\n")
        for source in sources:
            with self.subTest(source=source):
                self.write(VALIDATOR, source)
                self.change_skill()
                self.assertIn("ERROR skill-lifecycle/check_skill_lifecycle.py", self.push(success=False))

    def test_plugin_skill_selection_and_version_check_both_apply(self):
        self.write("plugins/Example/plugin.json", '{"version": "1.0.0"}\n')
        self.write("plugins/Example/skills/alpha/SKILL.md", "fixture\n")
        self.another_check("alpha")
        (self.repo / ".agents/skills/alpha/SKILL.md").unlink()
        self.commit()
        output = self.push()
        self.assertIn("OK plugins/Example: NEW 1.0.0", output)
        self.assertIn("OK alpha/check_contract.py", output)
        self.write("plugins/Example/skills/alpha/SKILL.md", "changed\n")
        self.commit()
        output = self.push(success=False)
        self.assertIn("FAIL plugins/Example", output)
        self.assertIn("OK alpha/check_contract.py", output)

    def test_non_skill_plugin_change_does_not_select_skill(self):
        self.write("plugins/Example/plugin.json", '{"version": "1.0.0"}\n')
        self.write("plugins/Example/references/skill-lifecycle/note.md", "changed\n")
        self.commit()
        self.assertNotIn("CHECK skill-lifecycle/", self.push())

    def test_rename_and_mode_change_are_skill_changes(self):
        self.write(SKILL + "/scripts/old.py", "x = 1\n")
        self.commit()
        self.push()
        self.git("mv", SKILL + "/scripts/old.py", SKILL + "/scripts/new.py")
        self.commit()
        self.assertIn("CHECK skill-lifecycle/", self.push())
        (self.repo / SKILL / "scripts/new.py").chmod(0o755)
        self.commit()
        self.assertIn("CHECK skill-lifecycle/", self.push())

    def test_deleted_required_file_blocks_push(self):
        (self.repo / SKILL / "SKILL.md").unlink()
        self.commit()
        self.assertIn("skill_metadata", self.push(success=False))

    def test_whole_skill_deletion_still_runs_registered_check(self):
        self.git("rm", "-r", SKILL)
        self.commit()
        self.assertIn("FAIL skill-lifecycle/", self.push(success=False))

    def test_special_filename_and_linked_worktree(self):
        worktree = self.root / "linked"
        self.git("worktree", "add", "-b", "linked", str(worktree), self.base)
        file = worktree / SKILL / "references/name with\nnewline.md"
        file.write_text("[broken](missing.md)\n")
        self.git("add", "--all", cwd=worktree)
        self.git("commit", "-qm", "Linked change", cwd=worktree)
        result = self.git("push", "origin", "HEAD:refs/heads/linked", cwd=worktree, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("local_references", result.stderr)

    def test_malformed_input_and_unknown_objects_are_errors(self):
        for input_text in ("broken\n", f"main {'a' * 40} main {'b' * 40}\n"):
            result = subprocess.run([sys.executable, "-I", "-B", str(PUSH_CHECKS),
                                     "origin", str(self.remote)], cwd=self.repo, env=self.env,
                                    input=input_text, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_timeout_is_an_execution_error(self):
        self.write(VALIDATOR, "import time\ntime.sleep(5)\n")
        target = self.change_skill()
        driver = ("import importlib.util, sys\n"
                  "spec = importlib.util.spec_from_file_location('push_checks', sys.argv[1])\n"
                  "module = importlib.util.module_from_spec(spec)\n"
                  "spec.loader.exec_module(module)\n"
                  "module.CHECK_TIMEOUT = 0.01\n"
                  "sys.exit(module.main(sys.argv[2:]))\n")
        result = subprocess.run([sys.executable, "-I", "-B", "-c", driver, str(PUSH_CHECKS),
                                 "origin", str(self.remote)], cwd=self.repo, env=self.env,
                                input=f"refs/heads/main {target} refs/heads/main {self.base}\n",
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("timed out", result.stderr)


if __name__ == "__main__":
    unittest.main()
