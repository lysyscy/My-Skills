# My-Skills 项目绑定

## 规则与事实来源

来源仓库 lysyscy/My-Skills。本仓普通方法为 [execution.md](../../skills/implement-solo-spec/references/execution.md)，子 Agent 前读 [delegation.md](../../skills/implement-solo-spec/references/delegation.md)，文档受影响时读 [document-maintenance.md](../../skills/setup-solo-workflow/references/document-maintenance.md)。已固定任务继续原 entry/runtime，不使用候选替代。

当前包结构见 [architecture.md](../architecture.md)；包实现、规则及策略的权威分别是 tools/、skills/ 和 [skill-package.json](../../skill-package.json)。不创建同义需求/授权表。当前维护任务从 Git common dir/workflow-state/runs/ 定位固定状态与证据。

## 检查、隔离与保存

检查以 skill-package.json 的 checks 为准；结构验证器从宿主真实系统路径按 [包操作](../../skills/improve-workflow/references/package-operations.md) 定位。隔离依据 [setup_fixture.py](../../tests/setup_fixture.py)、[test_skill_package.py](../../tests/test_skill_package.py)、[test_manager_sync.py](../../tests/test_manager_sync.py) 的真实夹具。夹具业务只是模拟，所有测试发布与安装限临时本地仓及 FakeManager。

维护授权、远端和分支以清单为唯一来源；本次请求的限制优先。维护入口是 [improve-workflow](../../skills/improve-workflow/SKILL.md)，运行继续固定工具及恢复机制。普通无远端项目的保存分支不改变本包的 origin 保护。

[历史试跑](../archive/2026-10-workflow-trials.md) 仅供追溯，不证明当前部署或其他机器状态。本仓不复制业务项目目录、票号、领域规则和命令。
