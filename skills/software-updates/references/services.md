# 服务与技能更新入口

具体服务的版本路径、启动方式、验收、备份和清理规则由其 README 及所指专题文档持有。先按目标读取对应入口，再使用技能的选版口径与[更新收尾](completion.md)；获当次授权后才执行写入、启停或分发。

## Hindsight 本机服务

维护入口：`D:\services\hindsight\README.md`。通过当前服务的 `openapi.json` 核 API 版本，管理页面版本另行核对；安装、运行和登记状态分别报告。

从实际部署识别发行渠道。本机 API 渠道为 [hindsight-api-slim](https://pypi.org/project/hindsight-api-slim/)，管理页为 [@vectorize-io/hindsight-control-plane](https://www.npmjs.com/package/@vectorize-io/hindsight-control-plane)；[官方更新日志](https://hindsight.vectorize.io/changelog)用于判断变更影响。只有实际部署渠道存在目标版本时才列升级候选。

默认分别检查 API、管理页的发行更新及当前版本依赖的兼容稳定候选。实际 Python、npm 锁和生效环境由 README 定位。API 的独立依赖按有效约束取可用的最新稳定版本。管理页先核启动器实际加载的构建和依赖。若启动的是上游发行包内的 standalone，则其中捆绑的依赖随该发行包维护。没有更高的有效发行版且外围 npm 锁变化没有实际消费者时，归「无需更新」。升级时按 README 保护切换期间新增记忆、完成相应隔离验证与实际加载验收，迁移管理和备份入口，再处理已解除回退需要的材料。历史升级回执只作证据，不当作下一版本的操作命令。

## Hindsight 客户端集成

从已接入 harness 的实际配置定位集成入口和包版本，核 [@vectorize-io/hindsight-coding-agents](https://www.npmjs.com/package/@vectorize-io/hindsight-coding-agents) 及[集成更新日志](https://hindsight.vectorize.io/changelog/integrations/coding-agents)。服务 API、客户端集成和受管 `hindsight-coding-agent` 技能分别登记。

DSH 客户端的本地补丁由实际 profile 的 `patches` 目录维护；本机入口为 `C:\Users\Administrator\.dsh\profiles\desktop\patches\hindsight-coding-agents-0.8.7\README.md`。检查客户端新版或 DS Bot 输入格式变化时，先读该入口，对照目标发行源码逐项判断保留、适配、缩减或删除，并记录回归与加载证据；未完成兼容性判断时暂缓该客户端升级。精确版本补丁不会自动适用于新版，不能只凭 issue 关闭或补丁能应用判定已修复。具体补丁、哈希和当前加载状态由该入口持有。

获授权时沿官方运行时更新入口应用精确版本，在现有接入范围内核实际宿主参数、项目目录、工具输入和分库结果。按当前配置处理停用项目和默认工作区，不以更新为由接入新的 harness。工具接口变化时核实际调用者；缓存刷新或重启按宿主规程与当次授权执行。回退材料按收尾条件释放。

## AstrBot 与 My feiyu

检测是否启用以[检查范围](targets.md#检查范围)为准。恢复检测后使用下述规程。

维护入口：`D:\dev\My feiyu\README.md`；按其导航读取 `docs/guides/manual-changes.md`、`docs/guides/plugin-patches.md` 及受影响组件规程。启停策略、当前暂停状态、实际运行目录、插件来源、补丁基线和验证命令均由项目持有。

同时核本体、已启用插件和当前共享环境依赖；用实际安装入口的清单联合解析，包含附加消费者的约束。候选环境和已加载生产环境分别记录，保护原有配置和真实数据。

涉及本地补丁时，按项目规程判断保留、适配、被上游替代或退役，按实际授权选择功能取舍。验证须覆盖受影响的导入、初始化、路由及实际加载；版本护栏和补丁锚点检查不代替功能验收。项目测试若绑定旧运行目录，应确认测试消费候选代码。QQ 等业务链路按项目授权单独处理，未验边界如实报告。

具体插件版本、设置、补丁文件和执行命令不在技能中重复维护；回执引用项目记录，统一完成入口迁移和残留清理。

## 受管技能

通过本机安装的 `manage-skills` 查询登记、来源和部署。自有技能按已安装 `improve-workflow/references/package-operations.md` 选择唯一维护源；上游版本、库内独有改动和已部署内容分别核对。

检查、更新和分发沿当次授权。保留既有身份、来源和部署选择；更新检测为 `unknown` 时，在报告「待确认」中逐项写技能名称和「未能判断是否有更新」。查询结果提供具体原因时一并注明。具体 My-Skills 发布与备份规则由包维护规范持有。
