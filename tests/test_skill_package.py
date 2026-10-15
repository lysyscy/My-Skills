"""Read-only package checks against temporary local sources."""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("skill_package_checks", ROOT / "tools/skill_package.py")
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                            text=True, encoding="utf-8")
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class PackageFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="package-check-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.source = self.home / "source"
        self.remote = self.home / "remote.git"
        self.source.mkdir()
        self.remote.mkdir()
        git(self.remote, "init", "--bare", "--initial-branch=main")
        git(self.source, "init", "--initial-branch=main")
        git(self.source, "config", "user.email", "test@example.invalid")
        git(self.source, "config", "user.name", "Fixture")
        git(self.source, "config", "core.autocrlf", "false")
        git(self.source, "remote", "add", "origin", str(self.remote))
        policy = json.loads((ROOT / "skill-package.json").read_text(encoding="utf-8"))
        policy["remote"] = str(self.remote)
        self.write("skill-package.json", json.dumps(policy))
        self.write(".gitignore", "__pycache__/\n*.pyc\n")
        for name in ("first", "improve-workflow"):
            self.add_skill(name)
        self.write("skills/first/references/guide.md", "Original guide\n")
        self.revision = self.commit("initial fixture")
        self.package = manager.Package(self.source)

    def write(self, name, content):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def add_skill(self, name):
        self.write(f"skills/{name}/SKILL.md", f"---\nname: {name}\ndescription: Test task.\n---\n# Test\n")

    def commit(self, message):
        git(self.source, "add", "--all")
        git(self.source, "commit", "-m", message)
        return git(self.source, "rev-parse", "HEAD")


class SourceChecks(PackageFixture):
    def test_current_markdown_references_resolve(self):
        documents = [ROOT / "README.md", ROOT / "AGENTS.md", *list((ROOT / "skills").rglob("*.md")),
                     ROOT / "docs/architecture.md", ROOT / "docs/agents/workflow.md"]
        for document in documents:
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("#"):
                    continue
                relative = target.split("#", 1)[0]
                self.assertTrue((document.parent / relative).is_file(), f"{document}: {target}")

    def test_discovers_future_skills_and_protects_upstream(self):
        self.add_skill("future-third")
        self.assertEqual(self.package.discover(), ["first", "future-third", "improve-workflow"])
        self.add_skill("retro")
        with self.assertRaisesRegex(manager.PackageError, "Upstream"):
            self.package.discover()

    def test_wrong_remote_and_escaping_root_are_rejected(self):
        git(self.source, "remote", "set-url", "origin", "other-repo")
        with self.assertRaisesRegex(manager.PackageError, "Origin"):
            manager.Package(self.source)
        with self.assertRaises(manager.PackageError):
            manager.contained(self.source, "../outside")

    def test_missing_or_mismatched_frontmatter_is_rejected(self):
        for content in ("no header", "---\nname: wrong\ndescription: test\n---\n",
                        "---\nname: first\n---\n"):
            self.write("skills/first/SKILL.md", content)
            with self.subTest(content=content), self.assertRaises(manager.PackageError):
                self.package.discover()

    def test_empty_package_cannot_pass_discovery(self):
        for name in ("first", "improve-workflow"):
            (self.source / "skills" / name / "SKILL.md").unlink()
        with self.assertRaisesRegex(manager.PackageError, "No skills"):
            self.package.discover()

    def test_requires_fixed_clean_revision(self):
        self.package.require_revision(self.revision)
        for revision in ("main", self.revision[:8]):
            with self.assertRaises(manager.PackageError):
                self.package.require_revision(revision)
        self.write("new-note.txt", "Other work\n")
        with self.assertRaisesRegex(manager.PackageError, "clean source"):
            self.package.require_revision(self.revision)
        self.commit("new source")
        with self.assertRaises(manager.PackageError):
            self.package.require_revision(self.revision)

    def test_structure_dependency_failure_stops_before_validator(self):
        validator = self.home / "validator.py"
        validator.write_text("raise AssertionError('must not run')", encoding="utf-8")
        with patch.object(manager, "process", return_value=subprocess.CompletedProcess([], 1, "", "no yaml")) as run:
            result = self.package.structure(validator, Path(sys.executable))
        self.assertEqual(result["status"], "environment_blocked")
        self.assertEqual(result["checks"], [])
        self.assertEqual(run.call_count, 1)

    def test_structure_validates_every_skill_with_utf8_and_absolute_paths(self):
        validator = self.home / "检查.py"
        validator.write_text("pass\n", encoding="utf-8")
        self.add_skill("future-third")
        with patch.object(manager, "process", return_value=subprocess.CompletedProcess([], 0, "ok", "")) as run:
            result = self.package.structure(validator, Path(sys.executable))
        self.assertEqual(result["status"], "verified")
        self.assertEqual(len(result["checks"]), 3)
        for call in run.call_args_list:
            self.assertEqual(call.args[0][1:3], ["-X", "utf8"])
            self.assertTrue(Path(call.args[0][0]).is_absolute())

    def test_structure_failure_is_not_environment_failure(self):
        validator = self.home / "validator.py"
        validator.write_text("pass\n", encoding="utf-8")
        outcomes = [subprocess.CompletedProcess([], 0, "", ""),
                    subprocess.CompletedProcess([], 1, "invalid", ""),
                    subprocess.CompletedProcess([], 0, "ok", "")]
        with patch.object(manager, "process", side_effect=outcomes):
            self.assertEqual(self.package.structure(validator, Path(sys.executable))["status"], "validation_failed")

    def test_observation_preserves_index_and_creates_no_workflow_state(self):
        git(self.source, "update-index", "--refresh")
        index = self.source / ".git/index"
        tracked = self.source / "skills/first/SKILL.md"
        os.utime(tracked, (tracked.stat().st_atime + 10, tracked.stat().st_mtime + 10))
        before = index.read_bytes(), index.stat().st_mtime_ns
        manager.Package(self.source).require_revision(self.revision)
        self.assertEqual((index.read_bytes(), index.stat().st_mtime_ns), before)
        self.assertFalse((self.source / ".git/workflow-state").exists())

    def test_retired_cli_actions_are_refused_without_touching_source(self):
        before = git(self.source, "status", "--porcelain")
        help_result = subprocess.run([sys.executable, str(ROOT / "tools/skill_package.py"), "--help"],
                                     capture_output=True, text=True)
        choices = re.search(r"\{([^}]+)\}", help_result.stdout).group(1).split(",")
        self.assertEqual(set(choices), {"structure", "preflight", "confirm-install"})
        for action in ("prepare", "verify", "publish", "resume", "sync", "sync-manager", "read", "inspect"):
            result = subprocess.run([sys.executable, str(ROOT / "tools/skill_package.py"), action,
                                     "--source", str(self.home / "absent-source")], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, action)
        self.assertEqual(git(self.source, "status", "--porcelain"), before)
        self.assertFalse((self.source / ".git/workflow-state").exists())

    def test_broken_cli_bridge_cannot_fall_back(self):
        bridge = self.home / ".skills-manager/bin"
        bridge.mkdir(parents=True)
        (bridge / ".version").write_text("1.42.0", encoding="utf-8")
        with patch.object(manager.Path, "home", return_value=self.home), patch.object(manager.shutil, "which") as fallback:
            with self.assertRaisesRegex(manager.PackageError, "bridge is incomplete"):
                manager.skills_manager_cli()
            fallback.assert_not_called()

    def test_query_errors_and_invalid_json_are_reported(self):
        for response in (subprocess.CompletedProcess([], 1, "", "TARGET_CONFLICT"),
                         subprocess.CompletedProcess([], 0, "bad json", ""),
                         subprocess.CompletedProcess([], 0, '{"ok": false, "message": "refused"}', "")):
            with patch.object(manager, "process", return_value=response), self.assertRaises(manager.PackageError):
                manager.manager_json("fixture", "skills", "list")

    def test_resource_fingerprints_have_unambiguous_file_boundaries(self):
        one_file = [("a", b"payloadb\x00content")]
        two_files = [("a", b"payload"), ("b", b"content")]
        self.assertNotEqual(manager.fingerprint(one_file), manager.fingerprint(two_files))

    def test_unreadable_resource_tree_cannot_pass(self):
        def unreadable(path, *, followlinks, onerror):
            onerror(PermissionError("fixture unreadable resource"))
        with patch.object(manager.os, "walk", side_effect=unreadable), self.assertRaises(PermissionError):
            manager.directory_fingerprint(self.source / "skills/first")


if __name__ == "__main__":
    unittest.main()
