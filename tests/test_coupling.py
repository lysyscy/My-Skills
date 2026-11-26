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

    def diagnostics(self):
        run = self.run_coupling("--json")
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        return json.loads(run.stdout)

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
            ("读取models.md文件", "host-config", "models.md"),
            ("读取hooks.json配置", "host-config", "hooks.json"),
            ("读取CODEX_HOME变量", "host-config", "CODEX_HOME"),
            ("使用codex-runtimes路径", "host-config", "codex-runtimes"),
            ("读取 D:/AppData/app/codex/plugins", "host-config", "D:/AppData/app/codex"),
            (r'读取 "C:\\Users\\Test User\\AppData\\app\\codex\\plugins"', "host-config",
             r"C:\\Users\\Test User\\AppData\\app\\codex"),
            ("读取 /mnt/d/AppData/app/codex/plugins", "host-config", "/mnt/d/AppData/app/codex"),
        ]
        clean = (
            "\n使用当前宿主加载的 pstack。\n"
            "Codex 的入口、Claude Code 的入口、由 Antigravity 调用。\n"
            "myCodexBridge pre_spawn_agent preview_status_text hooks.jsonl\n"
            "fixtures/AppData/app/codex/plugins D:/AppData/app/codex-example/plugins\n"
        )
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
                    (rule_id, match, hashlib.sha256(line.encode("utf-8")).hexdigest()),
                    [(item["rule_id"], item["match"], item["line_sha256"]) for item in findings],
                )
        self.assertFalse(any(item["line"] > len(cases) for item in result["violations"]))
        self.assertEqual(set(self.source.iterdir()), {source})
        self.assertEqual(source.read_bytes(), content.encode("utf-8"))

    def test_scans_contract_paths_and_preserves_wider_link_scope(self):
        contracts = [
            "AGENTS.md", "packages/example/AGENTS.md", "docs/agents/overview.md",
            "skills/group/example/SKILL.md", "skills/example/references/nested/guide.md",
            "skills/example/templates/README.md", "agent-skills/example/SKILL.md",
            "agent-skills/example/references/nested/guide.md",
            *[f"tools/nested/check.{ext}" for ext in ("py", "js", "mjs", "cjs", "ps1")],
        ]
        links_only = [
            "README.md", "CONTRIBUTING.md", "CODING_STANDARDS.md", "docs/guides/nested/how.md",
            "docs/reference/config/guide.md", "docs/adr/0001.md", "docs/architecture/storage/design.md",
            "docs/architecture-notes.md", "docs/requirements.md",
        ]
        outside_scope = [
            "docs/notes.md", "packages/example/README.md", "notes.py", "tools/helper.txt",
            "skills/example/examples/notes.md", "agent-skills/example/templates/README.md",
            ".artifacts/runs/current/AGENTS.md", ".scratch/current/AGENTS.md", "node_modules/lib/AGENTS.md",
        ]
        for name in contracts + links_only + outside_scope:
            self.write(name, "调用pstack:verify [help](missing.md)")
        result = self.diagnostics()
        self.assertEqual(result["files_checked"], len(contracts) + len(links_only))
        self.assertEqual(
            [(item["path"], item["rule_id"]) for item in result["violations"]],
            sorted(
                [(name, "pstack-qualified") for name in contracts]
                + [(name, "broken-relative-link") for name in contracts + links_only if name.endswith(".md")]
            ),
        )

    def test_prunes_unreadable_cache_and_dependency_directories(self):
        self.write("README.md", "# Project\n")
        caches = {
            self.write(f"backend/{name}/AGENTS.md", "Use preview_open. [Help](missing.md)").parent
            for name in (".pytest_cache", "__pycache__", ".venv", "node_modules", ".git")
        }
        scandir = os.scandir

        def scan(path):
            if Path(path) in caches:
                raise PermissionError("fixture unreadable cache or dependency directory")
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
        ):
            self.write(name, "T3 Code: use preview_open and hooks.json in Codex.")
        shared = [
            "docs/agents/host-rules.md", "docs/agents/t3-adapter.md",
            "skills/project-handoff/references/general.md", "skills/software-updates/SKILL.md",
            *[
                f"skills/software-updates/references/{name}.md"
                for name in ("general", "services", "status", "targets", "unigetui")
            ],
        ]
        for name in shared:
            self.write(name, "Use preview_open.")
        result = self.diagnostics()
        self.assertEqual([item["path"] for item in result["violations"]], sorted(shared))

    def test_accepts_same_line_ignores_in_each_supported_file_type(self):
        examples = {
            "AGENTS.md": ("Use preview_open.", "<!-- {} -->"),
            "tools/check.py": ("preview_open()", "# {}"),
            "tools/check.ps1": ("preview_open", "# {}"),
            **{f"tools/check.{ext}": ("const timeout = preview_open() / 2;", "// {}") for ext in ("js", "mjs", "cjs")},
        }
        directive = "coupling-ignore: host-tool This adapter loads CODEX_HOME before calling the tool."
        for name, (source, comment) in examples.items():
            self.write(name, f"{source} {comment.format(directive)}\r\n{source}\r\n")
        self.assertEqual(
            [(item["path"], item["line"], item["rule_id"]) for item in self.diagnostics()["violations"]],
            [(name, 2, "host-tool") for name in sorted(examples)],
        )

    def test_ignores_only_the_named_rule_on_the_annotated_line(self):
        self.write("AGENTS.md", "\n".join([
            "Read hooks.json before calling preview_open. <!-- coupling-ignore: host-tool The adapter owns this call. -->",
            "<!-- coupling-ignore: host-tool The adapter owns this call. -->",
            "Call preview_open.",
            "Read hooks.json before calling preview_open."
            " <!-- coupling-ignore: host-config Required file in this adapter. -->"
            " <!-- coupling-ignore: host-tool Required call in this adapter. -->",
        ]))
        self.assertEqual(
            [(item["line"], item["rule_id"]) for item in self.diagnostics()["violations"]],
            [(1, "host-config"), (3, "host-tool")],
        )

    def test_ignore_text_in_literals_does_not_apply(self):
        directive = "coupling-ignore: host-tool Only an example"
        examples = {
            "AGENTS.md": f"Use preview_open. `<!-- {directive} -->`",
            "tools/check.cjs": f"const example = /[// {directive}]/; preview_open();",
            "tools/check.py": f'print("preview_open # {directive}")',
            "tools/check.js": f'const example = "preview_open // {directive}";',
            "tools/check.ps1": f'Write-Output "preview_open # {directive}"',
        }
        for name, line in examples.items():
            self.write(name, line)
        self.assertEqual(
            [(item["path"], item["line"], item["rule_id"]) for item in self.diagnostics()["violations"]],
            [(name, 1, "host-tool") for name in sorted(examples)],
        )

    def test_reports_missing_fields_and_unknown_rules_at_the_comment(self):
        payloads = ("", "host-tool", "host-brand Removed rule")
        self.write("tools/check.py", "\n".join(
            f"preview_open()  # coupling-ignore: {payload}" for payload in payloads
        ))
        result = self.diagnostics()
        self.assertEqual(result["status"], "validation_failed")
        self.assertEqual(
            [(item["line"], item["match"]) for item in result["violations"] if item["rule_id"] == "invalid-ignore"],
            list(enumerate(payloads, 1)),
        )
        self.assertEqual(
            [item["line"] for item in result["violations"] if item["rule_id"] == "host-tool"],
            [1, 2, 3],
        )

    def test_retired_sidecar_is_not_loaded(self):
        self.write("AGENTS.md", "Use preview_open.")
        sidecar = self.write("coupling-exceptions.json", "invalid JSON")
        self.assertEqual(
            [(item["path"], item["rule_id"]) for item in self.diagnostics()["violations"]],
            [("AGENTS.md", "host-tool")],
        )
        run = self.run_coupling("--exceptions", sidecar)
        self.assertEqual(run.returncode, 2)
        self.assertIn("unrecognized arguments: --exceptions", run.stderr)

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

    def test_adapter_and_inline_ignores_do_not_waive_broken_links(self):
        self.write(
            "AGENTS.md",
            "Use preview_open [help](missing.md). <!-- coupling-ignore: host-tool The adapter supplies this tool. -->",
        )
        self.write(
            "README.md",
            "[help](missing.md) <!-- coupling-ignore: broken-relative-link An attempted link waiver. -->",
        )
        self.write("docs/agents/host-adapters.md", "T3 Code [help](missing.md)")
        result = self.diagnostics()
        self.assertEqual(
            [(item["path"], item["rule_id"]) for item in result["violations"]],
            [
                ("AGENTS.md", "broken-relative-link"),
                ("README.md", "broken-relative-link"),
                ("README.md", "invalid-ignore"),
                ("docs/agents/host-adapters.md", "broken-relative-link"),
            ],
        )
