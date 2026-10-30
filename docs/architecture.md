# 当前个人包结构

setup-solo-workflow/references/environment.md 是环境接入方法；本项目环境与测试契约由 CONTRIBUTING 及实际依赖配置持有。环境检查和准备复用原生管理器，不新增环境技能或包根运行依赖。

skills/ 持有可独立分发的操作技能；implement-solo-spec 是短实施流程与跨票统筹参考。setup 负责接入和获批更新，templates/ 是分发输入，项目与宿主部署副本才是日常规则。普通任务直接消费项目已采用规则。workspace_check.py 仍为只读路径/退出核验器；项目采用具体生命周期和调用方式。improve 持有复盘、改进取舍与包维护，不重复普通实施流程。

skill-package.json 是授权、远端、分支、CI工作流、依赖保护及检查的唯一配置。tools/skill_package.py 提供结构、更新前、源发布、本机安装及分发后验。核验读取 Skills Manager、GitHub CI结果、真实文件与Git对象；更新检测会刷新Manager自身检查缓存。工具不执行安装或备份推送。根工具不随独立技能安装，普通规则读取不依赖它，也不假设跨技能物理相邻。

improve-workflow/references/behavior-evaluation.md 拥有按需行为对照协议；setup-evaluation 保留接入场景、夹具与保护条件，通过同来源定位复用协议，不新增运行器或状态机。

发布与安装链的唯一方法由[包操作](../skills/improve-workflow/references/package-operations.md)持有，工具只核验各阶段证据。必要记录留在当前任务，既有Git common dir/workflow-state/runs/及其执行快照保持原位。

setup 的 documentation、document-layout 和 document-maintenance 是接入及方法维护资料，按实际职责生成项目规则；普通运行由项目 CONTRIBUTING 与专题指南持有。improve 在复盘发现具体问题时读取相应方法，不把普通项目工作重新导入接入流程。

project-handoff自带Codex/Claude生命周期适配器及模板，状态只归各宿主session，不与业务数据或包发布记录混用；根tests中的project-handoff和Claude回归消费同一维护源，运行事件均限隔离状态。

共享规则模板为 skills/setup-solo-workflow/templates/host-instructions.md，包含跨项目调用边界和已有记忆政策；宿主部署前保留旧入口。项目更新采用来源版本与本地适配，setup 只布置适用模块。memory-adoption.md 只负责首次接入/迁移，Hindsight 不承担正式规则发布。

tests/ 使用标准库 unittest、隔离本地 Git 仓和仅查询的 FakeManager；真实文件变化由夹具构造。测试覆盖保留的核验契约及接入/迁移保护，已退役的发布与安装编排不再作为新接口验收。结构、语义、夹具行为与真实宿主/安装效果分别证明。历史材料保留在 docs/archive/。

个人产物生命周期的已批准默认规则与工具接口归 setup/references/artifact-lifecycle.md；artifact_lifecycle.py 只处理显式接入的专用输出区。workspace_check 保持只读，新增登记与旧目录检查分别进入；实际项目接入、调度、通知与旧材料处置独立授权。
