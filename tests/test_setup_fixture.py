import tempfile
from pathlib import Path
import unittest

from setup_fixture import check, git, prepare, put, read, summary


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


if __name__ == "__main__":
    unittest.main()
