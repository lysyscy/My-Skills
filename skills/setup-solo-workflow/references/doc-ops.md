# 文档操作与阶段收尾

当项目要用 Git 跟踪任务、派生状态页或按证据结项时接入。需要 Python 3.12 以上及 Git。按[工具部署](../templates/README.md)选 `doc-ops`，将[配置示例](../templates/doc-ops.config.example.json)调整为项目的 `tools/audit/doc-ops.config.json`。从项目实际规则取得路径、票状态和登记来源。

采用 Copier 式三方更新。保存采用的源版本，更新时比较旧示例、新示例和项目配置。合并本次采用的字段，保留项目的票号、状态、路径与登记约定。项目和新模板都修改同一含义时先解决冲突。部署器只更新代码及版本记录。

## 任务和状态页

将任务放在配置的 `tasks.glob`，纳入 Git。任务 Markdown 以 `---` 隔开的 frontmatter 开头，随后是一级标题。使用以下字段，按项目配置填状态和编号。列表支持行内 JSON 数组或缩进的 `- 值`。

```yaml
---
id: sample-task
kind: ticket
status: open
parent: null
children: []
blocked_by: []
worktree: null
worktree_state: null
managed_runs: []
remaining_acceptance: []
next_step: 核对用户路径
updated_at: 2026-01-01T09:00:00+08:00
---
# 示例任务
```

关联工作树时加 `branch`，填写 `worktree` 和 `worktree_state`，使其与 `closeout.worktrees` 的登记一致。父子任务互相引用。将 `entry.view_start` 和 `entry.view_end` 各作为独立一行放入状态页，再将状态页纳入 Git。派生视图只改这两行之间的内容。

```text
python -B tools/audit/doc_ops.py refresh --config tools/audit/doc-ops.config.json
python -B tools/audit/doc_ops.py check --config tools/audit/doc-ops.config.json
```

从仓库根执行。在外部运行工具时，传 `--root <项目根>` 和配置的绝对路径。`check` 检查任务、视图差异和 Git 已跟踪 Markdown 的本地链接。单查链接用 `links`。已跟踪内容引用未跟踪文件时报告 `LINK_UNTRACKED_TARGET`。保留确需引用历史本机材料的文档时，在 `links.exclude_sources` 逐个记录理由。

### 有部署回执的项目

在 `entry` 补充 `release_sources`，每项填仓库相对 `glob` 及 `run_id_parent`。父目录从 0 开始计数，目录名作为运行 ID。用 `release_verified` 声明回执必须满足的字段和值，用 `release_fields` 映射 `action`、`product_commit`、`pid`、`finished_at`。字段路径用点分隔，用数字访问数组。填 `release_actions` 和 `release_limit`（1 或 2），以及 `utc_offset_minutes`、`release_history_note` 和位于派生视图之前的 `release_heading`。

没有部署回执的项目可省略整个发布设置，任务、链接和工作树或运行组收尾仍可用。依赖已验证发布的旧交接删除和发布目录分类需要回执。

## 计划与执行

在主检出中按实际情况填 `git.base`、`git.remote`、`git.worktree_root`。在 `closeout.worktrees` 逐一登记 `id`、`label`、`state`、`reason` 和需要的 `branch`。要退役时固定 `head`，只有核清消费者和线程后才设置 `consumers_checked` 和 `thread_bindings`。线程条目用 `id`、`state`，确认结束后用 `settled`。工作树登记 `runs` 时，每项给出运行 `id` 和 `location`（`primary` 或 `worktree`）。

有预览消费者时配置 `closeout.preview_registries` 的仓库相对路径或 glob。登记用 `source_root` 指明源检出。旧登记可用指向已登记工作树的 `owner_path`，或从仓库内的原 owner 回执核实源。身份不明的登记会阻塞退役。Windows 可启用 `inspect_windows_processes` 补查进程命令行，仍需核实其他消费者。

项目已采用运行组时，在 `closeout.runs` 设置 `root` 和 `retention_days`。可用 `runtime` 指向目标项目内已部署的 `artifact_lifecycle.py`。省略时从文档操作入口相邻目录加载。按实际退出授权填 `release`，每项包含 `id`、`kind`、`owner`、`released_on` 和 `reason`。生命周期仍负责保留、消费状态和数据清理。

有发布回执时，`closeout.handoffs` 可登记待退役交接文件的 `path`、`sha256`、`saved_commit`、`run_id`、`action` 和 `reason`。工具核对回执、主线和 Markdown 引用。用 `closeout.retention` 分类发布目录时，配置登记文件 `path`、`schema_version`、`registry_field`、`rollback_field`、`directories`、`revision_prefix_length` 和 `dir_pattern`。分类结果只进入保留或复核清单。

```text
python -B tools/audit/doc_ops.py closeout-plan --config tools/audit/doc-ops.config.json --out closeout.json
python -B tools/audit/doc_ops.py closeout-apply --config tools/audit/doc-ops.config.json --plan closeout.json
```

先看 `actions`、`blocked`、`retained`、`review`。取得针对这些动作的执行授权后才 apply。执行前工具重算计划，并在各动作前重验。遇 `PLAN_STALE` 重新生成并审查。若有部分完成，沿输出的 `applied` 和 `partial` 核实现场。再次计划时，已退出的动作应消失。
