---
name: skill-package-ops
description: 仅在用户明确点名 skill-package-ops 时使用。维护和分发 My-Skills，恢复失效的本地技能来源，或按需评估跨宿主能力与固定版本的技能行为。
disable-model-invocation: true
---

# 技能包维护

仅在用户明确点名本技能时调用。按当前授权选读对应参考，只读任务交付证据和结论。

- 维护或分发 My-Skills 时，在已绑定的 Git 仓编辑唯一维护源。按[维护与分发规范](references/package-operations.md)核对结构、行为、对应提交的 CI、Skills Manager 安装与部署、备份远端。中央库和各宿主副本用于分发。
- 本地技能的来源路径丢失、失效或生成同名副本时，按[本地来源恢复](references/local-source-recovery.md)核定作者目录，保护原登记和部署。
- 现有工具无法满足具体任务时，读[跨宿主能力选择](references/capability-selection.md)，核各宿主实际可用的工具、调用入口和权限。
- 需要验证技能或指令是否改变了行为时，读[行为观察与固定版本对照](references/behavior-evaluation.md)，按实际问题选择轻量观察或严格对照。

日常会话复盘用 pstack 的 `reflect`，反复发生的实施错误交给 `correct`，按当前宿主的技能入口调用。如果 `reflect` 发现应由 My-Skills 维护的改进，指回 `skill-package-ops`，获准后修同一维护源，避免在项目里另建同义技能。
