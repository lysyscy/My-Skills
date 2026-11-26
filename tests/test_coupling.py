"""Exercise the read-only coupling command against ordinary source directories."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.skill_package import check_coupling


TOOL = Path(__file__).resolve().parents[1] / "tools/skill_package.py"


class CouplingChecks(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="coupling-check-")
        self.addCleanup(directory.cleanup)
        self.source = Path(directory.name).resolve()

    def write(self, name, content):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="")
        return path

    def run_coupling(self, *options):
        return subprocess.run(
            [sys.executable, str(TOOL), "coupling", "--source", str(self.source), *map(str, options)],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )

    def diagnostics(self, *options, exit_code=1):
        run = self.run_coupling("--json", *options)
        self.assertEqual(run.returncode, exit_code, run.stdout + run.stderr)
        result = json.loads(run.stdout)
        return result

    def exception(self, path, line, rule="host-brand"):
        return {
            "path": path,
            "rule_id": rule,
            "line_sha256": hashlib.sha256(line.encode("utf-8")).hexdigest(),
            "owner": "fixture adapter",
            "reason": "Illustrates a concrete host invocation.",
        }

    def write_exceptions(self, entries, name="coupling-exceptions.json"):
        return self.write(name, json.dumps(entries, ensure_ascii=False))

    def test_detects_package_tool_config_and_host_tokens_at_ascii_boundaries(self):
        cases = [
            ("用t3-pstack接入", "pstack-package", "t3-pstack"),
            ("调用pstack:create-verification-skill后继续", "pstack-qualified", "pstack:create-verification-skill"),
            ("解析pstack:*", "pstack-qualified", "pstack:*"),
            ("在T3 Code里运行", "t3-runtime", "T3 Code"),
            ("设置T3_ACP_MCP_CALL即可", "t3-runtime", "T3_ACP_MCP_CALL"),
            ("配置T3CODE_AGENT的值", "t3-runtime", "T3CODE_AGENT"),
            ("调用delegate_task之后", "host-tool", "delegate_task"),
            ("调用spawn_agent之后", "host-tool", "spawn_agent"),
            ("使用preview_status和其他入口", "host-tool", "preview_status"),
            ("使用preview_open打开页面", "host-tool", "preview_open"),
            ("以preview_snapshot取证", "host-tool", "preview_snapshot"),
            ("调用mcp__t3_code__preview_act", "host-tool", "mcp__t3_code__preview_act"),
            ("先用orchestrator_capabilities探测", "host-tool", "orchestrator_capabilities"),
            ("调用t3_thread_launch", "host-tool", "t3_thread_launch"),
            ("Codex的入口", "host-brand", "Codex"),
            ("Claude Code的入口", "host-brand", "Claude Code"),
            ("由Antigravity调用", "host-brand", "Antigravity"),
            ("读取models.md文件", "host-config", "models.md"),
            ("读取hooks.json配置", "host-config", "hooks.json"),
            ("读取CODEX_HOME变量", "host-config", "CODEX_HOME"),
            ("使用codex-runtimes路径", "host-config", "codex-runtimes"),
        ]
        clean = "\n使用当前宿主加载的 pstack。\nmyCodexBridge pre_spawn_agent preview_status_text hooks.jsonl\n"
        content = "\n".join(line for line, _, _ in cases) + clean
        source = self.write("AGENTS.md", content)
        result = self.diagnostics()
        self.assertEqual(result["status"], "validation_failed")
        self.assertEqual(result["files_checked"], 1)
        self.assertEqual(Path(result["source"]), self.source)
        for number, (line, rule_id, match) in enumerate(cases, 1):
            with self.subTest(line=line):
                findings = [item for item in result["violations"] if item["line"] == number]
                self.assertIn(
                    (rule_id, match, self.exception("AGENTS.md", line)["line_sha256"]),
                    [(item["rule_id"], item["match"], item["line_sha256"]) for item in findings],
                )
        self.assertFalse(any(item["line"] > len(cases) for item in result["violations"]))
        self.assertEqual(set(self.source.iterdir()), {source})
        self.assertEqual(source.read_bytes(), content.encode("utf-8"))

    def test_scans_required_project_paths_and_excludes_runtime_artifacts(self):
        in_scope = [
            "AGENTS.md", "packages/example/AGENTS.md", "README.md", "CONTRIBUTING.md", "CODING_STANDARDS.md",
            "docs/agents/overview.md", "docs/guides/nested/how.md", "docs/reference/config/guide.md",
            "docs/adr/0001.md", "docs/architecture/storage/design.md", "docs/architecture-notes.md",
            "docs/requirements.md", "skills/group/example/SKILL.md", "skills/example/references/nested/guide.md",
            "skills/example/templates/README.md", "agent-skills/example/SKILL.md",
            "agent-skills/example/references/nested/guide.md",
            *[f"tools/nested/check.{ext}" for ext in ("py", "js", "mjs", "cjs", "ps1")],
        ]
        outside_scope = [
            "docs/notes.md", "packages/example/README.md", "notes.py", "tools/helper.txt",
            "skills/example/examples/notes.md", "agent-skills/example/templates/README.md",
            ".artifacts/runs/current/AGENTS.md", ".scratch/current/AGENTS.md", "node_modules/lib/AGENTS.md",
        ]
        for name in in_scope + outside_scope:
            self.write(name, "调用pstack:verify")
        result = self.diagnostics()
        self.assertEqual([item["path"] for item in result["violations"]], sorted(in_scope))

    def test_skips_unreadable_pytest_cache(self):
        self.write("README.md", "# Project\n")
        cache = self.write("backend/.pytest_cache/AGENTS.md", "Use Codex.").parent
        scandir = os.scandir

        def scan(path):
            if Path(path) == cache:
                raise PermissionError("fixture unreadable .pytest_cache")
            return scandir(path)

        with patch("os.scandir", side_effect=scan):
            result = check_coupling(self.source)
        self.assertEqual(
            (result["status"], result["files_checked"], result["violations"]),
            ("verified", 1, []),
        )

    def test_exempts_only_classified_adapter_and_history_paths(self):
        for name in (
            "docs/t3-adapter.md", "docs/archive/historical/AGENTS.md", "docs/receipts/AGENTS.md",
            "docs/agents/host-adapters.md", "skills/project-handoff/hooks/AGENTS.md",
            "skills/project-handoff/references/compaction-reminder.md", "tools/host_instructions.py",
            "skills/software-updates/references/targets.md",
        ):
            self.write(name, "T3 Code: use preview_open and hooks.json in Codex.")
        shared = [
            "docs/agents/host-rules.md", "docs/agents/t3-adapter.md",
            "skills/project-handoff/references/general.md", "skills/software-updates/references/general.md",
        ]
        for name in shared:
            self.write(name, "Use preview_open.")
        result = self.diagnostics()
        self.assertEqual([item["path"] for item in result["violations"]], sorted(shared))

    def test_exception_is_exact_to_one_path_rule_and_line_hash(self):
        name = "AGENTS.md"
        line = "  Codex的入口  "
        entry = self.exception(name, line)
        self.write(name, f"# Rules\r\n\r\n{line}\r\n")
        self.write_exceptions([entry])
        result = self.diagnostics(exit_code=0)
        self.assertEqual((result["status"], result["violations"]), ("verified", []))

        self.write(name, f"# Rules\n{line}\n")
        self.assertEqual(self.diagnostics(exit_code=0)["violations"], [])
        self.write("docs/guides/sibling.md", line)
        result = self.diagnostics()
        self.assertEqual([item["path"] for item in result["violations"]], ["docs/guides/sibling.md"])

        self.write(name, line.rstrip() + "\n")
        result = self.diagnostics()
        self.assertEqual(
            [(item["path"], item["rule_id"], item["line"]) for item in result["violations"]],
            [(name, "stale-exception", None), (name, "host-brand", 1), ("docs/guides/sibling.md", "host-brand", 1)],
        )
        self.assertEqual(result["violations"][0]["line_sha256"], entry["line_sha256"])

    def test_explicit_exceptions_override_default_and_preserve_other_rules(self):
        line = "Codex的工具调用spawn_agent"
        self.write("AGENTS.md", line)
        self.write_exceptions([self.exception("AGENTS.md", line, "host-tool")])
        explicit = self.write_exceptions([self.exception("AGENTS.md", line)], "overrides.json")
        self.assertEqual([item["rule_id"] for item in self.diagnostics()["violations"]], ["host-brand"])
        result = self.diagnostics("--exceptions", explicit)
        self.assertEqual([item["rule_id"] for item in result["violations"]], ["host-tool"])
        run = self.run_coupling("--exceptions", explicit)
        self.assertEqual(run.returncode, 1)
        self.assertIn("AGENTS.md:1 [host-tool]", run.stdout)

    def test_unused_and_ambiguous_exceptions_fail(self):
        line = "Codex的入口"
        name = "docs/reference/example.md"
        self.write_exceptions([self.exception(name, line)])
        absent = self.diagnostics()["violations"]
        self.assertEqual([(item["rule_id"], item["match"]) for item in absent], [("stale-exception", "host-brand")])
        self.write(name, f"{line}\n{line}\n")
        result = self.diagnostics()
        self.assertEqual(
            [(item["rule_id"], item["line"]) for item in result["violations"]],
            [("stale-exception", None), ("host-brand", 1), ("host-brand", 2)],
        )

    def test_malformed_exception_records_are_blocked(self):
        entry = self.exception("AGENTS.md", "Codex")
        for contents in (
            {"exceptions": [entry]},
            [{key: value for key, value in entry.items() if key != "owner"}],
            [{**entry, "reason": " "}],
            [{**entry, "line_sha256": "unchanged"}],
            [{**entry, "rule_id": "broken-relative-link"}],
            [{**entry, "path": "../AGENTS.md"}],
            [entry, entry],
        ):
            with self.subTest(contents=contents):
                self.write_exceptions(contents)
                result = self.diagnostics()
                self.assertEqual(set(result), {"status", "error"})
                self.assertEqual(result["status"], "blocked")

    def test_checks_relative_files_heading_fragments_and_reference_definitions(self):
        self.write("docs/guides/说明.md", "# 中文标题\n\n## 重复\n\n## 重复\n")
        self.write("docs/guides/guide (old).md", "With `Code`\n-----------\n")
        self.write("docs/architecture.md", '<a id="named"></a>\n# Current\n')
        self.write("README.md", "\n".join([
            "# Links",
            "[同仓标题](docs/guides/说明.md#%E4%B8%AD%E6%96%87%E6%A0%87%E9%A2%98)",
            "[重复标题](docs/guides/说明.md#重复-1)",
            '[文件名](<docs/guides/guide (old).md#with-code> "title")',
            "[目录](docs/guides/)",
            "[本页](#links)",
            "[引用][arch]",
            '[arch]: docs/architecture.md#named "Valid anchor"',
            "[远端](https://example.invalid/unknown.md#unavailable)",
            "[外部文件](file:///D:/unavailable.md)",
            '`[内联示例](inline-example.md)`',
            "```md",
            "[代码块示例](fenced-example.md)",
            "```",
            "<!-- [注释](comment-example.md) -->",
            "[缺文件](docs/missing.md)",
            "[旧锚点](docs/architecture.md#old)",
            "[跨行](",
            "    docs/missing-multiline.md",
            ")",
            "[失效定义]: docs/missing-ref.md",
            "[越界](../unavailable.md)",
        ]))
        result = self.diagnostics()
        self.assertEqual(
            [(item["line"], item["rule_id"], item["match"]) for item in result["violations"]],
            [
                (16, "broken-relative-link", "docs/missing.md"),
                (17, "broken-relative-link", "docs/architecture.md#old"),
                (18, "broken-relative-link", "docs/missing-multiline.md"),
                (21, "broken-relative-link", "docs/missing-ref.md"),
                (22, "broken-relative-link", "../unavailable.md"),
            ],
        )

    def test_unmatched_inline_backtick_cannot_hide_a_link_in_another_paragraph(self):
        self.write("README.md", (
            "A literal unpaired `.\n\n[Broken](missing.md)\n\n"
            "An inline example `[Example](example.md)`.\n"
        ))
        result = self.diagnostics()
        self.assertEqual([(item["line"], item["match"]) for item in result["violations"]], [(3, "missing.md")])

    def test_adapter_and_line_exception_do_not_waive_broken_links(self):
        line = "Codex [help](missing.md)"
        self.write("AGENTS.md", line)
        self.write_exceptions([self.exception("AGENTS.md", line)])
        self.write("docs/agents/host-adapters.md", "T3 Code [help](missing.md)")
        result = self.diagnostics()
        self.assertEqual(
            [(item["path"], item["rule_id"]) for item in result["violations"]],
            [("AGENTS.md", "broken-relative-link"), ("docs/agents/host-adapters.md", "broken-relative-link")],
        )
