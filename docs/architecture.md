# 当前个人包结构

项目环境政策的唯一主人是 setup-solo-workflow/references/environment.md；setup 接入与普通 execution 按触发读取，项目入口保留实际工具/测试契约。环境检查和准备复用原生管理器，不新增环境技能或包根运行依赖。

开发与跨项目方法及个人交接技能目录、技能内参考在 skills/；独立资源随所属技能分发，discover 只发现含 SKILL.md 的目录。普通实施核心是 implement-solo-spec/references/execution.md；统筹、委派与专项验证按各自触发读取。setup 拥有日常文档方法、统一目录职责及专项迁移；随技能分发的scripts/workspace_check.py只读解析固定路径并检查落点、运行退出、任务退出与证据期限，execution在开始/收尾实际调用；improve 拥有会话与Agent工作环境复盘、候选归因和归属、能力选择、自有技能维护源选择及分发核验；日常复盘由自身入口独立完成，外部retro保持原渠道。共享入口在创建、修改或分发自有技能时指向该规范；正常项目业务不触发技能维护，本地来源恢复仅在异常分支读取。

skill-package.json 是授权、远端、分支、CI工作流、依赖保护及检查的唯一配置。tools/skill_package.py 提供结构、更新前、源发布、本机安装及分发后验。核验读取 Skills Manager、GitHub CI结果、真实文件与Git对象；更新检测会刷新Manager自身检查缓存。工具不执行安装或备份推送。根工具不随独立技能安装，普通规则读取不依赖它，也不假设跨技能物理相邻。

improve-workflow/references/behavior-evaluation.md 拥有按需行为对照协议；setup-evaluation 保留接入场景、夹具与保护条件，通过同来源定位复用协议，不新增运行器或状态机。

发布与安装链的唯一方法由[包操作](../skills/improve-workflow/references/package-operations.md)持有，工具只核验各阶段证据。必要记录留在当前任务，既有Git common dir/workflow-state/runs/及其执行快照保持原位。

setup 的[documentation](../skills/setup-solo-workflow/references/documentation.md)持有文档读者、权威与内容分工，裁剪采用Diátaxis、arc42、ADR和随变更维护实践；document-layout持有物理位置及产物生命周期，document-maintenance负责日常同步。implement消费受影响资料并统一收尾，improve从实际阅读/维护问题判断是否需要重构，不建立另一套流程。

project-handoff自带Codex/Claude生命周期适配器及模板，状态只归各宿主session，不与业务数据或包发布记录混用；根tests中的project-handoff和Claude回归消费同一维护源，运行事件均限隔离状态。

共同自定义指令维护源为 skills/setup-solo-workflow/references/agent-instructions.md，随既有技能包分发；各端自定义指令消费同一正文，宿主专用约束保留于其适配。setup 的 memory-adoption.md 持有接入与首次内容迁移，execution 在自然收尾引用共同政策，不维护第二份记忆制度。

tests/ 使用标准库 unittest、隔离本地 Git 仓和仅查询的 FakeManager；真实文件变化由夹具构造。测试覆盖保留的核验契约及接入/迁移保护，已退役的发布与安装编排不再作为新接口验收。结构、语义、夹具行为与真实宿主/安装效果分别证明。历史材料保留在 docs/archive/。
