# 布置模块

模板只在接入/更新时读取。项目采用的内容进入现有项目入口，并记录采用来源与版本。日常任务不回读模板。

| 模板 | 目标与适用条件 |
|---|---|
| [项目工作规则](project-work.md) | 项目 AGENTS/CONTRIBUTING。按动作指向实际规则和验证入口。 |
| [数据验证](data-verification.md) | 涉及数据写入、金额、事务或恢复的项目验证指南。 |
| [预览](preview.md) | 有界面预览与人工验收入口的项目。 |
| [资源](resources.md) | 有临时运行、生成产物或共享资源的项目。包含 pstack 临时产物的接入段落。 |
| [文档操作配置](doc-ops.config.example.json) | 需要校验项目票、生成状态页或计划阶段收尾时，按 [文档操作](../references/doc-ops.md) 配置。 |
| [目录清单](directory-manifest.example.json) | 要声明目录归属、保留和可清理范围时，按 [目录治理](../references/directory-governance.md) 配置。 |
| [Oxlint](oxlintrc.example.json) 和 [Ruff](ruff-pyproject.example.toml) | 按项目语言选用，并按 [代码守卫](../references/code-guardrails.md) 接入提交与 CI。 |

采用 pstack 的项目按 [项目验证技能](../references/pstack.md#项目验证技能) 复用或补建验证入口。

不要全部复制。先复用项目已有内容，缺什么补什么；未解析占位符不能成为有效部署。专项技能仍在各自安装包中，不随项目铺开一份技能手册。

更新采用三方比较：旧模板/新模板/项目现状。模板删除某段不意味着可以删除项目独有规则。首次缺旧基线时先核归属；无变化不改文件。自动检查只核可判定条件，不冒称已证明模型遵守文本。

上述三个工具模块可独立部署。用 [工具部署器](../scripts/deploy_workflow_tools.py) 指定 `--project <项目根> --revision <已验证的完整源提交> --module <模块>`，可重复传 `--module`。模块名为 `doc-ops`、`directory-governance` 和 `code-guardrails`。默认预览，加 `--apply` 才写入 `tools/audit/`。每个模块的部署记录绑定源版本及文件摘要。项目配置和模板采用由各项目维护。保留独有修改并先解决冲突，再重新计划。

无项目任务可将资源模块部署到宿主约定的按需入口；仅新增运行产物时消费。该入口须指向实际已登记个人运行区与可用工具；尚未接入时说明并保留现状，不把模板存在当作接入完成，也不使普通任务回读模板。

早期的 [宿主共同规则模板](host-instructions.md) 供沿用旧版的固定任务查阅。当前宿主全局规则由独立的宿主维护入口管理。
