# Impeccable过程产物适配

用于已采用项目内runs布局的项目。外部Impeccable保持原安装来源；本适配随setup部署，日常从项目固定版本运行。PRODUCT.md、DESIGN.md、design.json、surfaces、共享配置、critique/ignore.md及live会话恢复状态由原主人维护，不纳入限期清理。

## 开始与消费

Agent在写第一份过程产物前，按本任务选最小原生路径。优先使用mocks/review/prototypes下的任务子目录；critique可以使用计算出的快照文件名，或仅在没有旧快照时声明整个critique目录。questions按需要声明；.gitignore和critique/ignore.md原位保留。已有非空输出、链接和其他活动任务占用的路径会拒绝接管，先找原owner，不以新任务重新起算旧材料。

从项目根调用（Python与项目根由实际环境提供）：

```text
python -B tools/_vendor/setup_solo_workflow/impeccable_artifacts.py --project <项目根> start --group <任务标识> --owner <负责人> --path .impeccable/mocks/<任务标识>
python -B tools/_vendor/setup_solo_workflow/impeccable_artifacts.py --project <项目根> exec --group <任务标识> -- <原生Impeccable或预览命令>
```

start自动登记运行和原生路径归属；exec自动登记当前命令的消费并保留退出码，环境变量IMPECCABLE_ARTIFACT_RUN为受管运行目录。Agent自身的文件/图像工具输出只写已经声明的路径。运行保持active，不因单条命令成功或失败自动结束。原生工具仍能在原位置读取评审和设计稿；正常产物写入不要求用户手工登记每个文件。

所有独立预览/辅助进程分别经exec持有消费至进程真正结束；禁止用后台启动器返回来代替预览退出。无法覆盖的子进程、浏览器中仍供用户验看的页面或未知占用，沿项目hold保护，核实用途结束前不finish。exec只跟踪自己等待的命令，不声称能发现任意外部消费者。读取已封存证据使用exec的--read选项和返回的evidence路径，不恢复旧任务或延长保留期。

## 用途结束

先完成必要设计判断、将采用的决定归正式正文，核人和进程均已结束消费。critique只有原生closed:true才允许收尾；原生close本身不等于生命周期结项。Agent调用：

```text
python -B tools/_vendor/setup_solo_workflow/impeccable_artifacts.py --project <项目根> finish --group <任务标识> --confirmed --days 30
```

--confirmed是负责人对用途结束的确认，不要求每次再询问用户；是否已有授权沿本次任务和项目规则。finish在生命周期互斥锁内核活动/未知消费者，将声明的原生输出按相对路径与散列移入本run/evidence，再封存30天。永久标记原位保持；独有原件、正式交付或待验收资产须先归其主人，不可通过本入口宣布可丢弃。普通异常保留active，恢复时核原绑定继续，不自动认定失败输出可弃。

部分搬移留下collecting清单，已移动项保持散列；重试只继续匹配的剩余项。任一新文件、内容变化、缺件、链接或仍活动消费者都会拒绝结束，保留现场供原负责人处理。已有陈旧资料不由本入口迁移；按当次单独授权逐组核实后清理。

## 接入与验证

setup部署同时携带artifact_lifecycle.py和impeccable_artifacts.py；项目在设计入口增加本节的条件指针。先用合成任务核原生写入、命令消费、未关闭评审拒绝、占用拒绝、收尾后的原生路径退出与证据期限；部署幂等、旧版升级及本地修改保护沿现有部署器检查。不新建调度器，也不让调度直接遍历.impeccable。
