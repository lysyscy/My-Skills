# My-Skills 资源与验证边界

源码、技能资源及持久测试归原工程目录；活动 Markdown 在 .scratch/<effort>，运行日志/报告/临时检出在 .artifacts/active/<effort>/<run> 的 logs/reports/work 等分类。已固定的 .git/workflow-state 旧运行保持原位。

测试仅使用临时本地仓和夹具，Manager fake 不写实际中央库；需要真实发布/安装时按 package-operations 的独立授权分支执行。业务项目、真实凭据与已安装技能不是测试可写目标。隔离检出仅隔离文件变化，不自动证明访问权限隔离。

用途结束后先核消费者与恢复依据，再退出本任务work/进程/工作树；保留候选、未归因失败与待复核材料。必要原始证据只选留最小集合到 .artifacts/archive/<effort>/<run>，retention.json 写明 reason 和 expires_on，最长30天；到期处置沿当次权限，不承诺后台自动清理。可达Git足够恢复时不复制整棵现场。

相关路径/运行退出检查使用本仓已有工具：`uv run python skills/setup-solo-workflow/scripts/workspace_check.py check --root <项目根> --effort <effort> --phase active`，运行或任务退出分别用 run-closed（含 --run）或 closed。检查只读，不代替删除授权、用途判断或实际资源退出。简单任务没有相关产物时不创建空运行目录。
