"""Exercise the update report through its CLI and generated HTML."""

from copy import deepcopy
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


RENDERER = (
    Path(__file__).resolve().parents[1]
    / "skills/software-updates/scripts/render_report.py"
)
NODE = shutil.which("node")


def batch_plan():
    item = {
        "id": "APP-1",
        "target": "示例工具",
        "current": "1.0",
        "candidate": "1.1",
        "risk": "需要核对插件兼容性",
        "action": "隔离验证",
        "safe": False,
        "ready": False,
        "details": {"发行说明": "版本 < 1.1 的配置需要复核"},
        "source": "https://example.org/releases/1.1",
    }
    return {
        "schema": 1,
        "batch": "2024-02-29",
        "caption": "检查快照",
        "groups": [{"name": "工具", "items": [item]}],
        "pending": ["APP-1 等待确认插件兼容性"],
        "current": [],
        "paused": [],
    }


class SoftwareUpdatesReportTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="software-updates-report-")
        self.addCleanup(directory.cleanup)
        self.input = Path(directory.name) / "batch.json"
        self.output = Path(directory.name) / "report.html"

    def run_report(self, plan):
        return self.run_report_json(json.dumps(plan, ensure_ascii=False))

    def run_report_json(self, payload):
        self.input.write_text(payload, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(RENDERER), str(self.input), str(self.output)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            timeout=15,
        )

    def render(self, plan):
        run = self.run_report(plan)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        return self.output.read_text(encoding="utf-8")

    def assert_rejected(self, run):
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.assertTrue(run.stderr)
        self.assertFalse(self.output.exists())

    def test_renders_batch_with_and_without_schema(self):
        for schema_present in (True, False):
            with self.subTest(schema_present=schema_present):
                plan = batch_plan()
                if not schema_present:
                    del plan["schema"]
                    del plan["groups"][0]["items"][0]["source"]
                report = self.render(plan)
                data = re.search(
                    r'<script id="report-data" type="application/json">(.*?)</script>',
                    report,
                    re.DOTALL,
                )
                self.assertIsNotNone(data)
                self.assertEqual(json.loads(data[1]), plan)
                self.assertNotIn("<", data[1])
                self.output.unlink()

    def test_rejects_malformed_json_and_non_objects(self):
        for payload in ("{", "null", "[]", "42", '"batch"'):
            with self.subTest(payload=payload):
                self.assert_rejected(self.run_report_json(payload))

    def test_rejects_duplicate_keys_and_unpaired_surrogates(self):
        payload = json.dumps(batch_plan()).replace('"schema": 1', '"schema": 1, "schema": 1')
        self.assert_rejected(self.run_report_json(payload))
        self.assert_rejected(self.run_report_json(json.dumps(dict(batch_plan(), caption="\ud800"))))

    def test_rejects_invalid_batch_fields(self):
        cases = {
            "schema": (True, 1.0, "1", 2, None),
            "batch": ("2024-02-30", "20240229", "2024-2-29", "2024-W09-4", 20240229),
            "caption": ("", " ", None),
            "groups": ([], "", {}, [{"name": 1, "items": [{}]}]),
            "pending": ("", [""], [1]),
            "current": ({}, [" "]),
            "paused": ([None], [""]),
            "unknown": (1,),
        }
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    plan = batch_plan()
                    plan[field] = value
                    self.assert_rejected(self.run_report(plan))

    def test_rejects_invalid_group_fields(self):
        for field, value in (
            ("name", 1), ("name", ""), ("name", " "),
            ("items", []), ("items", {}), ("items", ""), ("items", [None]),
            ("unknown", 1),
        ):
            with self.subTest(field=field, value=value):
                plan = batch_plan()
                plan["groups"][0][field] = value
                self.assert_rejected(self.run_report(plan))

    def test_rejects_invalid_item_fields(self):
        cases = {
            "id": ("app-1", "1", "APP", "APP-1\n", 1),
            "target": ("",),
            "current": (1,),
            "candidate": (None,),
            "risk": (" ",),
            "action": ("",),
            "safe": (1, "true"),
            "ready": (0, "false"),
            "details": ({}, [], {"": "文字"}, {"说明": " "}, {"说明": 1}),
            "source": (
                None, "", 1, "http://example.org", "https:///missing-host",
                "https:// /release", "https://example.org:bad", "https://[malformed",
                "https://example%3a.org", "https://[::1]invalid",
            ),
            "unknown": (1,),
        }
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    plan = batch_plan()
                    plan["groups"][0]["items"][0][field] = value
                    self.assert_rejected(self.run_report(plan))

    def test_rejects_missing_required_fields_at_each_level(self):
        for level in ("batch", "group", "item"):
            with self.subTest(level=level):
                plan = batch_plan()
                group = plan["groups"][0]
                item = group["items"][0]
                record, field = {
                    "batch": (plan, "paused"),
                    "group": (group, "name"),
                    "item": (item, "action"),
                }[level]
                del record[field]
                self.assert_rejected(self.run_report(plan))

    def test_rejects_duplicate_item_ids_across_groups(self):
        plan = batch_plan()
        other = deepcopy(plan["groups"][0])
        other["name"] = "另一个分组"
        plan["groups"].append(other)
        self.assert_rejected(self.run_report(plan))

    def test_rejects_existing_output_without_changing_it(self):
        self.output.write_bytes(b"existing output")
        run = self.run_report(batch_plan())
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.assertEqual(self.output.read_bytes(), b"existing output")

    @unittest.skipUnless(NODE, "Node.js is required to run the generated report JavaScript")
    def test_pending_count_matches_section_when_a_candidate_is_also_not_ready(self):
        plan = batch_plan()
        plan["groups"][0]["items"].append(
            dict(plan["groups"][0]["items"][0], id="APP-2", ready=True, safe=True)
        )
        html = self.render(plan)
        data, script = re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.DOTALL)
        document = """
            function element() {
              return {
                textContent: '', children: [], dataset: {},
                append(child) { this.children.push(child); },
                setAttribute() {}, addEventListener() {},
              };
            }
            const elements = Object.fromEntries(
              ['report-data', 'report', 'groups', 'date', 'counts'].map(id => [id, element()])
            );
            const document = {getElementById: id => elements[id], createElement: element};
            elements['report-data'].textContent = DATA;
        """.replace("DATA", json.dumps(data))
        inspect = """
            function text(node) {
              if (typeof node === 'string') return node;
              return node.textContent + node.children.map(text).join('');
            }
            console.log(JSON.stringify({
              counts: elements.counts.children.map(text),
              report: text(elements.report),
              pending: elements.report.children.find(node => node.id === 'pending').children.map(text),
            }));
        """
        run = subprocess.run(
            [NODE, "-"],
            input=document + script + inspect,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            timeout=15,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        for content in ("示例工具", "1.0", "1.1", "需要核对插件兼容性", "隔离验证", "未就绪"):
            self.assertIn(content, result["report"])
        self.assertIn("1 未就绪候选", result["counts"])
        self.assertEqual(
            [count for count in result["counts"] if "待确认" in count], ["1 待确认事项"]
        )
        self.assertEqual(result["pending"], ["待确认事项 · 1 项", plan["pending"][0]])


if __name__ == "__main__":
    unittest.main()
