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


def batch_plan_v2():
    plan = batch_plan()
    del plan["pending"]
    plan.update(
        schema=2,
        decisions=[],
        operations=[{
            "target": "示例工具账号",
            "action": "在桌面登录",
            "waiting": "核对账号同步",
            "candidateId": "APP-1",
        }],
        notices=["共用代理重启时会暂时断线。"],
        followups=[{
            "target": "共用环境",
            "status": "其他宿主的插件版本未验证。",
            "actions": [{
                "when": "now",
                "work": "检查其他宿主",
                "verify": "读取宿主实际加载的插件版本。",
            }],
        }],
    )
    item = plan["groups"][0]["items"][0]
    for field in ("risk", "action", "safe"):
        del item[field]
    item["notice"] = "重启示例工具时会断开同步。"
    item["actions"] = [
        {"when": "now", "work": "隔离验证新版本", "verify": "核对插件能否加载。"},
        {
            "when": "after-authorization",
            "work": "切换共享环境版本",
            "verify": "读取共享环境进程实际运行的版本。",
        },
    ]
    return plan


def update_decision():
    return {
        "target": "示例工具",
        "action": "选定共享环境的版本",
        "options": [
            {"label": "本批保留 1.0", "impact": "现有插件继续使用 1.0。"},
            {"label": "验证通过后切到 1.1", "impact": "使用该工具的进程需要重启。"},
        ],
        "recommendation": 1,
        "waiting": "把共享环境的示例工具切换到 1.1",
        "candidateId": "APP-1",
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

    def test_renders_legacy_batch_with_and_without_schema(self):
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
            "schema": (True, 1.0, 2.0, "1", 2, 3, None),
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

    def test_v2_requires_current_arrays_and_rejects_pending(self):
        for field in ("decisions", "operations", "notices", "followups"):
            with self.subTest(missing=field):
                plan = batch_plan_v2()
                del plan[field]
                self.assert_rejected(self.run_report(plan))
            with self.subTest(not_a_list=field):
                self.assert_rejected(self.run_report(dict(batch_plan_v2(), **{field: {}})))
        self.assert_rejected(self.run_report(dict(batch_plan_v2(), pending=[])))
        self.assert_rejected(self.run_report(dict(batch_plan_v2(), notices=[" "])))

    def test_v2_rejects_invalid_candidate_actions_notices_and_archive_fields(self):
        cases = {
            "actions": ([], [{"when": "later", "work": "核对", "verify": "读版本"}]),
            "notice": (" ", None),
            "risk": ("旧风险",),
            "action": ("旧动作",),
            "safe": (True,),
        }
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    plan = batch_plan_v2()
                    plan["groups"][0]["items"][0][field] = value
                    self.assert_rejected(self.run_report(plan))

    def test_v2_rejects_decisions_without_distinct_options_and_a_valid_recommendation(self):
        decision = update_decision()
        first, second = decision["options"]
        blank_impact = dict(second, impact=" ")
        duplicate_label = dict(second, label=f" {first['label']} ")
        cases = {
            "target": (" ",),
            "action": (None,),
            "options": ([first], [first, blank_impact], [first, duplicate_label], [first, {}]),
            "recommendation": (True, -1, 2, 1.0, "1"),
            "waiting": ("",),
            "candidateId": ("APP-9", []),
            "unknown": ("其他字段",),
        }
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    plan = batch_plan_v2()
                    plan["decisions"] = [dict(decision, **{field: value})]
                    self.assert_rejected(self.run_report(plan))
        del decision["waiting"]
        self.assert_rejected(self.run_report(dict(batch_plan_v2(), decisions=[decision])))

    def test_v2_rejects_invalid_followups_and_operations(self):
        cases = {
            "followups": {
                "target": ("",),
                "status": (None, " "),
                "actions": (
                    [],
                    [{"when": "now", "work": "", "verify": "读版本"}],
                    [{"when": "now", "work": "核对", "verify": None}],
                    [{"when": "now", "work": "核对"}],
                ),
            },
            "operations": {
                "target": (1,),
                "action": (" ",),
                "waiting": (None,),
                "candidateId": ("APP-9", False),
                "options": ([],),
            },
        }
        for section, fields in cases.items():
            for field, values in fields.items():
                for value in values:
                    with self.subTest(section=section, field=field, value=value):
                        plan = batch_plan_v2()
                        plan[section][0][field] = value
                        self.assert_rejected(self.run_report(plan))

    def inspect_report(self, plan):
        if not NODE:
            self.skipTest("Node.js is required to run the generated report JavaScript")
        html = self.render(plan)
        data, script = re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.DOTALL)
        document = """
            function element(tag) {
              return {
                tag, textContent: '', children: [], dataset: {}, attributes: {}, listeners: {},
                classList: {add() {}},
                append(child) { this.children.push(child); },
                setAttribute(name, value) { this.attributes[name] = value; },
                addEventListener(name, listener) { this.listeners[name] = listener; },
              };
            }
            const elements = Object.fromEntries(
              ['report-data', 'report-content', 'decisions', 'groups', 'date', 'counts']
                .map(id => [id, element()])
            );
            const document = {getElementById: id => elements[id], createElement: element};
            elements['report-data'].textContent = DATA;
            elements.decisions.hidden = true;
        """.replace("DATA", json.dumps(data))
        inspect = """
            function text(node) {
              if (typeof node === 'string') return node;
              if (node.hidden) return '';
              return node.textContent + node.children.map(text).join('');
            }
            function descendants(node, tag) {
              return node.children.flatMap(child => typeof child === 'string' ? [] : [
                ...(child.tag === tag ? [child] : []), ...descendants(child, tag),
              ]);
            }
            function links(node) {
              return descendants(node, 'a').map(link => [text(link), link.href]);
            }
            const content = elements['report-content'];
            const decisionSection = elements.decisions;
            const firstGroup = content.children.find(node => node.id === 'group-0');
            const button = descendants(firstGroup, 'button')[0];
            const rows = descendants(firstGroup, 'tr');
            const details = rows.find(row => row.id === button.attributes['aria-controls']);
            const beforeDetails = text(details);
            button.listeners.click();
            console.log(JSON.stringify({
              date: text(elements.date),
              counts: elements.counts.children.map(text),
              sections: Object.fromEntries(content.children.map(node => [node.id, text(node)])),
              columns: descendants(firstGroup, 'th').filter(node => node.scope === 'col').map(text),
              rows: rows.map(row => [row.id, row.children.map(text)]),
              reportLinks: links(content),
              decisions: text(decisionSection),
              decisionHeadings: descendants(decisionSection, 'h2').map(text),
              decisionLinks: links(decisionSection),
              decisionControls: ['button', 'input', 'select', 'form']
                .flatMap(tag => descendants(decisionSection, tag)).length,
              options: descendants(decisionSection, 'li').map(text),
              beforeDetails,
              afterDetails: text(details),
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
        return json.loads(run.stdout)

    def test_legacy_report_preserves_candidate_columns_and_shows_neutral_archived_notes(self):
        plan = batch_plan()
        plan["groups"][0]["items"].append(
            dict(plan["groups"][0]["items"][0], id="APP-2", ready=True, safe=True)
        )
        result = self.inspect_report(plan)
        self.assertEqual(result["date"], "2024-02-29 · 检查快照")
        self.assertEqual(result["columns"], ["编号", "目标", "当前版本", "候选版本", "风险", "建议动作"])
        for content in ("示例工具", "1.0", "1.1", "需要核对插件兼容性", "隔离验证", "未就绪"):
            self.assertIn(content, result["sections"]["group-0"])
        self.assertIn("1 未就绪候选", result["counts"])
        self.assertIn("1 风险可控候选", result["counts"])
        self.assertNotIn("待确认", " ".join(result["counts"]))
        self.assertEqual(result["decisions"], "")
        self.assertEqual(result["sections"]["pending"], "旧批次备注 · 1 项" + plan["pending"][0])
        self.assertIn(["查看来源", "https://example.org/releases/1.1"], result["reportLinks"])

    def test_v2_no_decisions_with_unready_work_notices_and_manual_operations(self):
        plan = batch_plan_v2()
        first = plan["groups"][0]["items"][0]
        second = dict(first, id="APP-2", target="另一工具", ready=True)
        del second["notice"]
        del second["source"]
        plan["groups"][0]["items"].append(second)
        result = self.inspect_report(plan)
        self.assertEqual(result["decisions"], "本批无需你决定")
        self.assertEqual(result["columns"][-2:], ["你留意一下", "我来处理"])
        self.assertIn("1 未就绪候选", result["counts"])
        self.assertIn("在桌面登录", result["sections"]["operations"])
        self.assertIn("核对账号同步", result["sections"]["operations"])
        self.assertIn(plan["notices"][0], result["sections"]["notices"])
        self.assertIn("其他宿主的插件版本未验证", result["sections"]["followups"])
        self.assertIn("检查其他宿主", result["sections"]["followups"])
        rows = dict(result["rows"])
        self.assertIn(first["notice"], rows["candidate-APP-1"])
        self.assertNotIn(first["notice"], rows["candidate-APP-2"])
        self.assertIn("现在能做隔离验证新版本", rows["candidate-APP-1"][-1])
        self.assertIn("获授权后再做切换共享环境版本", rows["candidate-APP-1"][-1])
        self.assertEqual(result["beforeDetails"], "")
        self.assertIn(first["actions"][0]["verify"], result["afterDetails"])
        self.assertIn(first["details"]["发行说明"], result["afterDetails"])
        self.assertIn(["查看来源", first["source"]], result["reportLinks"])

    def test_v2_decision_names_action_and_waiting_scope_and_counts_only_the_decision(self):
        plan = batch_plan_v2()
        decision = update_decision()
        decision["options"][1]["impact"] += " </script><b>重启后核对</b>"
        plan["decisions"] = [decision]
        result = self.inspect_report(plan)
        self.assertEqual(result["decisionHeadings"], ["需要你决定 · 1 项"])
        for content in (
            "示例工具 · 选定共享环境的版本",
            "等你决定后再做" + decision["waiting"],
            "只有列出的操作会等你决定",
            "其他已获授权、能独立开展的工作照常进行",
        ):
            self.assertIn(content, result["decisions"])
        self.assertEqual(result["options"], [
            "本批保留 1.0现有插件继续使用 1.0。",
            "验证通过后切到 1.1推荐使用该工具的进程需要重启。 </script><b>重启后核对</b>",
        ])
        self.assertIn("1 未就绪候选", result["counts"])
        self.assertNotIn("需要你决定", " ".join(result["counts"]))
        self.assertIn("需要你操作", result["sections"]["operations"])
        self.assertNotIn("在桌面登录", result["decisions"])
        self.assertEqual(result["decisionLinks"], [["查看候选 APP-1", "#candidate-APP-1"]])
        self.assertIn("candidate-APP-1", dict(result["rows"]))
        self.assertEqual(result["decisionControls"], 0)


if __name__ == "__main__":
    unittest.main()
