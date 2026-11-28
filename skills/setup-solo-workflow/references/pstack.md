# 接入 pstack

1. 核对目标宿主实际加载的 pstack 及项目所需技能。采用 `poteto-mode` 时，按当前宿主提供的入口进入。在 `docs/agents/workflow.md` 或项目已有绑定中记录采用来源、版本和实际加载结果。宿主配置由其自身入口维护。
2. 按 [项目工作规则](../templates/project-work.md) 布置从项目入口到开发验证、票库和领域文档的指针。更新时按三方比较移除退役工程技能的导航、专用标签映射和统筹指针。既有票的状态与依赖由原票库维护。已固定任务沿原基线，新工程工作使用 pstack。
3. 需要落盘的 pstack 产物按 [资源模块](../templates/resources.md#pstack-临时产物) 接到项目的登记根和固定运行时。核项目入口的 `register`、`lease` 和 `close --discard-work`，并确认已忽略登记目录。接续另按项目已采用的 `project-handoff` 入口处理。

## 项目验证技能

- **新项目或没有可复用的验证入口。** 用当前宿主的 pstack `/create-verification-skill` 建立 `.agents/skills/verify-<app>/`，从真实入口验证一条完整的用户路径。
- **已有预览或验证工具。** 建立薄层 `.agents/skills/verify-<app>/`，用 `features/*.md` 记录各功能步骤并调用已有命令。启动、清理各沿用现有入口。从真实入口验证一条完整的用户路径。
- **维护。** 路由、选择器、认证、数据前置条件或验证命令变化时，调用宿主的 pstack `/maintain-verification-skill` 核对受影响的验证步骤。
