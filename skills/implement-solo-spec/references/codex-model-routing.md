# Codex 子 Agent 模型选型

版本：2026-10-27。仅适用于 Codex；这是个人策略，不是官方能力或用量保证。实际创建子 Agent 或阶段选型时采用当前预设，按运行时真实支持的模型和推理强度显式指定；不可用时选支持且适合任务的配置，无合适配置则说明阻塞，不假称已选。API 可用不等于客户端可用。

目标是任务质量、返工总成本和总体用量；不保证精确等额度，不用 API 单价换算订阅用量，也不设固定模型比例。默认日常；仅有日常和充裕两个预设。用户反馈耗得快、用不完或换套餐时，重新校准这两份内容，不自动切换预设或创建预算控制器。

| 工作 | 日常 | 充裕 |
| --- | --- | --- |
| 机械提取、整理、规则明确的检查 | `gpt-6-luna` / `high` | `gpt-6-luna` / `high`；确需较多判断可用 `xhigh` |
| 简单界面操作、截图核对 | `gpt-6.1-terra` / `medium` | `gpt-6.1-terra` / `high` |
| 已定位局部修复、需要判断的视觉核验 | `gpt-6.1-terra` / `high` | `gpt-6.1-terra` / `high`；复杂视觉可用 `xhigh` |
| 常规代码实施、范围明确的技术分析 | `gpt-6.1-sol` / `medium` | `gpt-6.1-sol` / `high` |
| 疑难定位、复杂业务、跨模块工作、关键审查 | `gpt-6.1-sol` / `high` | `gpt-6.1-sol` / `xhigh`；极难局部才用 `max` |

两套均使用 standard。只有用户明确追求更快交付且工具支持时才用 Fast；Fast 消耗订阅用量为 standard 的 2.5 倍，API/credits 不能推算 included usage。`ultra` 不常规自动选，Astra 继续排除；日常不自动用 `max` 或 `ultra`。

按实际推理难度与业务后果判断风险，而非文件数。直接选适合的执行者，不强制先试便宜档或走 Luna → Terra → Sol 流水线。缺资料、权限或连接时处理缺口，不靠升模型解决。默认一个合适执行者，仅有独立收益才分工；不为调度额外增加审查或双跑。既有委派收益、隔离、独立审查与生命周期规则仍适用。

任务或阶段变化时重新判断；复用同一对话不意味着锁死模型。平台支持时，在空闲或新轮次显式指定 `model` / `thinking`，正常运行中的任务不打断，调整仅对后续生效。长任务仍按现有上下文和交接机制分批，不为节省少量用量反复迁移上下文。

官方参考：[订阅价格](https://learn.chatgpt.com/docs/pricing)、[速度](https://learn.chatgpt.com/docs/agent-configuration/speed)、[模型选择](https://developers.openai.com/api/docs/guides/model-selection)。
