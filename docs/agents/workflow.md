# My-Skills 项目绑定

## 规则与事实来源

来源仓库 lysyscy/My-Skills；本仓采用来源为本仓同一Git检出中的技能与模板；项目正文是本仓实际采用版本。普通工作按本项目 CONTRIBUTING 与适用专题；宿主规则单独布置并核实际加载，模板文件存在不代表部署完成。已固定任务保持原规则、版本与授权。

当前包结构见 [architecture.md](../architecture.md)；核验实现、规则及清单的权威分别是 tools/、skills/ 和 [skill-package.json](../../skill-package.json)。本轮范围、固定版本、验证及未决项留在任务已有记录；不建立发布状态机。Git common dir 下的固定旧运行按[接续与退役规则](../../skills/improve-workflow/references/package-operations.md#失败并发与旧运行)保留或退出。

## 全局指令由 Magpie 管理

2026-11-11 按用户要求，Codex、DSH、MiniMax Code 与 WorkBuddy 的全局指令管理和分发移交 Magpie Library → Instructions。活动指令集为 `Shared agent instructions`：共同正文关联本仓 [host-rules.md](host-rules.md)，各宿主附加正文由 Magpie 的对应 Agent 附加内容维护。共同源仍由 Git 保留版本；在 Magpie 编辑关联正文会写回该文件。

更新时先读取 Magpie 活动集合、关联文件及目标宿主现有有效指令。共同规则可通过 Magpie 或关联源编辑；宿主差异在 Magpie 的附加内容中修改，通过 Magpie 同步。核目标文件受管段只有一份、内容与来源一致，并区分文件同步与宿主实际加载。项目自己的 AGENTS.md、技能分发与 Hindsight 的职责不变。

原 [host-adapters.md](host-adapters.md) 仅保留移交时的历史快照，`tools/host_instructions.py` 仅保留为旧文本的只读比较工具；二者不再生成或部署现行全局指令。未来调整规则内容仍按当前请求和维护授权进行，不从旧快照恢复覆盖 Magpie 的有效增量。

首次移交已核 Codex、DSH 的有效正文与迁移前相同，保留各自适配；Codex 本次会话已重新加载受管入口。随后按用户明确要求，MiniMax 清空旧自由内容和附加内容，只采用当前共同规则；WorkBuddy 采用共同规则及两条附加偏好：Python 依赖优先沿项目既有 uv 配置，包源遵循锁文件和明确配置；会话结束不自动打开生成文件。两端自由内容已清空，WorkBuddy 其他设置保持原样。Magpie 原生备份和本次迁移证据保留恢复依据；其余客户端未扩展分发。

## 检查、隔离与保存

开发检查与隔离入口见[贡献指南](../../CONTRIBUTING.md)。结构验证器从宿主真实系统路径按[包操作](../../skills/improve-workflow/references/package-operations.md)定位；不从普通项目的工作目录猜测安装路径。

维护入口是 [improve-workflow](../../skills/improve-workflow/SKILL.md)，保存与分发从[贡献指南](../../CONTRIBUTING.md)进入包操作。普通无远端项目的保存分支不改变本包的 origin 保护；候选阶段止于获准的候选范围。

本仓不复制业务项目目录、票号、领域规则和命令。

## 共享记忆身份

本仓及其维护工作树固定使用 `project-d1109f2e2837a7f2`。个人技能的采用背景和维护经验归该项目库；跨项目长期偏好才进入个人库。当前方法、许可、安装/发布和验收边界仍由本仓技能及清单持有，历史记忆不替代现行版本。

## 已接入的个人产物生命周期

2026-10-30 采用个人包 `e1ab206` 的旧运行区；2026-11-11 切换本项目新开发产物到项目内固定运行时，版本以部署清单为准。操作、旧根及调度边界见[产物接入](../guides/artifact-lifecycle.md#本项目实际接入)，固定旧任务从[资源入口](../guides/workspace-lifecycle.md)选路。
