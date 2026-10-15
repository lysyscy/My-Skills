# 当前个人包结构

开发与跨项目方法的三个技能目录及技能内参考在 skills/；独立资源随所属技能分发，discover 只发现含 SKILL.md 的目录。普通实施核心是 implement-solo-spec/references/execution.md；统筹、委派与专项验证按各自触发读取。setup 拥有日常文档方法、统一目录职责及专项迁移；improve 拥有候选归属、能力选择和个人包维护核验。

skill-package.json 是授权、远端、分支、依赖保护及检查的唯一配置。tools/skill_package.py 只提供 structure、preflight 和 confirm-install。结构检查调用宿主验证器；安装核验只查询 Skills Manager、读取真实文件与 Git 对象。根工具不随独立技能安装，普通规则读取不依赖它，也不假设跨技能物理相邻。

improve-workflow/references/behavior-evaluation.md 拥有按需行为对照协议；setup-evaluation 保留接入场景、夹具与保护条件，通过同来源定位复用协议，不新增运行器或状态机。

源修改按风险验证，经普通 Git 提交、整合和推送；Skills Manager 负责更新、部署及跨设备备份。更新前输出的 JSON 只保存本轮预期来源与选择，更新后以同一提交核对完整资源、技能身份及部署集合；工具不保存运行状态、不写中央库、不创建链接、不清理源修改。必要记录留在当前任务，既有 Git common dir/workflow-state/runs/ 及其执行快照不因本次退役旧接口而变动。

tests/ 使用标准库 unittest、隔离本地 Git 仓和仅查询的 FakeManager；真实文件变化由夹具构造。测试覆盖保留的核验契约及接入/迁移保护，已退役的发布与安装编排不再作为新接口验收。结构、语义、夹具行为与真实宿主/安装效果分别证明。历史材料保留在 docs/archive/。
