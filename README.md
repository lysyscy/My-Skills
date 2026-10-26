# 个人 Agent 工作流

本仓维护单人 Agent 协作的个人技能与共享方法。Matt 原版保持独立；项目各自维护业务、代码、验收与授权。

本仓 Python 工具只用标准库，由 `pyproject.toml` 和 `uv.lock` 管理；运行 `uv sync` 准备环境，项目检查经 `uv run` 执行。

[GitHub Actions](.github/workflows/tests.yml) 在推送和 PR 时运行现有测试，使用 `.python-version` 指定的 Python；只检查，不执行发布、部署或技能同步。

业务技能仅在各业务项目本机维护，不纳入本仓skills目录、Skills Manager中央库或自动发布。开发与跨项目方法继续沿现有管理、验证和同步流程；共享基础工具保持其原渠道。

- [setup-solo-workflow](skills/setup-solo-workflow/SKILL.md)：接入、修复项目绑定及获批的专项文档迁移。
- [implement-solo-spec](skills/implement-solo-spec/SKILL.md)：显式启动或接续实施。普通已授权任务由项目绑定读取同一 [execution.md](skills/implement-solo-spec/references/execution.md)，不必先建规格或拆票；复杂统筹按采用授权触发。
- [improve-workflow](skills/improve-workflow/SKILL.md)：按真实证据复盘；获准个人包维护才验证和保存候选，按权限使用 Git 与 Skills Manager，只读分析止于结论。

- [project-handoff](skills/project-handoff/SKILL.md)：个人维护的交接保存与提醒；完整资源和计数器同源维护，上游来源及许可见技能维护页。

新项目的所有资料、运行数据与开发产物按[固定工作区契约](skills/setup-solo-workflow/references/document-layout.md)分类；结合Matt任务规格/逐票结构，每次授权改动及阶段结束处理相关资料；有效知识归现行主人，Git可追溯且无活动用途的原文默认退出，必要非Git证据与具名历史例外按各自生命周期处理，并通过已触发的收尾检查。老项目按具名消费者迁移，原始数据与在途任务保留边界。

本仓入口见 [工作流绑定](docs/agents/workflow.md)，当前结构见 [架构](docs/architecture.md)。文档受影响时读 [日常维护](skills/setup-solo-workflow/references/document-maintenance.md)，新落点或专项迁移再读对应参考。项目只绑定来源、事实主人、实际验收/隔离/保存机制，不复制通用正文。

维护来源为 [lysyscy/My-Skills](https://github.com/lysyscy/My-Skills)。授权及检查以 [清单](skill-package.json) 为准；维护步骤见 [包操作](skills/improve-workflow/references/package-operations.md)。完整发布同步依次核源与对应CI、官方Manager安装、更新检测及备份远端；跨设备恢复缺少基准时先校准。工具只核验，实际Git发布、Manager更新和备份动作由当前维护者执行。普通新会话仅定位所需规则；旧运行保持固定版本，按当前请求决定是否发布或安装。

[历史试跑](docs/archive/2026-10-workflow-trials.md) 仅在追溯时读取，不证明今天安装、长期速度或Token收益。
