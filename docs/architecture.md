# 当前个人包结构

三个技能目录及技能内参考在 skills/；独立资源随所属技能分发，discover 只发现含 SKILL.md 的目录。普通实施核心是 implement-solo-spec/references/execution.md；统筹、委派与专项验证按各自触发读取。setup 拥有日常文档方法、统一目录职责及专项迁移；improve 拥有候选归属、能力选择和包事务。

skill-package.json 是授权、远端、分支、依赖保护及检查的唯一配置。tools/skill_package.py 处理运行快照、验证、发布与 Skills Manager 分发确认；根工具不随独立技能安装。普通规则读取不依赖工具，也不假设跨技能物理相邻。

improve-workflow/references/behavior-evaluation.md 拥有按需行为对照协议；setup-evaluation 保留接入场景、夹具与保护条件，通过同来源定位复用协议，不新增运行器或状态机。

固定运行位于 Git common dir/workflow-state/runs/：state.json 承担恢复；source-snapshot、execution 和 upstream-inputs 保存原件、旧执行与上游输入。verify 比较授权与内容摘要，必要时运行候选和冻结原回归；发布与安装分开确认。既有运行的工具和测试不因候选修改而变化。

tests/ 使用标准库 unittest、隔离本地 Git 仓和 FakeManager。结构、语义、夹具行为与真实宿主/安装效果分别证明。历史材料退出普通入口，存入 docs/archive/，不当作现行规则。
