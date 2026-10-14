# 个人 Agent 工作流

本仓维护单人 Agent 协作的个人技能与共享方法。Matt 原版保持独立；项目各自维护业务、代码、验收与授权。

- [setup-solo-workflow](skills/setup-solo-workflow/SKILL.md)：接入、修复项目绑定及获批的专项文档迁移。
- [implement-solo-spec](skills/implement-solo-spec/SKILL.md)：显式启动或接续实施。普通已授权任务由项目绑定读取同一 [execution.md](skills/implement-solo-spec/references/execution.md)，不必先建规格或拆票；复杂统筹按采用授权触发。
- [improve-workflow](skills/improve-workflow/SKILL.md)：按真实证据复盘；获准个人包维护才进入固定版本的包事务，只读分析止于结论。

本仓入口见 [工作流绑定](docs/agents/workflow.md)，当前结构见 [架构](docs/architecture.md)。文档受影响时读 [日常维护](skills/setup-solo-workflow/references/document-maintenance.md)，新落点或专项迁移再读对应参考。项目只绑定来源、事实主人、实际验收/隔离/保存机制，不复制通用正文。

维护来源为 [lysyscy/My-Skills](https://github.com/lysyscy/My-Skills)。授权及检查以 [清单](skill-package.json) 为准；具体事务与恢复见 [包操作](skills/improve-workflow/references/package-operations.md)。My Skills 拥有维护源，Skills Manager 拥有中央库和 Agent 分发。普通新会话仅定位实际需要的规则，不自动更新或部署；在途运行保持固定 entry/runtime。

[历史试跑](docs/archive/2026-10-workflow-trials.md) 仅在追溯时读取，不证明今天安装、长期速度或Token收益。
