# 代码守卫

接入前先把项目现有正确性、类型和空异常处理违规改到零。注释守卫检查新增和改动行。修改旧文件时顺手删掉重复代码含义的旧注释。保留机器指令、API 文档和需要解释的外部约束。

按[工具部署](../templates/README.md)选 `code-guardrails`。守卫脚本使用 Python 标准库。项目已有本地解释器时沿用其入口。

## TS 和 JS

用项目包管理器将 Oxlint 加入开发依赖，按 [Oxlint 示例](../templates/oxlintrc.example.json) 合并 `.oxlintrc.json`。把检查接到 `package.json` 的 `lint`，在提交钩子和 CI 调用项目的 lint 命令。

```json
{
  "scripts": {
    "lint": "oxlint && python -B tools/audit/comment_guard.py --tracked --assertions"
  }
}
```

守卫识别跨行的 `as unknown as`，并跳过字符串、模板文本和常见正则字面量。用校验或类型收窄替代双重断言。

## Python

把 Ruff 加入开发依赖。按 [Ruff 示例](../templates/ruff-pyproject.example.toml) 合并 `pyproject.toml`，并用项目支持的 Python 版本设置 `target-version`。在提交钩子和 CI 调用 `ruff check`。使用 uv 的项目运行 `uv run ruff check`。修复根因或处理明确的异常，保留可诊断的失败。

## 新改动的注释

在 pre-commit 执行 `python -B tools/audit/comment_guard.py --staged`，它读取暂存内容，只检查新增或改动行。CI 可用 `--diff <比较基线>` 对照 PR 基线或推送前提交。手工检查用 `--diff` 对比 `HEAD`，包括未忽略的未跟踪源码。全文件排查用 `--files <路径...>`。

Python 用 `tokenize` 区分注释与文档字符串。TS 和 JS 保留带 API 标签的 JSDoc。工具指令如 `noqa`、`type:`、`coupling-ignore` 和 `@ts-expect-error` 可通过。外部约束用 `external-constraint: <约束及出处>`，由审查者确认内容。脚本报告 `文件:行号: 规则`，违规退出 1，输入或检查失败退出 2。

宿主已启用 Stop Code Guard 时，会发现 `tools/audit/comment_guard.py` 并从仓库根调用 `--diff`。提交与 CI 各自保留检查入口。
