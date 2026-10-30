# 维护与贡献

本仓维护个人 Agent 方法与随技能分发的资源。项目结构见[架构](docs/architecture.md)，业务技能由各业务项目维护；外部原版保持原渠道。按当次范围修改，不把项目业务规则或固定命令搬进通用方法。

## 开发与检查

Python 工具只用标准库，由 [pyproject.toml](pyproject.toml)、[uv.lock](uv.lock) 和 [.python-version](.python-version) 管理；用 `uv sync` 准备环境，经 `uv run` 执行。检查命令以 [skill-package.json](skill-package.json) 为准。[GitHub Actions](.github/workflows/tests.yml) 在推送和 PR 时运行检查，不执行发布、部署或技能同步。

隔离依据现有 [setup 夹具](tests/setup_fixture.py)、[包核验](tests/test_skill_package.py)、[Manager核验](tests/test_manager_sync.py)和[分发测试](tests/test_distribution.py)。测试写入限临时本地仓及夹具目录，Manager fake 只响应查询；实际文件缺失、陈旧、独有修改和错误来源必须被拒绝。分发测试使用本地裸仓与接收端克隆，覆盖 CI 失败、未推送备份、unknown 和恢复校准边界。

## 修改技能与文档

普通实施与唯一收尾按 [execution](skills/implement-solo-spec/references/execution.md)，文档修改按[日常维护](skills/setup-solo-workflow/references/document-maintenance.md)；新落点或专项迁移再读取所属参考。指令写作使用实际安装的 writing-for-agents。实现前与审查时按内容读取[架构](docs/architecture.md)、本次需求及相关技能正文；本仓不另复制一份通用编码规范。

技能运行所需规则、脚本和参考保留在所属技能内，避免安装单个技能后丢失依赖。需要验证行为变化时按[轻量观察与严格对照的分支](skills/improve-workflow/references/behavior-evaluation.md)取证，文件与结构通过不代替真实消费效果；已固定运行保留原基线。

## 保存与分发

授权、远端、发布分支及 CI 以 [skill-package.json](skill-package.json) 为唯一配置，本次请求优先。维护源选择、源保存、CI、Skills Manager 更新/部署及备份后验沿[包操作](skills/improve-workflow/references/package-operations.md)执行；根工具只核验，不代替实际分发。中央库或 Agent 副本不作为第二编辑源。

项目方法绑定、记忆身份和旧运行例外见[workflow](docs/agents/workflow.md)。历史试跑仅供追溯，不证明当前安装、实体设备或业务验收。
