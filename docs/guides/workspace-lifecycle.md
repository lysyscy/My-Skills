# My-Skills 资源与验证边界

源码、技能资源及持久测试归原工程目录；活动 Markdown 在 .scratch/<effort>。可重建中间件用系统临时 API，结项即退出；有具名后续用途的日志、报告等从[本项目产物接入](artifact-lifecycle.md#本项目实际接入)登记。固定旧运行的接续或退役沿[项目绑定](../agents/workflow.md#规则与事实来源)。

测试仅使用临时本地仓和夹具，Manager fake 不写实际中央库；需要真实发布/安装时按 package-operations 的独立授权分支执行。业务项目、真实凭据与已安装技能不是测试可写目标。隔离检出仅隔离文件变化，不自动证明访问权限隔离。

用途结束后先核消费者与恢复依据，再退出本任务临时资源；保留候选、未归因失败与待复核材料。新登记证据的30/60天和保护状态沿上述接入入口。仅未迁移旧生产者和固定旧运行继续使用 .artifacts/active/<effort>/<run>，必要原始证据选留到 .artifacts/archive/<effort>/<run>；旧 retention.json 的 reason 和 expires_on 仍采用原日期格式及最长30天检查，不写入新60天或带时间截止值。到期处置沿当次权限，不承诺后台自动清理；可达Git足够恢复时不复制整棵现场。

新登记产物用上述接入入口的 check 只读核验。旧目录分支才使用 `uv run python skills/setup-solo-workflow/scripts/workspace_check.py check --root <项目根> --effort <effort> --phase active`，旧运行或任务退出分别用 run-closed（含 --run）或 closed。检查不代替删除授权、用途判断或实际资源退出。简单任务没有相关产物时不创建空运行目录。

任务文件退出独立执行 `uv run python skills/setup-solo-workflow/scripts/task_files.py --root <项目根> --path .scratch/<effort> --revision <已保存提交>`，散置本任务票用重复 `--path` 指定；处置完成后加 `--closed`，核残留与仓内引用。检查边界及具名保留沿技能[目录规则](../../skills/setup-solo-workflow/references/document-layout.md#任务文件退出核查)，与新登记或旧运行选路无关。
