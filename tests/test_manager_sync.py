"""Skills Manager bridge transactions against local Git and a file-backed fake CLI."""
import importlib.util
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("package_transaction_fixtures", Path(__file__).with_name("test_skill_package.py"))
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
manager = fixtures.manager
git = fixtures.git


class FakeManager:
    """Mutations really change fixture files; registry alone cannot pass confirmation."""
    def __init__(self, case):
        self.case = case
        self.library, self.agents, self.read = case.managed_fixture()
        self.records = self.read("fixture", "skills", "list")
        self.agent_records = self.read("fixture", "agents", "list")
        self.metadata = Path(self.read("fixture", "repo", "status")["metadata_dir"]) / "skills"
        self.calls = []
        self.fail = None
        self.fail_name = None
        self.held_back = False
        self.noop_update = False

    def record(self, name):
        return next(record for record in self.records if record["name"] == name)

    def unlink(self, entry):
        if manager.linked(entry):
            if entry.is_symlink():
                entry.unlink()
            else:
                entry.rmdir()
        elif entry.exists():
            shutil.rmtree(entry)

    def copy_current(self, name, preserve_removals=False):
        target = self.library / name
        if not preserve_removals:
            self.unlink(target)
        shutil.copytree(self.case.source / "skills" / name, target, dirs_exist_ok=preserve_removals)

    def __call__(self, cli, *args):
        self.calls.append(args)
        if args[:2] == ("agents", "list"):
            return self.agent_records
        if args[:2] in (("repo", "status"), ("skills", "list")):
            return self.read(cli, *args)
        action = args[1]
        if (self.fail == action and "--dry-run" not in args
                and (self.fail_name is None or args[2] == self.fail_name)):
            raise manager.PackageError("fixture " + action + " failed")
        if action == "check":
            return {"updates": [{"name": r["name"], "id": r["id"], "has_update": True} for r in self.records]}
        if action == "update":
            if not self.noop_update:
                selected = args[2] if len(args) > 2 and not args[2].startswith("--") else None
                for record in self.records:
                    if selected is None or selected in (record["name"], record["id"]):
                        installed = self.library / record["name"]
                        source = self.case.source / "skills" / record["name"]
                        removed = {p.relative_to(installed) for p in installed.rglob("*") if p.is_file()} - {p.relative_to(source) for p in source.rglob("*") if p.is_file()}
                        if not self.held_back or removed:
                            self.copy_current(record["name"], preserve_removals=self.held_back)
            return {"updated": [] if self.held_back else [r["name"] for r in self.records],
                    "held_back_removals": ["fixture-removal"] if self.held_back else []}
        if action == "install":
            reference = args[2]
            name = reference.rstrip("/").split("/")[-1]
            self.copy_current(name)
            record = {"id": "new-" + name, "name": name, "path": str(self.library / name),
                      "source_type": "git", "source_ref": reference, "deployed_to": []}
            self.records.append(record)
            manager.write_json(self.metadata / (record["id"] + ".json"), {
                "skill_id": record["id"], "path": name, "source": {
                    "type": "git", "ref": reference, "subpath": "skills/" + name, "branch": "main"}})
            return {"installed": [name], "skill": record}
        if action == "deploy":
            if "--dry-run" in args:
                return {"conflicts": [], "plan": []}
            name = args[2]
            record = next(r for r in self.records if name in (r["id"], r["name"]))
            keys = [args[index + 1] for index, value in enumerate(args) if value == "--agent"]
            for key in keys:
                agent = next(a for a in self.agent_records if a["key"] == key)
                target = Path(agent["skills_dir"]) / record["name"]
                self.unlink(target)
                manager.link_directory(self.library / record["name"], target)
                if key not in record["deployed_to"]:
                    record["deployed_to"].append(key)
            return {"deployed": [record["name"]]}
        raise AssertionError("Unexpected fake CLI command: " + repr(args))


class ManagerSync(unittest.TestCase):
    # Share only fixture setup/helpers, never inherit the old test methods.
    setUpClass = classmethod(fixtures.Transactions.setUpClass.__func__)
    setUp = fixtures.Transactions.setUp
    write = fixtures.Transactions.write
    add_skill = fixtures.Transactions.add_skill
    commit = fixtures.Transactions.commit
    prepare = fixtures.Transactions.prepare
    candidate = fixtures.Transactions.candidate
    managed_fixture = fixtures.Transactions.managed_fixture

    def published_skill_change(self, run="trial", suffix="updated"):
        worktree = self.prepare(run)
        path = worktree / "skills/first/SKILL.md"
        path.write_text(path.read_text(encoding="utf-8") + suffix + "\n", encoding="utf-8")
        self.package.verify(run)
        self.commit(worktree, run)
        self.package.publish(run)
        return worktree

    def sync_fake(self, fake, run=None, **kwargs):
        with patch.object(manager, "manager_json", side_effect=fake):
            return self.package.sync_manager("fixture-cli", run, **kwargs)

    def published_resource_change(self, copied_deployment=False):
        # Payloads are candidate resources; Git and all installs stay in this fixture.
        old = (fixtures.ROOT / "skills/setup-solo-workflow/references/document-maintenance.md").read_bytes()
        added = (fixtures.ROOT / "skills/improve-workflow/references/package-operations.md").read_bytes()
        for path, content in (("references/old.md", old), ("references/obsolete.md", old)):
            target = self.source / "skills/first" / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        self.commit(self.source, "resource baseline")
        git(self.source, "push", "origin", "main")
        fake = FakeManager(self)
        if copied_deployment:
            fake.unlink(fake.agents / "first")
            shutil.copytree(fake.library / "first", fake.agents / "first")
        worktree = self.prepare()
        (worktree / "skills/first/references/old.md").rename(worktree / "skills/first/references/execution.md")
        (worktree / "skills/first/references/obsolete.md").unlink()
        (worktree / "skills/first/references/added.md").write_bytes(added)
        self.commit(worktree, "move add remove real references")
        self.package.verify("trial")
        self.package.publish("trial")
        return fake, old, added

    def assert_current_resources(self, root, old, added):
        self.assertEqual((root / "first/references/execution.md").read_bytes(), old)
        self.assertEqual((root / "first/references/added.md").read_bytes(), added)
        self.assertFalse((root / "first/references/old.md").exists())
        self.assertFalse((root / "first/references/obsolete.md").exists())

    def test_real_resource_move_add_delete_reaches_library_and_deployment(self):
        fake, old, added = self.published_resource_change(copied_deployment=True)
        self.assertEqual(self.sync_fake(fake, "trial")["status"], "synced")
        for root in (fake.library, fake.agents):
            self.assert_current_resources(root, old, added)
        state = self.package.load_run("trial")[1]
        frozen = Path(state["runtime"]).parents[1]
        self.assertEqual((frozen / "skills/first/references/old.md").read_bytes(), old)
        self.assertFalse((frozen / "skills/first/references/execution.md").exists())

    def test_real_resource_held_back_removal_is_visible_and_cannot_close(self):
        fake, old, added = self.published_resource_change()
        fake.held_back = True
        with self.assertRaises(manager.PackageError):
            self.sync_fake(fake, "trial")
        self.assertEqual((fake.library / "first/references/obsolete.md").read_bytes(), old)
        self.assertEqual((fake.library / "first/references/added.md").read_bytes(), added)
        self.assertEqual(self.package.load_run("trial")[1]["status"], "source_synced")
        fake.held_back = False
        # A mixed tree needs explicit reconciliation; an ordinary retry must preserve it.
        with self.assertRaises(manager.PackageError):
            self.sync_fake(fake, "trial")
        self.assertEqual((fake.library / "first/references/obsolete.md").read_bytes(), old)
        self.assertEqual(self.package.load_run("trial")[1]["status"], "source_synced")

    def test_real_resource_noop_update_preserves_old_files_and_cannot_close(self):
        fake, old, added = self.published_resource_change()
        fake.noop_update = True
        with self.assertRaises(manager.PackageError):
            self.sync_fake(fake, "trial")
        self.assertEqual((fake.library / "first/references/old.md").read_bytes(), old)
        self.assertFalse((fake.library / "first/references/added.md").exists())
        self.assertEqual(self.package.load_run("trial")[1]["status"], "source_synced")
        fake.noop_update = False
        self.assertEqual(self.sync_fake(fake, "trial")["status"], "synced")
        self.assert_current_resources(fake.agents, old, added)

    def test_real_resource_deploy_failure_keeps_old_agent_files_until_retry(self):
        fake, old, added = self.published_resource_change(copied_deployment=True)
        fake.fail = "deploy"
        with self.assertRaises(manager.PackageError):
            self.sync_fake(fake, "trial")
        self.assert_current_resources(fake.library, old, added)
        self.assertEqual((fake.agents / "first/references/old.md").read_bytes(), old)
        self.assertFalse((fake.agents / "first/references/execution.md").exists())
        self.assertEqual(self.package.load_run("trial")[1]["status"], "source_synced")
        fake.fail = None
        self.assertEqual(self.sync_fake(fake, "trial")["status"], "synced")
        self.assert_current_resources(fake.agents, old, added)

    def test_two_independent_runs_publish_integrate_and_sync_without_loss(self):
        fake = FakeManager(self)
        one = self.candidate("one", "one.txt")
        two = self.candidate("two", "two.txt")
        self.package.publish("one")
        self.assertEqual(self.sync_fake(fake, "one")["status"], "synced")
        self.assertEqual(self.package.publish("two")["status"], "needs_verification")
        self.package.verify("two")
        self.package.publish("two")
        self.assertEqual(self.sync_fake(fake, "two")["status"], "synced")
        for root in (self.source, two):
            self.assertEqual((root / "one.txt").read_text(), "one\n")
            self.assertEqual((root / "two.txt").read_text(), "two\n")
        self.assertEqual((one / "one.txt").read_text(), "one\n")
        self.assertEqual(git(self.source, "rev-parse", "HEAD"), git(self.source, "ls-remote", "origin", "refs/heads/main").split()[0])

    def test_conflicting_run_remains_preserved_after_first_sync(self):
        fake = FakeManager(self)
        one = self.candidate("one", "shared.txt")
        two = self.candidate("two", "shared.txt")
        self.package.publish("one")
        self.sync_fake(fake, "one")
        self.assertEqual(self.package.publish("two")["status"], "conflict")
        self.assertEqual((one / "shared.txt").read_text(), "one\n")
        self.assertIn("<<<<<<<", (two / "shared.txt").read_text())
        self.assertEqual(self.package.load_run("two")[1]["status"], "conflict")

    def test_update_failure_stays_pending_and_retry_completes(self):
        fake = FakeManager(self)
        self.published_skill_change()
        fake.fail = "update"
        with self.assertRaises(manager.PackageError):
            self.sync_fake(fake, "trial")
        self.assertEqual(self.package.load_run("trial")[1]["status"], "source_synced")
        fake.fail = None
        self.assertEqual(self.sync_fake(fake, "trial")["status"], "synced")

    def test_deployment_failure_stays_pending_and_retry_completes(self):
        fake = FakeManager(self)
        target = fake.agents / "first"
        fake.unlink(target)
        shutil.copytree(fake.library / "first", target)
        self.published_skill_change()
        fake.fail = "deploy"
        with self.assertRaises(manager.PackageError):
            self.sync_fake(fake, "trial")
        self.assertEqual(self.package.load_run("trial")[1]["status"], "source_synced")
        fake.fail = None
        self.assertEqual(self.sync_fake(fake, "trial")["status"], "synced")
        self.assertTrue(manager.linked(target))

    def test_held_back_removals_and_noop_updates_cannot_close_run(self):
        for mode in ("held_back", "noop_update"):
            with self.subTest(mode=mode):
                fake = FakeManager(self) if mode == "held_back" else fake
                if mode == "held_back":
                    self.published_skill_change()
                fake.held_back = mode == "held_back"
                fake.noop_update = mode == "noop_update"
                with self.assertRaises(manager.PackageError):
                    self.sync_fake(fake, "trial")
                self.assertEqual(self.package.load_run("trial")[1]["status"], "source_synced")
        fake.noop_update = False
        self.assertEqual(self.sync_fake(fake, "trial")["status"], "synced")

    def test_metadata_without_real_deployment_fails_confirmation(self):
        fake = FakeManager(self)
        fake.unlink(fake.agents / "first")
        with patch.object(manager, "manager_json", side_effect=fake), self.assertRaises(manager.PackageError):
            self.package.confirm_install("fixture-cli")

    def test_unknown_library_edit_is_rejected_before_any_update(self):
        fake = FakeManager(self)
        self.published_skill_change()
        (fake.library / "improve-workflow/SKILL.md").write_text("unknown local work", encoding="utf-8")
        with self.assertRaises(manager.PackageError):
            self.sync_fake(fake, "trial")
        self.assertFalse(any(args[1] in ("update", "install", "deploy") for args in fake.calls))
        self.assertEqual((fake.library / "improve-workflow/SKILL.md").read_text(), "unknown local work")

    def test_existing_ids_and_only_existing_deployment_agents_are_preserved(self):
        fake = FakeManager(self)
        record = fake.record("first")
        metadata_path = fake.metadata / (record["id"] + ".json")
        metadata = manager.read_json(metadata_path)
        metadata_path.unlink()
        record["id"] = "opaque-existing-id"
        record["preset_ids"] = ["personal-preset"]
        record["tags"] = ["personal-tag"]
        metadata["skill_id"] = record["id"]
        manager.write_json(fake.metadata / (record["id"] + ".json"), metadata)
        old_id = record["id"]
        second = self.home / "second-agent/skills"
        second.mkdir(parents=True)
        fake.agent_records.append({"key": "second", "skills_dir": str(second)})
        fake.unlink(fake.agents / "first")
        shutil.copytree(fake.library / "first", fake.agents / "first")
        shutil.copytree(fake.library / "first", second / "first")
        record["deployed_to"].append("second")
        unused = self.home / "unused-agent/skills"
        unused.mkdir(parents=True)
        fake.agent_records.append({"key": "unused", "skills_dir": str(unused)})
        self.published_skill_change()
        self.sync_fake(fake, "trial")
        self.assertEqual(record["id"], old_id)
        self.assertEqual(record["preset_ids"], ["personal-preset"])
        self.assertEqual(record["tags"], ["personal-tag"])
        self.assertTrue(any(args[:3] == ("skills", "update", old_id) for args in fake.calls))
        self.assertEqual(set(record["deployed_to"]), {"fixture", "second"})
        self.assertFalse((unused / "first").exists())
        deploys = [args for args in fake.calls if args[1] == "deploy"]
        self.assertTrue(any("--dry-run" in args for args in deploys))

    def test_text_line_endings_are_equivalent_but_binary_bytes_are_exact(self):
        self.write("skills/first/notes.txt", "one\ntwo\n")
        (self.source / "skills/first/image.bin").write_bytes(b"one\r\ntwo\x00")
        self.commit(self.source, "text and binary fixtures")
        git(self.source, "push", "origin", "main")
        fake = FakeManager(self)
        fake.unlink(fake.agents / "first")
        shutil.copytree(fake.library / "first", fake.agents / "first")
        (fake.agents / "first/notes.txt").write_bytes(b"one\r\ntwo\r\n")
        with patch.object(manager, "manager_json", side_effect=fake):
            self.assertEqual(self.package.confirm_install("fixture-cli")["status"], "synced")
        (fake.agents / "first/image.bin").write_bytes(b"one\ntwo\x00")
        with patch.object(manager, "manager_json", side_effect=fake), self.assertRaises(manager.PackageError):
            self.package.confirm_install("fixture-cli")

    def test_new_skill_installs_exact_tree_and_defaults_to_library_only(self):
        fake = FakeManager(self)
        worktree = self.prepare()
        self.add_skill(worktree, "new-skill")
        self.package.verify("trial")
        self.commit(worktree, "new skill")
        self.package.publish("trial")
        self.sync_fake(fake, "trial")
        record = fake.record("new-skill")
        self.assertEqual(record["source_ref"], self.package.policy["remote"].removesuffix(".git") + "/tree/main/skills/new-skill")
        self.assertEqual(record["deployed_to"], [])
        self.assertFalse((fake.agents / "new-skill").exists())

    def test_new_skill_explicitly_deploys_to_selected_agent(self):
        fake = FakeManager(self)
        worktree = self.prepare()
        self.add_skill(worktree, "new-skill")
        self.package.verify("trial")
        self.commit(worktree, "new skill")
        self.package.publish("trial")
        self.sync_fake(fake, "trial", deploy_new_to=("fixture",))
        self.assertEqual(fake.record("new-skill")["deployed_to"], ["fixture"])
        self.assertTrue((fake.agents / "new-skill/SKILL.md").is_file())


    def test_new_skill_deployment_intent_survives_run_retry_without_flags(self):
        fake = FakeManager(self)
        worktree = self.prepare()
        self.add_skill(worktree, "new-skill")
        self.package.verify("trial")
        self.commit(worktree, "new skill")
        self.package.publish("trial")
        fake.fail = "deploy"
        fake.fail_name = "new-skill"
        with self.assertRaises(manager.PackageError):
            self.sync_fake(fake, "trial", deploy_new_to=("fixture",))
        self.assertEqual(self.package.load_run("trial")[1]["status"], "source_synced")
        self.assertEqual(fake.record("new-skill")["deployed_to"], [])
        self.assertTrue((fake.library / "new-skill/SKILL.md").is_file())
        with patch.object(manager, "manager_json", side_effect=fake), self.assertRaises(manager.PackageError):
            self.package.confirm_install("fixture-cli", "trial")
        self.assertEqual(self.package.load_run("trial")[1]["status"], "source_synced")
        fake.fail = None
        result = self.sync_fake(fake, "trial")
        self.assertEqual(result["status"], "synced")
        self.assertEqual(self.package.load_run("trial")[1]["status"], "synced")
        self.assertEqual(fake.record("new-skill")["deployed_to"], ["fixture"])
        self.assertTrue((fake.agents / "new-skill/SKILL.md").is_file())
        self.assertEqual(sum(args[1] == "install" for args in fake.calls), 1)

    def test_new_skill_deployment_intent_survives_no_run_retry_without_flags(self):
        fake = FakeManager(self)
        self.add_skill(self.source, "new-skill")
        self.commit(self.source, "new skill")
        git(self.source, "push", "origin", "main")
        fake.fail = "deploy"
        fake.fail_name = "new-skill"
        with self.assertRaises(manager.PackageError):
            self.sync_fake(fake, deploy_new_to=("fixture",))
        self.assertEqual(fake.record("new-skill")["deployed_to"], [])
        self.assertTrue((fake.library / "new-skill/SKILL.md").is_file())
        fake.fail = None
        result = self.sync_fake(fake)
        self.assertEqual(result["status"], "synced")
        self.assertEqual(fake.record("new-skill")["deployed_to"], ["fixture"])
        self.assertTrue((fake.agents / "new-skill/SKILL.md").is_file())
        self.assertEqual(sum(args[1] == "install" for args in fake.calls), 1)


class ResourceBytes(unittest.TestCase):
    def test_binary_payload_in_text_extension_preserves_exact_bytes(self):
        first = b"one\r\ntwo\x00"
        second = b"one\ntwo\x00"
        self.assertNotEqual(manager.resource_bytes(Path("binary.txt"), first, normalize_text=True),
                            manager.resource_bytes(Path("binary.txt"), second, normalize_text=True))


if __name__ == "__main__":
    unittest.main()
