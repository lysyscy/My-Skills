# 维护与来源

本技能为个人维护版本，唯一源码为[lysyscy/My-Skills的skills/project-handoff](https://github.com/lysyscy/My-Skills/tree/main/skills/project-handoff)。运行、保存及接续仍按SKILL.md；仅修改或发布本技能时读取本页。

先读实际安装的 `manage-skills`，核 Skills Manager 登记来源、技能 ID 与已有部署。只在上述维护源修改。一起核验完整资源、共享计数脚本与根 `tests/` 中的两组回归。定位同源 `skill-package-ops` 的 `references/package-operations.md`，按其规则保存源、核对应 CI，用官方 Manager 更新并验证安装与备份。中央库及 Agent 副本用于分发。

本机原project-handoff ID沿用，来源迁移不创建同名第二个技能，不改变preset、标签或部署选择。更新仍用Manager，不手改元数据。安装文件一致、真实宿主加载、最终文本核验及另一实体设备分别报告；更新技能不代表/hooks原生信任或真实提醒链已经验收。

上游来源是[duoduoler-ops/Table-skills](https://github.com/duoduoler-ops/Table-skills)，采用MIT许可，完整许可见[upstream-license.txt](upstream-license.txt)。本技能仅在上述个人维护源更新，上游用于来源追溯，不自动双向同步。
