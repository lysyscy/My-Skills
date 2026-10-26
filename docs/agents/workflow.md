# My-Skills 项目绑定

## 规则与事实来源

来源仓库 lysyscy/My-Skills。本仓普通方法为 [execution.md](../../skills/implement-solo-spec/references/execution.md)，子 Agent 前读 [delegation.md](../../skills/implement-solo-spec/references/delegation.md)，文档受影响时读 [document-maintenance.md](../../skills/setup-solo-workflow/references/document-maintenance.md)。已固定任务保持原规则、版本与授权。

当前包结构见 [architecture.md](../architecture.md)；核验实现、规则及清单的权威分别是 tools/、skills/ 和 [skill-package.json](../../skill-package.json)。本轮范围、固定版本、验证及未决项留在任务已有记录；不建立发布状态机。旧运行的 Git common dir/workflow-state/runs/ 原位保留。

## 检查、隔离与保存

检查以 skill-package.json 的 checks 为准；结构验证器从宿主真实系统路径按 [包操作](../../skills/improve-workflow/references/package-operations.md) 定位。隔离依据 [setup_fixture.py](../../tests/setup_fixture.py)、[test_skill_package.py](../../tests/test_skill_package.py)、[test_manager_sync.py](../../tests/test_manager_sync.py) 和 [test_distribution.py](../../tests/test_distribution.py)。所有测试写入限临时本地仓及夹具目录；Manager fake 仅响应查询，实际文件缺失、陈旧、独有修改和错误来源必须使核验失败。分发用本地裸仓和接收端克隆覆盖CI失败、未推送备份、unknown状态和恢复后缺少基准的校准边界。

维护授权、远端和分支以清单为唯一来源；本次请求的限制优先。维护入口是 [improve-workflow](../../skills/improve-workflow/SKILL.md)。完整发布按包操作核源、CI、Manager更新、真实部署、更新检测及备份远端；候选阶段止于隔离分支。普通无远端项目的保存分支不改变本包的 origin 保护。

[历史试跑](../archive/2026-10-workflow-trials.md) 仅供追溯，不证明当前部署或其他机器状态。本仓不复制业务项目目录、票号、领域规则和命令。

## 共享记忆身份

本仓及其维护工作树固定使用 `project-d1109f2e2837a7f2`。个人技能的采用背景和维护经验归该项目库；跨项目长期偏好才进入个人库。当前方法、许可、安装/发布和验收边界仍由本仓技能及清单持有，历史记忆不替代现行版本。
