# 当前个人包结构

开发与跨项目方法的三个技能目录及技能内参考在 skills/；独立资源随所属技能分发，discover 只发现含 SKILL.md 的目录。普通实施核心是 implement-solo-spec/references/execution.md；统筹、委派与专项验证按各自触发读取。setup 拥有日常文档方法、统一目录职责及专项迁移；improve 拥有候选归属、能力选择和个人包维护核验。

skill-package.json 是授权、远端、分支、CI工作流、依赖保护及检查的唯一配置。tools/skill_package.py 提供结构、更新前、源发布、本机安装及分发后验。核验读取 Skills Manager、GitHub CI结果、真实文件与Git对象；更新检测会刷新Manager自身检查缓存。工具不执行安装或备份推送。根工具不随独立技能安装，普通规则读取不依赖它，也不假设跨技能物理相邻。

improve-workflow/references/behavior-evaluation.md 拥有按需行为对照协议；setup-evaluation 保留接入场景、夹具与保护条件，通过同来源定位复用协议，不新增运行器或状态机。

源修改按风险验证，经普通Git发布并核对应CI后，由官方Skills Manager更新、部署和推送备份。更新前JSON保存本轮预期来源与选择，安装后核同一提交的资源、身份和部署集合；分发后验再核更新检测、备份远端SHA和提交内真实个人技能。备份不保存版本基准时，显式要求恢复后官方更新校准，不假报原生跨设备提醒正常。必要记录留在当前任务，既有Git common dir/workflow-state/runs/及其执行快照保持原位。

tests/ 使用标准库 unittest、隔离本地 Git 仓和仅查询的 FakeManager；真实文件变化由夹具构造。测试覆盖保留的核验契约及接入/迁移保护，已退役的发布与安装编排不再作为新接口验收。结构、语义、夹具行为与真实宿主/安装效果分别证明。历史材料保留在 docs/archive/。
