# smyw 过程产物适配

用于已采用项目内 runs 布局、且本次获准接入的项目。外部 `smyw` 沿 Skills Manager 的原上游更新，不改写其技能文件或脚本；本适配随 setup 固定版本部署。仅使用实际安装的 `smyw` 入口和脚本，原技能的其他交互与反馈步骤保持。

## 开始、构建与反馈

在写本次第一份规格前，从项目根调用项目已部署的适配器，`<smyw技能目录>`取当前宿主实际加载的安装目录：

```text
python -B tools/_vendor/setup_solo_workflow/smyw_artifacts.py --project <项目根> start --group <任务标识> --owner <负责人> --skill <smyw技能目录>
python -B tools/_vendor/setup_solo_workflow/smyw_artifacts.py --project <项目根> build --group <任务标识> --skill <smyw技能目录>
python -B tools/_vendor/setup_solo_workflow/smyw_artifacts.py --project <项目根> apply --group <任务标识> --skill <smyw技能目录> --feedback feedback-v<N>.md
```

`start` 返回已登记的工作目录和 `spec.json` 路径。将规格、原型、预览、原样反馈与版本文件放在这个目录；此项目规则替代上游示例的项目根 `.smyw/<任务>` 落点，不改上游实现。运行保持 active，浏览器中仍在查看、等反馈或有未吸收意见时不得结项。`build`、`apply` 在登记的消费期内调用当前安装脚本，保留其输出和退出码；`apply --dry-run` 保留原有预检能力。其他独立生成或预览进程用 `exec --group <任务标识> -- <命令>` 持有消费；该命令的 `SMYW_ARTIFACT_DIR` 指向工作目录。外部浏览器和未登记消费者不会被自动发现，由负责人确认用途结束。

## 上游更新

`start`、`build`、`apply` 每次先在系统临时目录用合成数据核对当前安装版本：指定规格目录构建单文件预览、反馈补丁回写及生成旧版规格。兼容的上游更新无需修改适配器或重新固定上游版本；脚本缺失、输出契约变化或检查期间发生更新时拒绝操作，保留活动草稿，先检查新版本再更新适配。不要在一次操作执行期间同时更新技能；本检查不是对上游内容安全性或全部功能的审计。

## 结束与旧预览

已采用的决定先归项目需求和代码；独有反馈、待验收与有效恢复材料先归相应主人。负责人确认用户和所有消费者结束后运行：

```text
python -B tools/_vendor/setup_solo_workflow/smyw_artifacts.py --project <项目根> finish --group <任务标识> --confirmed
```

`--confirmed` 是负责人确认用途结束，不新增例行用户确认。运行按 `work` 结项并立即具备清理资格，实际删除仍由已接入的生命周期清理入口完成；不得声称已经删除。需要具名后续用途的最小证据另按项目规则登记，不能因进程退出或完成构建而结束用户仍在查看的预览。

旧 `.smyw` 文件不由适配器自动认领、移动或清理。先核用户反馈、数据敏感性、当前用途与实际消费者；处理仅作用已确认范围，原始业务资料及其他任务保护。
