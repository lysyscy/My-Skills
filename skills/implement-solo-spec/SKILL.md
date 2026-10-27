---
name: implement-solo-spec
description: 用于用户显式启动或接续已授权的个人实施；普通项目通过绑定读取共享 execution 参考，按风险验证和唯一收尾，不用于只读分析或拆票。
---

# 个人实施入口

用于用户显式启动或接续已授权的实施范围。输入可以是明确需求、已批准规格或票；不要求每次先创建规格。只读分析不进入实施。

读取 [execution.md](references/execution.md)，作为本次唯一实施与收尾方法。普通项目任务也通过项目入口读取这同一参考，不需要隐式调用本 Skill。

默认为普通改动。只有工作需要跨批依赖、累计集成或项目已明确要求统筹，并且采用依据与授权范围清楚时，才读取 [coordination.md](references/coordination.md)。是否统筹与风险高低分别判断；不将已授权在途统筹静默降级。

涉及重要界面内容取舍、用户阶段验收或交互预览时，读取 [human-collaboration.md](references/human-collaboration.md)。

任何子 Agent 创建前必须读取 [delegation.md](references/delegation.md)；特殊风险、浏览器或环境/失败问题出现时读取 [verification.md](references/verification.md)。没有触发不要读完这些分支。

## 普通改动

现行正文：[execution.md](references/execution.md)。不要再运行一份独立 Matt implement 收尾。

## 输入与分批接续

先用 [execution.md](references/execution.md) 核输入；已授权跨批范围的额外规则在 [coordination.md](references/coordination.md)。

## 模型与推理强度

委派入口：[delegation.md](references/delegation.md)。创建任何调查、实现、审查或修复子 Agent 前必读；Codex 选型按其中指针读取专用规则。

## 验证与失败处理

基础验证和发现关闭在 [execution.md](references/execution.md)；特殊分支在 [verification.md](references/verification.md)。已有有效证据按适用范围复用，不因经过这个入口重复执行。

## 评审

普通任务由Agent按 [execution.md](references/execution.md) 主动选择自查、定向独立审查或完整双轴，包含累计未审改动；统筹任务按 [coordination.md](references/coordination.md) 保留最终独立双轴。主 Agent 负责关闭发现和一次最终回执。

## 整体统筹模式

采用授权明确后读 [coordination.md](references/coordination.md)。

## 主 Agent 的执行循环

跨批推进与集成读 [coordination.md](references/coordination.md)，唯一收尾读 [execution.md](references/execution.md)。

## 动态分派与隔离

分派前读 [delegation.md](references/delegation.md)。

### 外部方法消费边界

参考与完整调用的边界读 [execution.md](references/execution.md)。

### 当次能力发现

实际缺口按执行核心定位同来源 improve-workflow → references/capability-selection.md；不启动复盘。

### 发现关闭与额外审查

发现关闭由 [execution.md](references/execution.md) 的唯一主人处理。

## 项目适配

项目绑定只持有实际事实、验收/隔离/保存机制与例外；普通方法见 [execution.md](references/execution.md)，不复制全局正文、不改变其他在途任务。
