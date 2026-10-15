"""Installation checks use real temporary files and a query-only Manager fake."""
import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

from test_skill_package import PackageFixture, git, manager
from setup_fixture import link_directory


class FakeManager:
    def __init__(self, case):
        self.case = case
        self.library = case.home / "manager/skills"
        self.metadata = case.home / "manager/metadata/skills"
        self.agent_root = case.home / "agent/skills"
        self.metadata.mkdir(parents=True)
        self.agent_root.mkdir(parents=True)
        self.records = []
        self.agents = [{"key": "fixture", "skills_dir": str(self.agent_root)}]
        self.calls = []
        for name in case.package.discover():
            shutil.copytree(case.source / "skills" / name, self.library / name)
            shutil.copytree(self.library / name, self.agent_root / name)
            record = {"id": "opaque-" + name, "name": name, "path": str(self.library / name),
                      "source_type": "git", "source_ref": case.package.policy["remote"],
                      "deployed_to": ["fixture"], "tags": ["personal"], "preset_ids": ["preset-a"]}
            self.records.append(record)
            self.write_metadata(name)

    def record(self, name):
        return next(record for record in self.records if record["name"] == name)

    def write_metadata(self, name, **source_changes):
        record = self.record(name)
        source = {"type": record["source_type"], "ref": record["source_ref"],
                  "subpath": "skills/" + name, "branch": "main", **source_changes}
        (self.metadata / (record["id"] + ".json")).write_text(json.dumps({
            "skill_id": record["id"], "path": name, "source": source}), encoding="utf-8")

    def __call__(self, cli, *args):
        self.calls.append(args)
        return {("repo", "status"): {"skills_dir": str(self.library), "metadata_dir": str(self.metadata.parent)},
                ("skills", "list"): self.records, ("agents", "list"): self.agents}[args]

    def copy_source(self, root):
        for name in self.case.package.discover():
            target = root / name
            if target.is_dir():
                shutil.rmtree(target)
            shutil.copytree(self.case.source / "skills" / name, target)


class ManagerChecks(PackageFixture):
    def setUp(self):
        super().setUp()
        self.fake = FakeManager(self)

    def preflight(self):
        with patch.object(manager, "manager_json", side_effect=self.fake):
            return self.package.preflight("fixture", self.revision)

    def confirm(self, plan):
        with patch.object(manager, "manager_json", side_effect=self.fake):
            return self.package.confirm_install("fixture", self.revision, plan)

    def change_source(self):
        (self.source / "skills/first/references/guide.md").unlink()
        self.write("skills/first/references/new.md", "New guide\n")
        self.revision = self.commit("move resource")

    def test_real_add_move_delete_reaches_all_files_and_checks_only_query(self):
        self.change_source()
        plan = self.preflight()
        self.fake.copy_source(self.fake.library)
        self.fake.copy_source(self.fake.agent_root)
        result = self.confirm(plan)
        self.assertEqual(result["status"], "installation_verified")
        self.assertEqual(result["revision"], self.revision)
        self.assertEqual(result["deployments"]["first"], ["fixture"])
        self.assertTrue(all(args in {( "repo", "status"), ("skills", "list"), ("agents", "list")}
                            for args in self.fake.calls))

    def test_stale_library_or_noop_update_cannot_pass(self):
        self.change_source()
        plan = self.preflight()
        with self.assertRaisesRegex(manager.PackageError, "library differs"):
            self.confirm(plan)

    def test_extra_resource_after_held_back_removal_cannot_pass(self):
        self.change_source()
        plan = self.preflight()
        self.fake.copy_source(self.fake.library)
        (self.fake.library / "first/references/guide.md").write_text("old", encoding="utf-8")
        with self.assertRaises(manager.PackageError):
            self.confirm(plan)

    def test_failed_deployment_and_missing_target_cannot_pass(self):
        self.change_source()
        plan = self.preflight()
        self.fake.copy_source(self.fake.library)
        with self.assertRaisesRegex(manager.PackageError, "stale"):
            self.confirm(plan)
        shutil.rmtree(self.fake.agent_root / "first")
        with self.assertRaises(manager.PackageError):
            self.confirm(plan)

    def test_unknown_edits_are_preserved_in_library_and_agent(self):
        for root in (self.fake.library, self.fake.agent_root):
            target = root / "first/references/guide.md"
            original = target.read_bytes()
            target.write_bytes(b"unique local edit\n")
            with self.subTest(root=root), self.assertRaisesRegex(manager.PackageError, "edits preserved"):
                self.preflight()
            self.assertEqual(target.read_bytes(), b"unique local edit\n")
            target.write_bytes(original)

    def test_extra_untracked_sensitive_file_blocks_update_without_exposing_contents(self):
        target = self.fake.library / "first/.env"
        target.write_text("fixture-only-secret", encoding="utf-8")
        with self.assertRaises(manager.PackageError) as error:
            self.preflight()
        self.assertNotIn("fixture-only-secret", str(error.exception))
        self.assertEqual(target.read_text(), "fixture-only-secret")

    def test_missing_entry_with_unique_files_is_not_treated_as_absent(self):
        target = self.fake.agent_root / "first"
        (target / "SKILL.md").unlink()
        with self.assertRaises(manager.PackageError):
            self.preflight()
        self.assertTrue((target / "references/guide.md").exists())

    def test_missing_agent_target_can_be_repaired_but_not_marked_done(self):
        shutil.rmtree(self.fake.agent_root / "first")
        plan = self.preflight()
        with self.assertRaises(manager.PackageError):
            self.confirm(plan)
        self.assertFalse((self.fake.agent_root / "first").exists())
        self.fake.copy_source(self.fake.agent_root)
        self.confirm(plan)

    def test_foreign_link_is_preserved(self):
        target = self.fake.agent_root / "first"
        shutil.rmtree(target)
        link_directory(self.source / "skills/first", target)
        with self.assertRaisesRegex(manager.PackageError, "Foreign"):
            self.preflight()
        self.assertEqual(target.resolve(), (self.source / "skills/first").resolve())

    def test_correct_link_and_library_only_are_valid(self):
        target = self.fake.agent_root / "first"
        shutil.rmtree(target)
        link_directory(self.fake.library / "first", target)
        self.fake.record("improve-workflow")["deployed_to"] = []
        result = self.confirm(self.preflight())
        self.assertEqual(result["deployments"]["improve-workflow"], [])

    def test_nested_link_cannot_escape_resource_tree(self):
        link_directory(self.source / "skills/first", self.fake.library / "first/escape")
        with self.assertRaisesRegex(manager.PackageError, "Linked skill resource"):
            self.preflight()

    def test_sources_metadata_and_default_branch_are_checked(self):
        record = self.fake.record("first")
        original = record["source_ref"]
        record["source_ref"] = "https://example.invalid/foreign"
        with self.assertRaises(manager.PackageError):
            self.preflight()
        record["source_ref"] = original
        for changes in ({"branch": "other"}, {"subpath": "skills/other"}, {"ref": "foreign"}):
            self.fake.write_metadata("first", **changes)
            with self.subTest(changes=changes), self.assertRaises(manager.PackageError):
                self.preflight()
        git(self.source, "push", "origin", "main")
        self.fake.write_metadata("first", branch=None, subpath="skills\\first")
        self.confirm(self.preflight())

    def test_group_install_reference_is_valid_with_exact_metadata(self):
        self.fake.record("first")["source_ref"] = self.package.policy["remote"].removesuffix(".git") + "/tree/main/skills"
        self.fake.write_metadata("first")
        self.confirm(self.preflight())

    def test_metadata_without_files_cannot_pass(self):
        plan = self.preflight()
        (self.fake.library / "first/SKILL.md").unlink()
        with self.assertRaises(manager.PackageError):
            self.confirm(plan)

    def test_all_existing_identity_and_deployment_choices_must_match(self):
        plan = self.preflight()
        for key, value in (("id", "changed-id"), ("tags", []), ("preset_ids", []),
                           ("deployed_to", []), ("deployed_to", ["fixture", "unapproved"])):
            record = self.fake.record("first")
            original = copy.deepcopy(record[key])
            record[key] = value
            self.fake.write_metadata("first")
            with self.subTest(key=key, value=value), self.assertRaises(manager.PackageError):
                self.confirm(plan)
            record[key] = original
            self.fake.write_metadata("first")

    def test_new_skill_defaults_to_library_only_and_unmanaged_files_are_preserved(self):
        self.add_skill("new-skill")
        self.revision = self.commit("new skill")
        plan = self.preflight()
        self.assertIsNone(plan["skills"]["new-skill"]["id"])
        self.assertEqual(plan["skills"]["new-skill"]["deployed_to"], [])
        (self.fake.library / "new-skill").mkdir()
        with self.assertRaisesRegex(manager.PackageError, "Unmanaged"):
            self.preflight()

    def test_plan_must_match_revision_source_library_and_skill_set(self):
        plan = self.preflight()
        for key, value in (("revision", "0" * 40), ("source", "other"), ("library", "other"),
                           ("skills", {}), ("status", "not-a-preflight")):
            invalid = {**plan, key: value}
            with self.subTest(key=key), self.assertRaises(manager.PackageError):
                self.confirm(invalid)

    def test_new_skill_can_be_verified_without_expanding_deployment(self):
        self.add_skill("new-skill")
        self.revision = self.commit("new skill")
        plan = self.preflight()
        self.fake.copy_source(self.fake.library)
        self.fake.records.append({"id": "new-opaque-id", "name": "new-skill",
                                  "path": str(self.fake.library / "new-skill"), "source_type": "git",
                                  "source_ref": self.package.policy["remote"],
                                  "tags": [], "preset_ids": [], "deployed_to": []})
        self.fake.write_metadata("new-skill")
        result = self.confirm(plan)
        self.assertEqual(result["deployments"]["new-skill"], [])
        self.assertFalse((self.fake.agent_root / "new-skill").exists())
        self.fake.record("new-skill")["deployed_to"] = ["fixture"]
        with self.assertRaisesRegex(manager.PackageError, "choices changed"):
            self.confirm(plan)
        plan["skills"]["new-skill"]["deployed_to"] = ["fixture"]
        shutil.copytree(self.fake.library / "new-skill", self.fake.agent_root / "new-skill")
        self.assertEqual(self.confirm(plan)["deployments"]["new-skill"], ["fixture"])

    def test_unknown_agents_and_duplicate_names_are_rejected(self):
        self.fake.record("first")["deployed_to"] = ["unregistered"]
        with self.assertRaisesRegex(manager.PackageError, "Unknown managed"):
            self.preflight()
        self.fake.record("first")["deployed_to"] = ["fixture"]
        self.fake.records.append(dict(self.fake.record("first")))
        with self.assertRaisesRegex(manager.PackageError, "Ambiguous"):
            self.preflight()

    def test_incomplete_selection_cannot_disable_choice_protection(self):
        plan = self.preflight()
        plan["skills"]["first"] = {}
        self.fake.record("first")["deployed_to"] = []
        with self.assertRaises(manager.PackageError):
            self.confirm(plan)

    def test_text_line_endings_match_but_binary_bytes_are_exact(self):
        self.write("skills/first/notes.txt", "one\ntwo\n")
        (self.source / "skills/first/image.md").write_bytes(b"one\r\ntwo\x00")
        self.revision = self.commit("binary and text resources")
        self.fake.copy_source(self.fake.library)
        self.fake.copy_source(self.fake.agent_root)
        (self.fake.agent_root / "first/notes.txt").write_bytes(b"one\r\ntwo\r\n")
        plan = self.preflight()
        self.confirm(plan)
        (self.fake.agent_root / "first/image.md").write_bytes(b"one\ntwo\x00")
        with self.assertRaises(manager.PackageError):
            self.confirm(plan)

    def test_cli_checks_leave_files_index_and_state_unchanged(self):
        before = {path.relative_to(self.home).as_posix(): path.read_bytes()
                  for path in self.home.rglob("*") if path.is_file()}
        output = io.StringIO()
        with patch.object(sys, "argv", ["skill_package.py", "preflight", "--source", str(self.source),
                          "--revision", self.revision, "--skills-manager-cli", "fixture"]), \
                patch.object(manager, "manager_json", side_effect=self.fake), contextlib.redirect_stdout(output):
            self.assertEqual(manager.main(), 0)
        plan = json.loads(output.getvalue())
        plan_path = self.home / "preflight.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        with patch.object(sys, "argv", ["skill_package.py", "confirm-install", "--source", str(self.source),
                          "--revision", self.revision, "--skills-manager-cli", "fixture", "--plan", str(plan_path)]), \
                patch.object(manager, "manager_json", side_effect=self.fake), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(manager.main(), 0)
        after = {path.relative_to(self.home).as_posix(): path.read_bytes()
                 for path in self.home.rglob("*") if path.is_file() and path != plan_path}
        self.assertEqual(after, before)
