# 当前个人包结构

setup-solo-workflow/references/environment.md 是环境接入方法；本项目环境与测试契约由 CONTRIBUTING 及实际依赖配置持有。环境检查和准备复用原生管理器，不新增环境技能或包根运行依赖。

`skills/` 持有可独立分发的操作技能。setup 负责接入和获批更新，模板是分发输入，日常工作按项目与宿主实际采用的规则执行。`workspace_check.py` 负责只读路径与退出核验，项目选择适用的生命周期与调用方式。`skill-package-ops` 持有包维护规则及按需评估资料。

skill-package.json 是授权、远端、分支、CI工作流、依赖保护及检查的唯一配置。tools/skill_package.py 提供结构、更新前、源发布、本机安装及分发后验。核验读取 Skills Manager、GitHub CI结果、真实文件与Git对象；更新检测会刷新Manager自身检查缓存。工具不执行安装或备份推送。根工具不随独立技能安装，普通规则读取不依赖它，也不假设跨技能物理相邻。

[行为观察与严格对照](../skills/skill-package-ops/references/behavior-evaluation.md)用于按需验证技能行为。setup-evaluation 保留接入场景、夹具与保护条件，通过同源技能定位行为对照方法。

发布、安装核验及固定旧运行退役沿[包操作](../skills/skill-package-ops/references/package-operations.md)执行，工具只核验各阶段证据。必要记录留在当前任务。

setup 的 documentation、document-layout 和 document-maintenance 是接入及方法维护资料，按实际职责生成项目规则。普通运行由项目 CONTRIBUTING 与专题指南持有。

project-handoff自带Codex/Claude生命周期适配器及模板，状态只归各宿主session，不与业务数据或包发布记录混用；根tests中的project-handoff和Claude回归消费同一维护源，运行事件均限隔离状态。

本机宿主规则的维护和部署归 [Magpie 全局指令入口](agents/workflow.md#全局指令由-magpie-管理)。项目规则由 setup 按采用的版本和本地适配布置。memory-adoption.md 只负责首次接入/迁移，Hindsight 不承担正式规则发布。

tests/ 使用标准库 unittest、隔离本地 Git 仓和仅查询的 FakeManager；真实文件变化由夹具构造。测试覆盖保留的核验契约及接入/迁移保护，已退役的发布与安装编排不再作为新接口验收。结构、语义、夹具行为与真实宿主/安装效果分别证明。历史材料保留在 docs/archive/。

个人产物生命周期的已批准默认规则与工具接口归 setup/references/artifact-lifecycle.md；artifact_lifecycle.py 只处理显式接入的专用输出区。workspace_check 保持只读，新增登记与旧目录检查分别进入；实际项目接入、调度、通知与旧材料处置独立授权。
