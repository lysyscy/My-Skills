"""Read-only package checks against temporary local sources."""
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
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
        for name in ("first", "skill-package-ops"):
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

    def rename_source(self, old, new):
        skills = self.source / "skills"
        (skills / old).rename(skills / new)
        entry = skills / new / "SKILL.md"
        content = entry.read_text(encoding="utf-8").replace(f"name: {old}\n", f"name: {new}\n")
        entry.write_text(content, encoding="utf-8")
        policy = {**self.package.policy,
                  "previous_skill_directories": {**self.package.previous_skill_directories, new: old}}
        self.write("skill-package.json", json.dumps(policy))
        self.revision = self.commit("rename source directory")
        self.package = manager.Package(self.source)

    def commit(self, message):
        git(self.source, "add", "--all")
        git(self.source, "commit", "-m", message)
        return git(self.source, "rev-parse", "HEAD")


class SourceChecks(PackageFixture):
    def test_current_markdown_references_resolve(self):
        documents = [ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "CONTRIBUTING.md", *list((ROOT / "skills").rglob("*.md")),
                     ROOT / "docs/architecture.md", ROOT / "docs/agents/workflow.md"]
        for document in documents:
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("#"):
                    continue
                relative = target.split("#", 1)[0]
                path = (document.parent / relative).resolve()
                self.assertTrue(path.is_relative_to(ROOT), f"Link outside the repository: {document}: {target}")
                self.assertTrue(path.is_file(), f"{document}: {target}")

    def test_discovers_future_skills_and_protects_upstream(self):
        self.add_skill("future-third")
        self.assertEqual(self.package.discover(), ["first", "future-third", "skill-package-ops"])
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
        for name in ("first", "skill-package-ops"):
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
        self.assertEqual(set(choices), {
            "structure", "coupling", "preflight", "confirm-install", "confirm-source", "confirm-distribution",
        })
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


class BuiltinStructureChecks(PackageFixture):
    def structure_cli(self, source):
        return subprocess.run(
            [sys.executable, str(ROOT / "tools/skill_package.py"), "structure", "--source", str(source)],
            capture_output=True, text=True, encoding="utf-8",
        )

    def test_current_skills_pass_builtin_structure(self):
        shutil.rmtree(self.source / "skills")
        shutil.copytree(ROOT / "skills", self.source / "skills", symlinks=True)
        exceptions = json.loads((ROOT / "coupling-exceptions.json").read_text(encoding="utf-8"))
        skill_exceptions = [entry for entry in exceptions if entry["path"].startswith("skills/")]
        self.write("coupling-exceptions.json", json.dumps(skill_exceptions))
        run = self.structure_cli(self.source)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(result["validator"], "builtin:cross-host")
        self.assertEqual(result["status"], "verified")
        expected = {file.parent.name for file in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertEqual({check["skill"] for check in result["checks"]}, expected)
        self.assertTrue(all(check["exit_code"] == 0 for check in result["checks"]))
        self.assertEqual(result["coupling"]["violations"], [])

    def test_structure_fails_when_coupling_finds_a_host_call(self):
        self.write("AGENTS.md", "调用preview_open预览。\n")
        run = self.structure_cli(self.source)
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(result["status"], "validation_failed")
        self.assertTrue(all(check["exit_code"] == 0 for check in result["checks"]))
        self.assertEqual(
            [(item["path"], item["rule_id"]) for item in result["coupling"]["violations"]],
            [("AGENTS.md", "host-tool")],
        )

    def test_accepts_cross_host_fields_and_openai_structure(self):
        self.write("skills/first/SKILL.md", (
            '---\nname: "first" # skill ID\n'
            "description: >-\n  A folded description\n  spans two lines.\n"
            "compatibility: |\n  Works without third-party libraries.\n"
            "disable-model-invocation: true\nuser-invocable: true\n"
            "argument-hint: '[file #1]'\n"
            'metadata:\n  author: "测试: Example"\n  version: \'It\'\'s a string\'\n'
            "---\n\n"
            "- ```python\n  pass\n  ```\n"
            "~~~text\nan example\n~~~~\n"
        ))
        self.write("skills/first/agents/openai.yaml", (
            'interface:\n  display_name: "测试"\n'
            "dependencies:\n  tools:\n    - type: mcp\n      url: https://example.invalid/mcp\n"
            "policy:\n  allow_implicit_invocation: false # manual only\n"
        ))
        result = self.package.structure()
        self.assertEqual(result["status"], "verified", result)

    def test_rejects_bad_skill_metadata(self):
        for fields, expected in (
            ("name: first\ndescription: test\nunknown-key: value", "unknown-key"),
            ("name: first\ndescription: test\nmalformed", "expected a YAML mapping entry"),
            ("name: first\ndescription: test\ndescription: duplicate", "duplicate mapping key"),
            ("name: first\ndescription: test\ndisable-model-invocation: 'true'", "disable-model-invocation"),
            ("name: first\ndescription: test\nuser-invocable: yes", "user-invocable"),
            ("name: first\ndescription: test\nargument-hint: ''", "argument-hint"),
            ("name: first\ndescription: test\ncompatibility: false", "compatibility"),
            ("name: first\ndescription: test\ncompatibility: >-\n  " + "a" * 501, "compatibility"),
            ("name: first\ndescription: 1024", "description"),
            ("name: first\ndescription: ''", "description"),
            ("name: first\ndescription: 'Use <tag>'", "description"),
            ("name: first\ndescription: '[TODO: update]'", "description"),
            ("name: first\ndescription: |-\n  " + "a" * 1025, "description"),
            ("name: first--second\ndescription: test", "name"),
            ("name: wrong\ndescription: test", "must match the skill folder"),
        ):
            with self.subTest(expected=expected, fields=fields[:100]):
                self.write("skills/first/SKILL.md", f"---\n{fields}\n---\n")
                result = self.package.structure()
                self.assertEqual(result["status"], "validation_failed", result)
                failed, passed = result["checks"]
                self.assertEqual((failed["skill"], failed["exit_code"]), ("first", 1))
                self.assertIn(expected, failed["output"])
                self.assertEqual((passed["skill"], passed["exit_code"]), ("skill-package-ops", 0))

    def test_rejects_bad_openai_structure(self):
        for yaml, expected in (
            ("policy:\n  allow_implicit_invocation: maybe\n", "policy.allow_implicit_invocation"),
            ('policy:\n  allow_implicit_invocation: "false"\n', "policy.allow_implicit_invocation"),
            ("policy: true\n", "policy must be a mapping"),
            ("interface:\n  display_name\n", "expected a YAML mapping entry"),
        ):
            with self.subTest(yaml=yaml):
                self.write("skills/first/agents/openai.yaml", yaml)
                result = self.package.structure()
                self.assertEqual(result["status"], "validation_failed", result)
                self.assertIn(expected, result["checks"][0]["output"])

    def test_cli_rejects_unclosed_fence(self):
        self.write("skills/first/SKILL.md", "---\nname: first\ndescription: test\n---\n~~~~text\n~~~\n")
        run = self.structure_cli(self.source)
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(result["status"], "validation_failed")
        self.assertIn("unclosed fenced code block", result["checks"][0]["output"])

    def test_rejects_incomplete_frontmatter_and_invalid_utf8(self):
        for content in (b"---\nname: first\ndescription: test\n---extra\n",
                        b"---\rname: first\rdescription: test\r---\r", b"\xff"):
            with self.subTest(content=content):
                path = self.source / "skills/first/SKILL.md"
                path.write_bytes(content)
                result = self.package.structure()
                self.assertEqual(result["status"], "validation_failed", result)
                self.assertEqual(result["checks"][0]["skill"], "first")
                self.assertEqual(result["checks"][0]["exit_code"], 1)

if __name__ == "__main__":
    unittest.main()
