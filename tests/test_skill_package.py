"""Behavioral transactions using local bare remotes; no real account or installation.

SKILL_PACKAGE_CANDIDATE lets a frozen old test suite target a new candidate.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(os.environ.get("SKILL_PACKAGE_CANDIDATE", Path(__file__).resolve().parents[1]))
spec = importlib.util.spec_from_file_location("skill_package_candidate", ROOT / "tools/skill_package.py")
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                            text=True, encoding="utf-8")
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class Transactions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = tempfile.TemporaryDirectory(prefix="skill-package-template-")
        cls.addClassCleanup(cls.template.cleanup)
        template = Path(cls.template.name)
        cls.template_remote = template / "remote.git"
        cls.template_source = template / "source"
        cls.template_remote.mkdir()
        git(cls.template_remote, "init", "--bare", "--initial-branch=main")
        git(template, "clone", str(cls.template_remote), str(cls.template_source))
        git(cls.template_source, "config", "user.email", "test@example.invalid")
        git(cls.template_source, "config", "user.name", "Fixture")
        git(cls.template_source, "config", "core.autocrlf", "false")
        policy = json.loads((ROOT / "skill-package.json").read_text(encoding="utf-8"))
        policy.update(remote=str(cls.template_remote), checks=[["{python}", "-c", "pass"]])
        content = {"skill-package.json": json.dumps(policy), ".gitignore": "__pycache__/\n*.pyc\n",
                   "tools/skill_package.py": (ROOT / "tools/skill_package.py").read_text(encoding="utf-8")}
        for name in ("first", "improve-workflow"):
            content[f"skills/{name}/SKILL.md"] = f"---\nname: {name}\ndescription: Test task.\n---\n# Test\n"
        for name, text in content.items():
            path = cls.template_source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        git(cls.template_source, "add", "--", *content)
        git(cls.template_source, "commit", "-m", "fixture template")
        git(cls.template_source, "push", "origin", "main")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="skill-package-test-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.remote = self.home / "remote.git"
        self.source = self.home / "source"
        self.install = self.home / "user" / "skills"
        shutil.copytree(self.template_remote, self.remote)
        shutil.copytree(self.template_source, self.source)
        git(self.source, "remote", "set-url", "origin", str(self.remote))
        policy = manager.read_json(self.source / "skill-package.json")
        policy["remote"] = str(self.remote)
        policy["checks"] = [["{python}", "-c", "pass"]]
        self.write("skill-package.json", json.dumps(policy))
        self.commit(self.source, "initial")
        git(self.source, "push", "origin", "main")
        self.package = manager.Package(self.source)

    def write(self, name, content, root=None):
        path = (root or self.source) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def add_skill(self, root, name):
        self.write(f"skills/{name}/SKILL.md", f"---\nname: {name}\ndescription: Test task.\n---\n# Test\n", root)

    def commit(self, root, message):
        names = manager.files(root)
        git(root, "add", "--", *names)
        git(root, "commit", "-m", message)
        return git(root, "rev-parse", "HEAD")

    def prepare(self, run="trial"):
        state = self.package.prepare(run)
        return Path(state["worktree"])

    def candidate(self, run="trial", name="new-file.txt"):
        worktree = self.prepare(run)
        self.write(name, run + "\n", worktree)
        self.assertEqual(self.package.verify(run)["status"], "verified")
        self.commit(worktree, run)
        return worktree

    def test_discovers_future_skill_and_itself(self):
        self.add_skill(self.source, "future-third")
        self.assertEqual(self.package.discover(), ["first", "future-third", "improve-workflow"])

    def managed_fixture(self):
        library = self.home / "manager" / "skills"
        agents = self.home / "agent" / "skills"
        library.mkdir(parents=True)
        agents.mkdir(parents=True)
        metadata_root = self.home / "manager" / "metadata"
        (metadata_root / "skills").mkdir(parents=True)
        records = []
        for name in self.package.discover():
            shutil.copytree(self.source / "skills" / name, library / name)
            manager.link_directory(library / name, agents / name)
            records.append({"id": name, "name": name, "path": str(library / name), "source_type": "git",
                            "source_ref": self.package.policy["remote"], "deployed_to": ["fixture"]})
            (metadata_root / "skills" / (name + ".json")).write_text(json.dumps({
                "skill_id": name, "path": name, "source": {"type": "git", "ref": self.package.policy["remote"],
                "subpath": "skills\\" + name, "branch": None}}), encoding="utf-8")
        def response(cli, *args):
            return {("repo", "status"): {"skills_dir": str(library), "metadata_dir": str(metadata_root)},
                    ("skills", "list"): records,
                    ("agents", "list"): [{"key": "fixture", "skills_dir": str(agents)}]}[args]
        return library, agents, response

    def test_source_only_sync_never_writes_installation(self):
        self.install.mkdir(parents=True)
        marker = self.install / "keep.txt"
        marker.write_text("manager owned")
        result = self.package.sync(self.install, source_only=True)
        self.assertEqual(result["status"], "source_synced")
        self.assertEqual(list(self.install.iterdir()), [marker])
        self.assertEqual(marker.read_text(), "manager owned")

    def test_cli_sync_uses_source_only_even_when_install_root_is_given(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools/skill_package.py"), "sync",
                                 "--source", str(self.source), "--install-root", str(self.install)],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(json.loads(result.stdout)["status"], "source_synced")
        self.assertFalse(self.install.exists())

    def test_confirm_manager_library_and_actual_agent_links(self):
        library, agents, response = self.managed_fixture()
        with patch.object(manager, "manager_json", side_effect=response):
            result = self.package.confirm_install("fixture-cli")
        self.assertEqual(result["installation_manager"], "skills-manager")
        self.assertEqual(result["deployments"]["first"], ["fixture"])
        report = self.package.inspect(library, manager_owned=True)
        self.assertEqual(report["installation"]["first"]["expected_target"], str(library / "first"))
        self.assertTrue(report["installation"]["first"]["matches_source"])
        (library / "first/SKILL.md").write_text("stale")
        with patch.object(manager, "manager_json", side_effect=response), self.assertRaisesRegex(manager.PackageError, "differs"):
            self.package.confirm_install("fixture-cli")

    def test_confirm_does_not_trust_deployment_metadata_without_files(self):
        library, agents, response = self.managed_fixture()
        target = agents / "first"
        if target.is_symlink():
            target.unlink()
        else:
            target.rmdir()
        with patch.object(manager, "manager_json", side_effect=response), self.assertRaisesRegex(manager.PackageError, "deployment"):
            self.package.confirm_install("fixture-cli")

    def test_source_sync_keeps_run_pending_until_manager_confirmation(self):
        self.candidate()
        self.package.publish("trial")
        self.package.sync(self.install, "trial", source_only=True)
        self.assertEqual(self.package.load_run("trial")[1]["status"], "source_synced")
        self.assertTrue(self.package.inspect(self.install)["pending"])
        library, agents, response = self.managed_fixture()
        with patch.object(manager, "manager_json", side_effect=response):
            self.package.confirm_install("fixture-cli", "trial")
        self.assertEqual(self.package.load_run("trial")[1]["status"], "synced")

    def test_invalid_manager_source_and_errors_cannot_close_run(self):
        library, agents, response = self.managed_fixture()
        records = response("fixture", "skills", "list")
        records[0]["source_ref"] = "https://example.invalid/other"
        with patch.object(manager, "manager_json", side_effect=response), self.assertRaisesRegex(manager.PackageError, "source differs"):
            self.package.confirm_install("fixture-cli")
        remote_reference = self.package.policy["remote"].removesuffix(".git")
        for suffix in ("/tree/other/skills/first", "/tree/main/skills/other"):
            records[0]["source_ref"] = remote_reference + suffix
            with patch.object(manager, "manager_json", side_effect=response), self.assertRaisesRegex(manager.PackageError, "source differs"):
                self.package.confirm_install("fixture-cli")
        records[0]["source_ref"] = remote_reference + "/tree/main/skills/first"
        metadata_path = Path(response("fixture", "repo", "status")["metadata_dir"]) / "skills/first.json"
        metadata = manager.read_json(metadata_path)
        metadata["source"]["ref"] = records[0]["source_ref"]
        manager.write_json(metadata_path, metadata)
        with patch.object(manager, "manager_json", side_effect=response):
            self.assertEqual(self.package.confirm_install("fixture-cli")["status"], "synced")
        for field, value in (("subpath", "skills/other"), ("branch", "other")):
            modified = json.loads(json.dumps(metadata))
            modified["source"][field] = value
            manager.write_json(metadata_path, modified)
            with patch.object(manager, "manager_json", side_effect=response), self.assertRaisesRegex(manager.PackageError, "source " + field):
                self.package.confirm_install("fixture-cli")
        with patch.object(manager, "process", return_value=subprocess.CompletedProcess([], 1, "", "refused")), self.assertRaisesRegex(manager.PackageError, "refused"):
            manager.manager_json("fixture", "skills", "list")

    def test_inspect_reports_actual_installation_links_and_copies(self):
        self.install.mkdir(parents=True)
        missing = self.package.inspect(self.install)["installation"]["first"]
        self.assertEqual(missing["kind"], "missing")
        source = self.source / "skills/first"
        entry = self.install / "first"
        manager.link_directory(source, entry)
        report = self.package.inspect(self.install)["installation"]["first"]
        self.assertIn(report["kind"], ("symlink", "directory_link"))
        self.assertEqual(report["target"], str(source.resolve()))
        self.assertTrue(report["matches_source"])
        if entry.is_symlink():
            entry.unlink()
        else:
            entry.rmdir()
        shutil.copytree(source, entry)
        copy = self.package.inspect(self.install)["installation"]["first"]
        self.assertEqual(copy["kind"], "copy")
        self.assertTrue(copy["matches_source"])
        (entry / "SKILL.md").write_text("independent change", encoding="utf-8")
        self.assertFalse(self.package.inspect(self.install)["installation"]["first"]["matches_source"])

    def test_structure_missing_dependency_stops_before_validator(self):
        validator = self.home / "quick_validate.py"
        validator.write_text("raise AssertionError('must not run')", encoding="utf-8")
        failed = subprocess.CompletedProcess([], 1, "", "ModuleNotFoundError: No module named 'yaml'")
        with patch.object(manager, "process", return_value=failed) as calls:
            result = self.package.structure(validator, Path(sys.executable))
        self.assertEqual(result["status"], "environment_blocked")
        self.assertEqual(result["dependency"], "yaml")
        self.assertEqual(calls.call_count, 1)
        self.assertEqual(result["checks"], [])

    def test_structure_reports_validation_failure_separately(self):
        validator = self.home / "quick_validate.py"
        validator.write_text("# fixture", encoding="utf-8")
        ready = subprocess.CompletedProcess([], 0, "", "")
        failed = subprocess.CompletedProcess([], 1, "invalid frontmatter", "")
        passed = subprocess.CompletedProcess([], 0, "Skill is valid!", "")
        with patch.object(manager, "process", side_effect=[ready, failed, passed]):
            result = self.package.structure(validator, Path(sys.executable))
        self.assertEqual(result["status"], "validation_failed")
        self.assertEqual([check["exit_code"] for check in result["checks"]], [1, 0])

    def test_structure_uses_absolute_validator_and_all_discovered_skills(self):
        validator = self.home / "quick_validate.py"
        validator.write_text("# fixture", encoding="utf-8")
        passed = subprocess.CompletedProcess([], 0, "Skill is valid!", "")
        with patch.object(manager, "process", return_value=passed) as calls:
            result = self.package.structure(validator, Path(sys.executable))
        self.assertEqual(result["status"], "verified")
        self.assertEqual(len(result["checks"]), 2)
        self.assertEqual(calls.call_args_list[1].args[0][1:4], ["-X", "utf8", str(validator.resolve())])

    def test_structure_reads_unicode_even_when_host_disables_utf8(self):
        self.write("skills/first/SKILL.md", "---\nname: first\ndescription: 中文验证\n---\n")
        validator = self.home / "验证器.py"
        validator.write_text("import sys\nfrom pathlib import Path\n(Path(sys.argv[1])/'SKILL.md').read_text()\n", encoding="utf-8")
        original = manager.process
        def without_yaml_dependency(args, **kwargs):
            if args[-1] == "import yaml":
                return subprocess.CompletedProcess(args, 0, "", "")
            return original(args, **kwargs)
        with patch.dict(os.environ, {"PYTHONUTF8": "0"}), patch.object(manager, "process", side_effect=without_yaml_dependency):
            self.assertEqual(self.package.structure(validator, Path(sys.executable))["status"], "verified")

    def test_upstream_and_path_escape_are_rejected(self):
        self.add_skill(self.source, "retro")
        with self.assertRaises(manager.PackageError):
            self.package.discover()
        with self.assertRaises(manager.PackageError):
            manager.contained(self.source, "../outside")

    def test_wrong_remote_refuses_management(self):
        git(self.source, "remote", "set-url", "origin", str(self.home / "foreign.git"))
        with self.assertRaises(manager.PackageError):
            manager.Package(self.source)

    def test_dirty_source_is_preserved_and_not_applied_blindly(self):
        self.write("skills/first/SKILL.md", "old optimization")
        self.write("extra.txt", "new local idea")
        worktree = self.prepare()
        directory, state = self.package.load_run("trial")
        self.assertEqual((directory / "source-snapshot/extra.txt").read_text(), "new local idea")
        self.assertEqual((self.source / "skills/first/SKILL.md").read_text(), "old optimization")
        self.assertIn("# Test", (worktree / "skills/first/SKILL.md").read_text())
        self.assertEqual(state["source_head"], git(self.source, "rev-parse", "HEAD"))

    def test_three_projects_isolate_and_integrate_before_publish(self):
        for run in ("one", "two", "three"):
            self.candidate(run, run + ".txt")
        git(self.source, "config", "--unset", "user.name")
        git(self.source, "config", "--unset", "user.email")
        with patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(self.home / "empty-global"), "GIT_CONFIG_NOSYSTEM": "1"}):
            self.assertEqual(self.package.publish("one")["status"], "published")
            for run in ("two", "three"):
                self.assertEqual(self.package.publish(run)["status"], "needs_verification")
                self.assertEqual(self.package.verify(run)["status"], "verified")
                self.assertEqual(self.package.publish(run)["status"], "published")
        self.assertEqual(self.package.sync(self.install, "three")["status"], "synced")
        for name in ("one", "two", "three"):
            self.assertTrue((self.source / (name + ".txt")).is_file())

    def test_same_file_conflict_preserves_both_worktrees(self):
        first = self.candidate("one", "shared.txt")
        second = self.candidate("two", "shared.txt")
        self.package.publish("one")
        self.assertEqual(self.package.publish("two")["status"], "conflict")
        self.assertEqual((first / "shared.txt").read_text(), "one\n")
        self.assertIn("<<<<<<<", (second / "shared.txt").read_text())

    def test_validation_failure_and_changed_inputs_block_publish(self):
        self.candidate()
        worktree = Path(self.package.load_run("trial")[1]["worktree"])
        self.write("new-file.txt", "changed after checks", worktree)
        with self.assertRaises(manager.PackageError):
            self.package.publish("trial")
        self.assertFalse((self.install / "improve-workflow").exists())
        self.write("new-file.txt", "trial\n", worktree)
        original_process = manager.process
        def timeout_check(args, **kwargs):
            if args[0] == sys.executable:
                raise subprocess.TimeoutExpired(args, 120)
            return original_process(args, **kwargs)
        with patch.object(manager, "process", side_effect=timeout_check):
            with self.assertRaises(subprocess.TimeoutExpired):
                self.package.verify("trial")
        self.assertIsNone(self.package.load_run("trial")[1]["verified_digest"])
        with self.assertRaises(manager.PackageError):
            self.package.publish("trial")

    def test_self_update_uses_snapshot_and_old_regression(self):
        self.write("tests/test_previous.py", "import unittest, os, runpy\nfrom pathlib import Path\nclass Previous(unittest.TestCase):\n def test_old(self):\n  tool = runpy.run_path(str(Path(os.environ['SKILL_PACKAGE_CANDIDATE']) / 'tools/skill_package.py'))\n  self.assertTrue(callable(tool['Package']))\n")
        worktree = self.prepare()
        directory, state = self.package.load_run("trial")
        self.write("tools/skill_package.py", "raise RuntimeError('candidate fails')\n", worktree)
        (worktree / "tests/test_previous.py").unlink(missing_ok=True)
        result = self.package.verify("trial")
        self.assertEqual(result["status"], "verification_failed")
        self.assertTrue(Path(state["runtime"]).is_file())
        self.assertEqual(Path(state["runtime"]).read_bytes(), (ROOT / "tools/skill_package.py").read_bytes())
        self.assertTrue(Path(state["entry"]).is_file())
        self.assertIn("class Package", (self.source / "tools/skill_package.py").read_text())

    def test_policy_cannot_expand_itself(self):
        worktree = self.prepare()
        policy = manager.read_json(worktree / "skill-package.json")
        policy["authorization"] = "expanded without user choice"
        self.write("skill-package.json", json.dumps(policy), worktree)
        with self.assertRaises(manager.PackageError):
            self.package.verify("trial")
        policy["authorization"] = self.package.policy["authorization"]
        policy["upstream_skills"].append("future-matt-dependency")
        policy["checks"].append(["{python}", "-c", "raise SystemExit(1)"])
        self.write("skill-package.json", json.dumps(policy), worktree)
        self.assertEqual(self.package.verify("trial")["status"], "verification_failed")

    def test_push_failure_has_bounded_resumable_attempts(self):
        self.candidate()
        original = manager.git
        def failed_push(root, *args, **kwargs):
            if args and args[0] == "push":
                return subprocess.CompletedProcess(args, 1, "", "network unavailable")
            return original(root, *args, **kwargs)
        with patch.object(manager, "git", side_effect=failed_push):
            for attempt in range(1, 4):
                self.assertEqual(self.package.publish("trial")["attempts"], attempt)
            self.assertEqual(self.package.publish("trial")["status"], "pending")
        self.assertTrue(Path(self.package.load_run("trial")[1]["worktree"]).is_dir())
        self.assertEqual(self.package.resume("trial")["attempts"], 0)
        self.assertEqual(self.package.publish("trial")["status"], "published")

    def test_uncertain_success_is_detected_without_duplicate_publish(self):
        worktree = self.candidate()
        git(worktree, "push", "origin", "HEAD:main")
        state = self.package.resume("trial")
        self.assertEqual(state["status"], "published")
        self.assertTrue(self.package.publish("trial")["already_published"])

    def test_offline_prepare_saves_originals(self):
        self.write("dirty.txt", "preserve me")
        with patch.object(self.package, "fetch", side_effect=manager.PackageError("offline")):
            with self.assertRaises(manager.PackageError):
                self.package.prepare("offline")
        directory, state = self.package.load_run("offline")
        self.assertEqual(state["status"], "prepare_failed")
        self.assertEqual((directory / "source-snapshot/dirty.txt").read_text(), "preserve me")
        resumed = self.package.resume("offline")
        self.assertEqual(resumed["status"], "prepared")
        self.assertTrue(Path(resumed["worktree"]).is_dir())

    def test_install_future_skill_preserves_matt_and_is_idempotent(self):
        self.install.mkdir(parents=True)
        matt = self.install / "retro" / "SKILL.md"
        matt.parent.mkdir()
        matt.write_text("Matt original")
        worktree = self.prepare()
        self.add_skill(worktree, "future-third")
        self.package.verify("trial")
        self.commit(worktree, "future")
        self.package.publish("trial")
        first = self.package.sync(self.install, "trial")
        second = self.package.sync(self.install)
        self.assertEqual(first["commit"], second["commit"])
        self.assertEqual((self.install / "future-third").resolve(), (self.source / "skills/future-third").resolve())
        self.assertEqual(matt.read_text(), "Matt original")

    def test_adopt_copy_and_failed_install_restore_original(self):
        old = self.install / "first"
        old.mkdir(parents=True)
        (old / "SKILL.md").write_text("old personal copy")
        with self.assertRaises(manager.PackageError):
            self.package.sync(self.install)
        with patch.object(manager, "link_directory", side_effect=manager.PackageError("cannot link")):
            with self.assertRaises(manager.PackageError):
                self.package.sync(self.install, adopt_copies=True)
        self.assertEqual((old / "SKILL.md").read_text(), "old personal copy")
        result = self.package.sync(self.install, adopt_copies=True)
        self.assertEqual(result["status"], "synced")
        backups = list((self.install.parent / "skill-install-backups").glob("*/first/SKILL.md"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "old personal copy")

    def test_dirty_sync_requires_matching_saved_snapshot(self):
        self.write("original.txt", "old optimization")
        self.candidate()
        self.package.publish("trial")
        self.write("original.txt", "another task's new work")
        with self.assertRaises(manager.PackageError):
            self.package.sync(self.install, "trial", reconcile_source=True)
        self.assertEqual((self.source / "original.txt").read_text(), "another task's new work")

    def test_reconciled_dirty_source_keeps_original_snapshot(self):
        self.write("original.txt", "old optimization")
        worktree = self.candidate()
        self.write("original.txt", "reconciled on latest", worktree)
        self.package.verify("trial")
        self.commit(worktree, "reconcile")
        self.package.publish("trial")
        self.assertEqual(self.package.sync(self.install, "trial", reconcile_source=True)["status"], "synced")
        directory, _ = self.package.load_run("trial")
        self.assertEqual((directory / "source-snapshot/original.txt").read_text(), "old optimization")
        self.assertEqual((self.source / "original.txt").read_text(), "reconciled on latest")

    def test_shared_transaction_excludes_other_writer(self):
        other = manager.Package(self.source)
        with self.package.transaction():
            with self.assertRaises(manager.PackageError):
                with other.transaction():
                    self.fail("second owner acquired transaction")

    def test_tampered_source_snapshot_cannot_release_dirty_work(self):
        self.write("original.txt", "original")
        self.candidate()
        self.package.publish("trial")
        directory, _ = self.package.load_run("trial")
        (directory / "source-snapshot/original.txt").write_text("lost evidence")
        with self.assertRaises(manager.PackageError):
            self.package.sync(self.install, "trial", reconcile_source=True)
        self.assertEqual((self.source / "original.txt").read_text(), "original")

    def test_cli_requires_pinned_runtime(self):
        self.prepare()
        state = self.package.load_run("trial")[1]
        args = ["inspect", "--source", str(self.source), "--install-root", str(self.install)]
        result = manager.process([sys.executable, state["runtime"], *args])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["skills"], ["first", "improve-workflow"])
        blocked = manager.process([sys.executable, str(ROOT / "tools/skill_package.py"),
                                   "verify", "--source", str(self.source), "--run", "trial"])
        self.assertEqual(blocked.returncode, 1)
        verified = manager.process([sys.executable, state["runtime"], "verify",
                                    "--source", str(self.source), "--run", "trial"])
        self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)

    def test_document_only_change_uses_structural_check(self):
        worktree = self.prepare()
        self.add_skill(worktree, "future-document")
        result = self.package.verify("trial")
        self.assertEqual(result["status"], "verified")
        self.assertEqual([check["command"] for check in result["checks"]], [["package-discovery"]])

    def test_no_change_does_not_create_commit(self):
        before = git(self.source, "rev-parse", "HEAD")
        self.prepare()
        self.package.verify("trial")
        self.assertTrue(self.package.publish("trial")["no_change"])
        self.assertEqual(git(self.source, "rev-parse", "HEAD"), before)

    def test_unpublished_run_remains_pending_after_sync_attempt(self):
        self.candidate()
        with self.assertRaises(manager.PackageError):
            self.package.sync(self.install, "trial")
        self.assertEqual(self.package.inspect(self.install)["pending"][0]["run"], "trial")
        self.assertNotIn("published", self.package.load_run("trial")[1])
        self.assertFalse(self.install.exists())

    def test_unpublished_local_main_is_never_installed(self):
        self.add_skill(self.source, "unpublished")
        before = self.commit(self.source, "local unpublished")
        with self.assertRaises(manager.PackageError):
            self.package.sync(self.install)
        self.assertEqual(git(self.source, "rev-parse", "HEAD"), before)
        self.assertFalse(self.install.exists())

    def test_sync_requires_remote_to_contain_acknowledged_publication(self):
        worktree = self.candidate()
        directory, state = self.package.load_run("trial")
        state.update(status="published", published=git(worktree, "rev-parse", "HEAD"))
        self.package.save_run(directory, state)
        with self.assertRaises(manager.PackageError):
            self.package.sync(self.install, "trial")
        self.assertEqual(self.package.load_run("trial")[1]["status"], "published")

    def test_failed_relink_keeps_original_entry_without_recreating_it(self):
        old_target = self.package.state_root / "previous-first"
        old_target.mkdir(parents=True)
        (old_target / "SKILL.md").write_text("previous compatible entry")
        self.install.mkdir(parents=True)
        manager.link_directory(old_target, self.install / "first")
        with patch.object(manager, "link_directory", side_effect=manager.PackageError("link creation unavailable")):
            with self.assertRaises(manager.PackageError):
                self.package.sync(self.install)
        self.assertEqual((self.install / "first").resolve(), old_target.resolve())
        self.assertEqual((self.install / "first/SKILL.md").read_text(), "previous compatible entry")

    def test_upstream_change_detection_snapshots_and_compatible_baseline(self):
        original = self.install / "retro" / "SKILL.md"
        original.parent.mkdir(parents=True)
        original.write_text("original version one")
        implementation = self.install / "implement" / "SKILL.md"
        implementation.parent.mkdir()
        implementation.write_text("implementation contract one")
        self.assertEqual(self.package.inspect(self.install)["upstream"]["status"], "unverified")
        state = self.package.prepare("upstream-one", install_root=self.install)
        directory, _ = self.package.load_run("upstream-one")
        self.assertEqual((directory / "upstream-inputs/retro/SKILL.md").read_text(), "original version one")
        self.package.verify("upstream-one", checked_upstream=["implement"])
        self.package.publish("upstream-one")
        self.package.sync(self.install, "upstream-one")
        self.assertEqual(self.package.inspect(self.install)["upstream"]["changed"], ["retro"])
        self.package.prepare("retro-reviewed", install_root=self.install)
        self.package.verify("retro-reviewed", checked_upstream=["retro"])
        self.package.publish("retro-reviewed")
        self.package.sync(self.install, "retro-reviewed")
        self.assertEqual(self.package.inspect(self.install)["upstream"]["status"], "checked")
        original.write_text("original version two")
        changed = self.package.inspect(self.install)["upstream"]
        self.assertEqual(changed["changed"], ["retro"])
        self.assertEqual(changed["status"], "changed")
        self.package.prepare("upstream-two", install_root=self.install)
        original.write_text("changed again before completion")
        self.package.verify("upstream-two", checked_upstream=["retro"])
        self.package.publish("upstream-two")
        self.package.sync(self.install, "upstream-two")
        self.assertEqual(self.package.inspect(self.install)["upstream"]["status"], "changed")


class MaterialReading(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="skill-material-test-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

    def test_large_manifest_has_bounded_overview_and_selected_window(self):
        path = self.home / "manifest.json"
        content = {"files": [{"path": f"目录/文件 {i}.md", "sha256": "a" * 64} for i in range(2000)]}
        path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
        overview = manager.read_material(path)
        self.assertEqual(overview["view"], "json_overview")
        self.assertIn('"items": 2000', overview["text"])
        self.assertLess(len(json.dumps(overview)), 4000)
        selected = manager.read_material(path, pointer="/files", limit=100)
        self.assertEqual(selected["items"], 2000)
        self.assertFalse(selected["complete"])
        self.assertEqual(selected["next_offset"], 100)
        followup = manager.read_material(path, pointer="/files", offset=100, limit=100)
        self.assertEqual(selected["text"] + followup["text"], json.dumps(content["files"], ensure_ascii=False, indent=2)[:200])

    def test_relative_reference_uses_referring_file_not_working_directory(self):
        folder = self.home / "技能目录"
        folder.mkdir()
        entry = folder / "SKILL.md"
        entry.write_text("[reference](SKILL-MECHANICS.md)", encoding="utf-8")
        reference = folder / "SKILL-MECHANICS.md"
        reference.write_text("correct reference", encoding="utf-8")
        result = manager.read_material(Path("SKILL-MECHANICS.md"), relative_to=entry)
        self.assertEqual(result["path"], str(reference.resolve()))
        self.assertEqual(result["text"], "correct reference")
        with self.assertRaises(manager.PackageError):
            manager.read_material(Path("references/SKILL-MECHANICS.md"), relative_to=entry)

    def test_read_rejects_invalid_windows_and_supports_pointer_escaping(self):
        path = self.home / "data.json"
        path.write_text('{"a/b": {"~": "值"}}', encoding="utf-8")
        self.assertEqual(manager.read_material(path, pointer="/a~1b/~0")["text"], '"值"')
        for options in ({"limit": 0}, {"limit": 6001}, {"offset": -1}, {"pointer": "/missing"}):
            with self.assertRaises(manager.PackageError):
                manager.read_material(path, **options)

    def test_read_cli_needs_no_run_or_git_repository(self):
        path = self.home / "大文件.md"
        path.write_text("字符" * 5000, encoding="utf-8")
        result = manager.process([sys.executable, str(ROOT / "tools/skill_package.py"), "read", "--file", str(path), "--limit", "200"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        read = json.loads(result.stdout)
        self.assertEqual(len(read["text"]), 200)
        self.assertFalse(read["complete"])


if __name__ == "__main__":
    unittest.main()
