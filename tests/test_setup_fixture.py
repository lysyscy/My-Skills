import tempfile
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import unittest

from setup_fixture import check, check_migration, consume, git, prepare, prepare_migration, put, read, summary


class SetupFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="setup-fixture-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "exercise"
        self.skill = Path(__file__).resolve().parents[1] / "skills/setup-solo-workflow/SKILL.md"
        prepare(self.root, self.skill)

    def test_original_material_and_dirty_state_are_valid(self):
        self.assertTrue(check(self.root)["passed"])
        status = git(self.root / "dirty", "status", "--short")
        self.assertIn("docs/product.md", status)
        self.assertIn("docs/new-requirement.md", status)
        self.assertIn("inbox/", status)
        with self.assertRaises(ValueError):
            prepare(self.root, self.skill)

    def test_detects_business_history_and_untracked_damage(self):
        for case, path in (("existing", ".scratch/old/issues/01.md"),
                           ("dirty", "inbox/supplier-note.txt"),
                           ("dirty", "docs/new-requirement.md")):
            (self.root / case / path).unlink()
        errors = check(self.root)["errors"]
        self.assertEqual(sum("protected content" in error for error in errors), 3)

    def test_repeated_setup_cannot_introduce_churn(self):
        put(self.root / "repeat", "AGENTS.md", "Rewritten unnecessarily\n")
        put(self.root / "repeat", "docs/agents/extra.md", "Duplicate ledger\n")
        errors = check(self.root)["errors"]
        self.assertTrue(any("AGENTS.md" in error for error in errors))
        self.assertTrue(any("extra.md" in error for error in errors))

    def test_new_product_files_and_commits_are_rejected(self):
        project = self.root / "existing"
        put(project, "src/new.js", "Unrequested implementation\n")
        git(project, "add", ".")
        git(project, "commit", "-qm", "Unrequested commit")
        errors = check(self.root)["errors"]
        self.assertTrue(any("unauthorized commit" in error for error in errors))
        self.assertTrue(any("src/new.js" in error for error in errors))

    def test_checks_actual_new_link_targets(self):
        project = self.root / "existing"
        put(project, "docs/agents/workflow.md", "[Missing](absent.md)\n")
        self.assertFalse(check(self.root)["passed"])
        put(project, "docs/agents/workflow.md", "[Requirements](../product.md)\n")
        self.assertTrue(check(self.root)["passed"])

    def test_detects_empty_future_directories_and_lost_intent_to_add(self):
        (self.root / "existing/.scratch/future/issues").mkdir(parents=True)
        git(self.root / "dirty", "reset", "-q", "--", "docs/new-requirement.md")
        errors = check(self.root)["errors"]
        self.assertTrue(any("unexpected new directory" in error for error in errors))
        self.assertTrue(any("protected index changed: docs/new-requirement.md" in error for error in errors))

    def test_new_empty_binding_directory_is_rejected(self):
        (self.root / "existing/docs/agents/future/issues").mkdir(parents=True)
        self.assertFalse(check(self.root)["passed"])
        put(self.root / "existing", "docs/agents/future/issues/binding.md", "[Requirements](../../../product.md)\n")
        self.assertTrue(check(self.root)["passed"])

    def test_measures_actual_selected_reads_and_repetition(self):
        path = self.root / "existing" / "docs/product.md"
        text = read(self.root, path, 1, 1)
        read(self.root, path, 1, 1)
        totals = summary(self.root)
        self.assertEqual(totals["reads"], 2)
        self.assertEqual(totals["output_bytes"], len(text.encode("utf-8")) * 2)
        self.assertEqual(totals["repeated_identical_reads"], 1)
        self.assertGreaterEqual(totals["read_seconds"], 0)

    def test_long_read_is_bounded_and_can_continue_without_losing_content(self):
        path = self.root / "existing/.scratch/old/spec.md"
        preview = read(self.root, path)
        self.assertLess(len(preview), 2200)
        self.assertIn("next_offset=2000", preview)
        first = read(self.root, path, offset=0, limit=20).split("\n[partial", 1)[0]
        second = read(self.root, path, offset=20, limit=20).split("\n[partial", 1)[0]
        self.assertEqual(first + second, path.read_text(encoding="utf-8")[:40])
        with self.assertRaises(ValueError):
            read(self.root, path, start=0)


class MigrationFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="migration-fixture-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "exercise"
        self.package = Path(__file__).resolve().parents[1]
        self.skill = self.package / "skills/setup-solo-workflow/SKILL.md"
        prepare_migration(self.root, self.skill)
        self.manifest = json.loads((self.root / "migration.json").read_text(encoding="utf-8"))

    def migrate(self):
        for name, entries in self.manifest["cases"].items():
            project = self.root / name
            for entry in entries:
                source, target = project / entry["source"], project / entry["target"]
                target.parent.mkdir(parents=True, exist_ok=True)
                if entry["action"] == "delete":
                    source.unlink()
                else:
                    source.rename(target)
            put(project, "consumer.json", '{"requirements_glob":"docs/requirements.md"}\n')
            put(project, "AGENTS.md", "现行业务 [需求](docs/requirements.md)；活任务 .scratch/current/spec.md。\n")
            put(project, "docs/agents/workflow.md", "现行权威 [需求](../requirements.md)，历史 [决定](../archive/old-decision.md)。\n")
        self.manifest.update(migration_authorized=True, archive_authorized=True, delete_authorized=True)

    def test_authorized_migration_reads_same_content_and_has_recovery_evidence(self):
        originals = {name: next(iter(consume(self.root / name).values())) for name in self.manifest["cases"]}
        self.migrate()
        self.assertTrue(check_migration(self.root, self.manifest)["passed"])
        state = json.loads((self.root / "state.json").read_text(encoding="utf-8"))
        for name, original in originals.items():
            project = self.root / name
            self.assertEqual(consume(project), {"docs/requirements.md": original})
            self.assertEqual((self.root / "rollback" / name / "docs/product.md").read_bytes(), original)
            self.assertEqual(git(project, "rev-parse", "HEAD"), state["cases"][name]["head"])
            self.assertIn("未提交裁定", original.decode("utf-8"))
            self.assertIn("docs/pending.md", state["cases"][name]["index"])
        self.assertFalse((self.root / "materials/src").exists())
        self.assertFalse((self.root / "materials/package.json").exists())
        # Fixture business commands live only in the simulated software project.
        self.assertNotIn("node --test", (self.root / "materials/docs/agents/workflow.md").read_text(encoding="utf-8"))

    def test_migration_and_archive_and_deletion_need_separate_authorization(self):
        self.migrate()
        for flag, action in (("migration_authorized", "move"), ("archive_authorized", "archive"), ("delete_authorized", "delete")):
            self.manifest[flag] = False
            self.assertTrue(any(f"{action} authorization" in e for e in check_migration(self.root, self.manifest)["errors"]))
            self.manifest[flag] = True

    def test_valid_markdown_links_do_not_prove_old_glob_consumes_requirements(self):
        self.migrate()
        project = self.root / "software"
        put(project, "consumer.json", '{"requirements_glob":"docs/product*.md"}\n')
        self.assertEqual(consume(project), {})
        self.assertTrue(any("actual glob consumer" in e for e in check_migration(self.root, self.manifest)["errors"]))

    def test_approved_manifest_cannot_expand_into_activity_or_unique_data(self):
        self.migrate()
        self.manifest["cases"]["software"].append({"source": ".scratch/current/spec.md", "target": "docs/requirements.md", "action": "delete"})
        (self.root / "software/.scratch/current/spec.md").unlink()
        errors = check_migration(self.root, self.manifest)["errors"]
        self.assertTrue(any("scope differs" in e for e in errors))
        self.assertTrue(any("protected content changed: .scratch/current/spec.md" in e for e in errors))

    def test_detects_adr_active_issue_untracked_ita_and_index_damage(self):
        self.migrate()
        project = self.root / "software"
        for path in ("docs/adr/0001-authority.md", ".scratch/current/issues/01.md", "inbox/original.txt", "docs/pending.md"):
            (project / path).unlink()
        git(project, "reset", "-q", "--", "docs/pending.md")
        errors = check_migration(self.root, self.manifest)["errors"]
        self.assertEqual(sum("protected content changed" in e for e in errors), 4)
        self.assertTrue(any("protected index changed" in e for e in errors))

    def test_content_loss_stale_entry_empty_categories_and_bad_recovery_fail(self):
        self.migrate()
        project = self.root / "materials"
        put(project, "docs/requirements.md", "Lost an independent uncommitted decision.\n")
        put(project, "AGENTS.md", "旧入口 docs/product.md\n")
        (project / "docs/operations").mkdir()
        (self.root / "rollback/materials/git-index").unlink()
        put(self.root / "rollback/materials", "docs/product.md", "Lost backup\n")
        errors = check_migration(self.root, self.manifest)["errors"]
        for expected in ("content conservation", "retired ordinary entry", "empty category", "rollback index", "rollback original"):
            self.assertTrue(any(expected in e for e in errors), errors)

    def test_repeat_keeps_identical_tree_and_migration_never_weakens_old_mode(self):
        self.migrate()
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file() and ".git" not in p.parts}
        self.assertTrue(check_migration(self.root, self.manifest)["passed"])
        self.assertTrue(check_migration(self.root, self.manifest)["passed"])
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        old = Path(self.temp.name) / "old"
        prepare(old, self.skill)
        (old / "existing/docs/product.md").rename(old / "existing/docs/requirements.md")
        self.assertFalse(check(old)["passed"])
        with self.assertRaises(ValueError):
            check_migration(old, self.manifest)

    def test_migration_cannot_lose_host_entry_or_required_navigation(self):
        self.migrate()
        project = self.root / "software"
        entry = project / "AGENTS.md"
        original = entry.read_bytes()
        for content in (None, "", "[需求](docs/requirements.md)\n",
                        "活任务 .scratch/current/spec.md。\n"):
            with self.subTest(content=content):
                if content is None:
                    entry.unlink()
                else:
                    put(project, "AGENTS.md", content)
                self.assertFalse(check_migration(self.root, self.manifest)["passed"])
                entry.write_bytes(original)
        self.assertTrue(check_migration(self.root, self.manifest)["passed"])

    def test_optional_binding_cannot_be_empty_or_lose_authority(self):
        self.migrate()
        project = self.root / "software"
        for content in ("", "历史 [决定](../archive/old-decision.md)。\n"):
            with self.subTest(content=content):
                put(project, "docs/agents/workflow.md", content)
                self.assertFalse(check_migration(self.root, self.manifest)["passed"])

    def test_recovery_preserves_parallel_content_and_stops_at_occupied_origin(self):
        self.migrate()
        project = self.root / "software"
        put(project, "parallel.txt", "Someone else's new work.\n")
        put(project, "docs/product.md", "Someone else's new origin.\n")
        entries = self.manifest["cases"]["software"]
        conflicts = [entry["source"] for entry in entries if (project / entry["source"]).exists()]
        self.assertEqual(conflicts, ["docs/product.md"])
        self.assertEqual((project / "docs/product.md").read_text(encoding="utf-8"), "Someone else's new origin.\n")
        self.assertTrue((project / "docs/requirements.md").exists())
        # Once that conflict is independently resolved, recover only owned mappings.
        (project / "docs/product.md").rename(project / "parallel-origin.md")
        for entry in entries:
            shutil.copyfile(self.root / "rollback/software" / entry["source"], project / entry["source"])
            if entry["action"] != "delete":
                (project / entry["target"]).unlink()
        self.assertEqual((project / "docs/product.md").read_bytes(), (self.root / "rollback/software/docs/product.md").read_bytes())
        self.assertEqual((project / "parallel.txt").read_text(encoding="utf-8"), "Someone else's new work.\n")
        self.assertEqual((project / "parallel-origin.md").read_text(encoding="utf-8"), "Someone else's new origin.\n")


def read_pinned_reference(catalog, owner, resource):
    """Test the path contract only; this is not an installer or host resolver."""
    rel = PurePosixPath(resource)
    if rel.is_absolute() or ".." in rel.parts or "\\" in resource:
        raise ValueError("unsafe relative resource")
    matches = [r for r in catalog if r["origin"] == "lysyscy/My-Skills" and r["owner"] == owner]
    if len(matches) != 1:
        raise ValueError("missing or ambiguous trusted owner")
    record = matches[0]
    entry = Path(record["entry"]).resolve(strict=True)
    target = (entry.parent / Path(*rel.parts)).resolve(strict=True)
    if not target.is_relative_to(entry.parent) or not target.is_file():
        raise ValueError("outside owner package")
    if hashlib.sha256(target.read_bytes()).hexdigest() != record["expected"][resource]:
        raise ValueError("changed fixed resource")
    return target.read_bytes()


class RealResourceLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="real-resource-layout-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = Path(__file__).resolve().parents[1]
        policy = json.loads((source / "skill-package.json").read_text(encoding="utf-8"))
        self.assertEqual(policy["remote"], "https://github.com/lysyscy/My-Skills.git")
        self.catalog = []
        for directory, owner, resource in (("independent/library-a", "setup-solo-workflow", "references/document-maintenance.md"),
                                           ("unrelated/library-b", "improve-workflow", "references/package-operations.md"),
                                           ("another/location-c", "implement-solo-spec", "references/execution.md")):
            original = source / "skills" / owner
            target = self.root / directory / owner
            shutil.copytree(original, target)
            resources = [resource]
            if owner == "implement-solo-spec":
                resources.extend("references/" + name + ".md" for name in ("coordination", "delegation", "verification"))
            self.catalog.append({"origin": "lysyscy/My-Skills", "owner": owner,
                                 "entry": str(target / "SKILL.md"),
                                 "expected": {path: hashlib.sha256((original / path).read_bytes()).hexdigest() for path in resources}})

    def test_nonadjacent_copies_read_actual_candidate_resources(self):
        for record in self.catalog:
            resource = next(iter(record["expected"]))
            text = read_pinned_reference(self.catalog, record["owner"], resource)
            self.assertGreater(len(text), 100)
            self.assertEqual(text, (Path(record["entry"]).parent / resource).read_bytes())
        self.assertNotEqual(Path(self.catalog[0]["entry"]).parent.parent, Path(self.catalog[1]["entry"]).parent.parent)

    def test_copied_execution_reaches_its_real_specialist_resources(self):
        record = next(r for r in self.catalog if r["owner"] == "implement-solo-spec")
        execution = read_pinned_reference(self.catalog, record["owner"], "references/execution.md").decode("utf-8")
        for name in ("coordination", "delegation", "verification"):
            self.assertIn(name + ".md", execution)
            resource = "references/" + name + ".md"
            actual = read_pinned_reference(self.catalog, record["owner"], resource)
            self.assertEqual(actual, (Path(record["entry"]).parent / resource).read_bytes())
            self.assertGreater(len(actual), 100)
        self.assertNotEqual(Path(record["entry"]).parent.parent, Path(self.catalog[0]["entry"]).parent.parent)

    def test_actual_link_entry_and_foreign_same_name_preserve_owner(self):
        from test_skill_package import manager
        record = self.catalog[0]
        link = self.root / "agent-link"
        manager.link_directory(Path(record["entry"]).parent, link)
        self.assertTrue(manager.linked(link))
        linked = dict(record, entry=str(link / "SKILL.md"))
        resource = next(iter(record["expected"]))
        foreign_root = self.root / "third-party" / record["owner"]
        shutil.copytree(Path(record["entry"]).parent, foreign_root)
        foreign_resource = foreign_root / resource
        foreign_resource.write_bytes(foreign_resource.read_bytes() + b"\nforeign fork\n")
        foreign = dict(record, origin="other/skills", entry=str(foreign_root / "SKILL.md"),
                       expected={resource: hashlib.sha256(foreign_resource.read_bytes()).hexdigest()})
        self.assertEqual(read_pinned_reference([foreign, linked], record["owner"], resource),
                         (link / resource).read_bytes())
        with self.assertRaisesRegex(ValueError, "missing or ambiguous"):
            read_pinned_reference([foreign], record["owner"], resource)

    def test_missing_ambiguous_foreign_escaping_and_changed_resources_reject(self):
        record = self.catalog[0]
        resource = next(iter(record["expected"]))
        for catalog, owner, path in (([], record["owner"], resource),
                                     ([record, dict(record)], record["owner"], resource),
                                     ([dict(record, origin="other/skills")], record["owner"], resource),
                                     ([record], record["owner"], "../outside.md"),
                                     ([record], record["owner"], "/outside.md"),
                                     ([record], record["owner"], "references/absent.md")):
            with self.subTest(path=path, catalog=catalog), self.assertRaises((ValueError, FileNotFoundError, KeyError)):
                read_pinned_reference(catalog, owner, path)
        target = Path(record["entry"]).parent / resource
        target.write_bytes(target.read_bytes() + b"\nchanged after pin\n")
        with self.assertRaisesRegex(ValueError, "changed fixed"):
            read_pinned_reference([record], record["owner"], resource)

    def test_linked_resource_cannot_escape_its_owner_package(self):
        from test_skill_package import manager
        record = self.catalog[0]
        outside = self.root / "outside"
        outside.mkdir()
        resource = next(iter(record["expected"]))
        shutil.copyfile(Path(record["entry"]).parent / resource, outside / "real.md")
        manager.link_directory(outside, Path(record["entry"]).parent / "references/escape")
        with self.assertRaisesRegex(ValueError, "outside owner"):
            read_pinned_reference([record], record["owner"], "references/escape/real.md")


if __name__ == "__main__":
    unittest.main()
