# 状态与记录

维护位置为 `D:\dev\tooling\My-Skills\skills\software-updates\references\status.md`；安装副本只读。各行是带日期的更新证据，具体服务现状与规则以其 README 为准。

## 当前状态

下表是登记与最近已有证据，未填的状态等对应检查补齐；旧证据的日期不随查表日期更新。实际栏按运行目标区分本机命令、项目环境、已部署或已加载。

| 项目 / 组件 | 锁定或声明 | 实际运行 / 使用 | 上游渠道 / 版本 | 核对日期 · 状态 |
|---|---|---|---|---|
| 材料工作台后端 | `backend/uv.lock`；本地 `.python-version` 3.15.2 | 生产监听进程 Python 3.15.2；原前端 `472fce96` | [Python 3.15.2](https://www.python.org/downloads/release/python-3152/) | 2026-11-10 · 已重启，`/app/` 200 且索引散列一致；pin 已提交并推送 `6281cece`，远端 master SHA 已核对 |
| 材料工作台 pypdf | 主线 `62e23a68`，锁定 `7.0.1` | 生产环境实装 `7.0.1`，已切换至新服务进程 | [上游安全修复](https://github.com/py-pdf/pypdf/releases/tag/7.0.1) | 2026-11-10 · 原隔离回归 13 项通过；本次部署 `/healthz` 与 `/app/` 正常，8000 监听归属通过。报告 `.artifacts/runs/pypdf-701-check/reports/pypdf-deployment.json` |
| 材料工作台前端 | `apps/frontend/pnpm-lock.yaml`；本地 `motion` 14.12.0；pnpm 12.18.0 | 本地 `motion` 14.12.0；生产已加载 `472fce96` | [npm 官方](https://www.npmjs.com/package/motion/v/14.12.0) | 2026-11-10 · 已提交、推送并验证生产加载 `472fce96` |
| 材料工作台 · 本批依赖候选 | 后端 P1/P2 共 13 项（含 `pypdf 7.1.1`、FastAPI `0.165.0`、Playwright `1.65.2`）；前端 F1–F5（`antd 6.7.1` 补丁已改绑）及 pnpm `12.21.0` | 隔离候选全部通过；正式部署以生产回执为准 | 项目依赖锁及本地补丁 | 2026-11-20 · 验证回执 `mtrl-dependency-wave2b-20261120/verification.json` |
| i8 爬虫开发 | `D:\dev\i8-data-crawler\uv.lock`；Playwright 1.65.0 | 开发 Python 3.15.2，Playwright 1.65.0 | Python.org / PyPI | 2026-11-10 · 已重建；原锁与包版本一致，隔离无头 Chromium 冒烟通过 |
| i8 爬虫 Win7 打包 | `打包.bat` 锁定 uv 管理的 Python 3.8.20 32 位；PyInstaller 5.13.2，独立 `.buildenv` | `.buildenv` 实测 Python 3.8.20 32 位 | uv 管理的 CPython | 2026-11-13 · 已核脚本与实装，实际 Win7 运行待验 |
| 询价 Excel 归一化 | `uv.lock`：openpyxl 3.1.5、xlrd 2.0.2、et-xmlfile 2.0.0；`.python-version`：3.15.2 | 项目本地 `uv run` 实测 3.15.2，三包与锁一致；已发布六端核验为 3.15.2 | [openpyxl 3.1.5](https://pypi.org/project/openpyxl/)、[xlrd 2.0.2](https://pypi.org/project/xlrd/)、[et-xmlfile 2.0.0](https://pypi.org/project/et-xmlfile/) | 2026-11-10 · 合成工作簿回归通过；发布包实测 3.15.2 |
| 询价主应用 / 审批辅助 | 询价 Node ≥24；审批辅助 Python ≥3.15，未声明第三方 Python 依赖 | 审批辅助本地 Python 3.15.2 | Node.js / Python.org | 2026-11-10 · 审批环境已重建，离线技能包测试通过 |
| Hindsight API / 管理页 | API slim 与管理页 `1.2.3`，按本机发布锁 | API、管理页已加载 `1.2.3`，`pg0-embedded 0.17.0` | [Hindsight 发行](https://github.com/vectorize-io/hindsight/releases) | 2026-11-20 · 已验收并收尾，回执 `D:\services\hindsight\state\upgrade-1.2.3-wave-2a-20261120.json` |
| Hindsight 客户端集成 · DSH desktop | profile pnpm 精确版及 A/B 补丁 | 已加载 `0.8.8` 和 A/B 补丁 | [服务登记](services.md#hindsight-客户端集成) | 2026-11-26 · Desktop 已验收 8 个原生工具、页面读取及真实 Bot request 来源。2026-11-20 的 103/103 回归与离线检查通过 |
| Hindsight 客户端集成 · Codex / Antigravity / Grok Build | 共用 staged `0.8.8`，官方 `update`，本机子代理过滤补丁 | `grok-build` 已安装；八个 hook bundle 重放与六组隔离回归通过 | [服务登记](services.md#hindsight-客户端集成) | 2026-11-25 · 保留 Antigravity cwd 包装；新宿主会话加载待验 |
| Grok Build CLI | 原生 Windows `install.ps1` | `grok --version` 实测 `1.0.92`；两处 junction 已核 | [工具链登记](targets.md#工具链) | 2026-11-25 · CLI 与存储位置已核 |
| t3-pstack | `chhoumann/t3-pstack#v2.7.1`，提交 `11a71d2` | Codex 与 Antigravity `2.7.1`；共享模型表 `C:/Users/Administrator/.config/t3-pstack/models.md` 实测 `session hook: on` | [工具链登记](targets.md#工具链) | 2026-11-26 · Antigravity 锚点补丁和两端 SessionStart 已核验。2026-11-25 的 `doctor` 通过 |
| 技能更新 | Skills Manager 的已登记来源 | 55 项受管技能 | [受管技能](services.md#受管技能) | 2026-11-20 · 55 项均为 `up_to_date` |
| uv / 本机 Python | 按项目 `.python-version` 和有效环境核对 | uv `0.13.9`；2026-11-10 已核 Python 默认 3.15.2，另有 3.14.10 / 3.13.18 / 3.12.16，Hindsight 独立 3.12.16 | [uv](https://docs.astral.sh/uv/concepts/python-versions/) | 2026-11-20 · uv 已核；Python 3.12.14 失效注册表键已清理 |
| Node / pnpm | 按各仓库声明 | 全局 pnpm `12.21.0`；Node 26.13.0 为 2026-11-10 实测 | Node.js / pnpm Releases | 2026-11-20 · 已核 pnpm 同步 |
| Playwright / 共用 Chromium | 浏览器修订随各项目 Playwright 版本核对 | 共用 Chromium `1255`（`159.0.8154.6`），目录 `C:\ProgramData\ms-playwright` | [Playwright 浏览器说明](https://playwright.dev/python/docs/browsers) | 2026-11-20 · 已核共用浏览器版本 |
| playwright-cli | 独立安装渠道 | `0.1.25` | 按实际包名和渠道核对 | 2026-11-20 · 已核版本 |
| 独立版 Codex CLI | npm `@openai/codex`，供 T3 Code 使用 | `0.171.0` 已加载 | [检查归属](unigetui.md#归属) | 2026-11-20 · 已清理旧 `0.170.0` 退役目录 |
| project-workflow | `pnpm-lock.yaml`；pnpm `12.21.0`；TypeScript 7.0.2、@types/node 26.6.6 为 2026-11-10 锁定记录 | 项目 pnpm `12.21.0` 已同步 | 配置的 npm 源 | 2026-11-20 · 已核 pnpm 同步 |
| Git for Windows | 按实际安装渠道 | 2.56.0.windows.4 | 渠道及上游待查 | 2026-11-10 · 本机命令已核 |
| npm | Node.js 随附、用户全局两个实例 | 用户全局 `12.2.3`；随附版本 11.20.0 为 2026-11-13 实测 | 随附版本跟随 Node.js，用户全局按 npm 发行渠道核对 | 2026-11-20 · 已核用户全局版本 |
| 独立 PowerShell Preview | 独立预览渠道 | 7.7.0-rc.1 | [官方 Release](https://github.com/PowerShell/PowerShell/releases/tag/v7.7.0-rc.1) | 2026-11-10 · 官方包 SHA-256 与实际启动版本已核验 |
| WinGet / App Installer | App Installer 渠道待核 | WinGet 入口存在，App Installer 版本未核到 | 待查 | 2026-11-10 · 待确认 |
| UniGetUI | [本机软件候选](unigetui.md) | `2026.3.4` | WinGet 后端 | 2026-11-20 · 定版行为见[逐项更新](unigetui.md#逐项更新) |
| 桌面软件已达标项 | 本批目标版本 | DuMate `1.0.93`、Gemini Desktop `1.21.1`、滴答清单 `8.2.6.0`、豆包 `2.36.10` | 各自安装渠道 | 2026-11-20 · 四项实测达标 |
| ego (lite) | 目标 `0.6.3.17` | 实测 `0.6.3.14` | 独立桌面软件 | 2026-11-20 · 待用户复查 |
| U4 · WinGet Python 3.14 | 用户级登记 `Python.Python.3.14` 3.14.7 | uv 管理的 3.14.10 实测正常；未定位到 WinGet 记录对应的独立解释器 | WinGet 3.14.10 | 2026-11-10 · 不重复安装，登记来源待确认 |

询价试点：合成模板测试通过，模拟同步后实际版本与锁一致；锁漂移被拒绝，模拟目标与真实项目输入经核对。回执：`C:\Users\Administrator\AppData\Local\AgentArtifacts\projects\inquiry\groups\upd-1110-c\files\rehearsal.json`。

### 2026-11-10 批次复核

- **VLC** `VideoLAN.VLC`。WinGet 机器范围，卸载登记及 `vlc.exe` 均为 3.0.24，UniGetUI 操作 `4920034` 成功。
- **Windows Terminal** `Microsoft.WindowsTerminal`。WinGet 用户范围，重启后当前用户 AppX、WinGet 和 UniGetUI 一致为 1.25.2733.0，AppX 状态正常。原在用阻塞已解除。
- **OneDrive**。签名卸载程序返回成功，常规卸载项和客户端可执行文件已消失。用户确认已卸载，重启后 WinGet 和 UniGetUI 均已无该项。
- **滴答清单** `Appest.Dida`。用户已更新，WinGet 和 UniGetUI 安装清单均为 8.2.5.0。
- **Python 项目迁移**。爬虫开发、询价本地和发布包、审批辅助、My-Skills、材料工作台实测 Python 3.15.2。AstrBot 本地环境 3.13.18，Hindsight 控制器与 API 3.12.16。询价助手原六客户端逐文件核验，发布包用原锁实测。工作台和 Hindsight 已重启并核对实际进程与健康。3.15.0、3.15.1 无在用引用后已卸载，旧发布档案留作历史；另核实微信桥使用自己目录里的 3.12.15。全局 3.12 已切至 3.12.16，确认无在用引用后卸载 3.12.14；微信桥与 Win7 3.8.10 32 位兼容环境保持原样。
- **材料工作台**。`motion` 本地冻结安装、类型检查、165 项单测和构建通过。用户补充授权后，已提交、推送并验证生产加载 `472fce96`。 发布回执 `D:\dev\mtrl-workbench\.artifacts\runs\205534-313178-10908\reports\deployment.json`。
- **AstrBot**。三套离线回归为 93、32 和 228 项，原插件目录已备份。用户确认 B 站 2.0.5 主动观看按上游 `bot_self` 跨会话召回。本地共享记忆仍保留自己的 `private_pair` 规则，纯文本兜底与观看流水照旧。原生核心与 WebUI 逐字节等同上游包，21 项原生测试通过。AstrBot 停机，待加载。

## 更新历史

| 日期 | 项目 | 当时记录 | 后续 |
|---|---|---|---|
| 2026-11-07 | Hindsight API | 运行中 1.2.0，PyPI 1.2.0 | 当时无更新；管理页面版本未单独验证。 |
| 2026-11-07 | AstrBot 插件 | 陪伴 7.1.0 → 提示 7.1.3；表情包管理器 5.3.0 → 5.3.5；B 站界面提示 2.0.2 | 当时未更新；这些提示不代表当前最新版。 |
| 2026-11-08 | AstrBot 插件 | 陪伴 7.1.0 → 7.1.5，B 站 1.9.5 → 2.0.4，表情包管理器 5.3.0 → 5.3.5；记忆插件和 QQ 表情转换未升级。 | DSH 报告补丁已适配，项目记录测试 193/193、健康检查 11/11；详情见项目 `docs/status.md` 及补丁文档。 |
| 2026-11-09 | AstrBot 插件 | 磁盘版本及项目基线与当日记录一致；三组插件补丁的 `--check` 显示无待施打项。 | 本次未重新核对上游最新版，也未重新运行功能测试。 |
| 2026-11-10 | 材料工作台 | 依赖已同步；生产已加载 `265e2fde`。 | `.artifacts/runs/dependency-release-20261110/reports/` 下分别见 `dependency-sync.json` 与 `deployment.json`（仓根 `D:\dev\mtrl-workbench`）。 |
| 2026-11-10 | 用户选定批次 | OneDrive 客户端已卸载；uv 0.13.7、独立 Python 3.14.10 / 3.15.2、PowerShell Preview 7.7.0-rc.1、`motion` 14.12.0 及三个 AstrBot 插件已更新；爬虫、询价源和审批辅助 Python 3.15.2，AstrBot Python 3.13.18，旧 3.13.7 / 3.14.7 已卸载。用户已处理 U2 / U3 与 U7，滴答清单重启后核到 8.2.5.0。 | VLC 3.0.24、Terminal 1.25.2733.0 已核验，已提交、推送并验证生产加载 `472fce96`。待办见批次复核。 |
| 2026-11-10 | P1 / A1 / H1 / S1–S3 / U4 | P1 候选验证通过；A1 磁盘 7.1.12；H1 客户端 0.8.7；三项技能由用户更新并复核。 | P1 待同步与部署，A1 停机待加载，U4 保留核对。 |
| 2026-11-10 | P1 部署 / A1 加载 | P1 已推送 `62e23a68`，生产切换到 `pypdf 7.0.1`；A1 初始化失败并回退，`7.1.11` 已实际加载。 | 7.1.12 待可安装发行包；QQ 链路受 SnowLuma 停机影响。 |
| 2026-11-10 | 陪伴小屋 7.1.14 部署 | 官方包已安装，三组补丁原样重放，正式加载 7.1.14。 | 仪表板 200，后台并发保留 1；登录后日志与作品操作及 QQ 链路待验。 |
| 2026-11-11 | AstrBot 依赖 / Hindsight 1.2.1 | AstrBot 35 项稳定依赖已应用，并发 3 已重载；Hindsight API 和管理页均部署 1.2.1。 | AstrBot 回执在 My feiyu 的 `var/astrbot/maintenance-backups/dependency-update-20261111/deployment.json`，Hindsight 回执在 `state/upgrade-1.2.1/cutover-verified.json`。 |
| 2026-11-13 | 本机软件、工具链、材料工作台与 Hindsight | Argus 0.5.0、Claude Code 2.1.323、ego lite 0.6.3.12、Node 26.13.1、Obsidian 1.15.1、UU 远程 4.47.0.5146、Windows Terminal 1.25.3131.0、豆包 2.35.12、uv 0.13.8、Git 2.56.1.windows.1、独立 PowerShell 稳定版 7.7.0 均核实实装。impeccable 4.9.0 已同步原四处部署。 | 材料工作台前后端依赖已推送，后端提交 `45ef7f22`，前端 CI 实测 Node 26.13.1。正式部署状态见项目。Hindsight API 依赖切换与备份已验收，回执见其 `state/maintenance-20261113-dependencies.json`。i8 爬虫按现行范围暂停。 |
| 2026-11-20 | 本机软件、工具链、Hindsight、材料工作台与受管技能 | Hindsight 服务已加载并收尾，staged 实例 MCP 已连通；工具链和四项桌面软件实测已达标，失效登记及退役 CLI 已清理。材料工作台隔离候选全部通过，55 项受管技能检测为最新。 | DSH 磁盘升级待重载验收，ego (lite) 待用户复查；材料工作台正式部署以生产回执为准。版本和回执见[当前状态](#当前状态)。 |
| 2026-11-23 | 用户选定批次 | P1、F1、F2 已隔离实装并推送材料工作台 `59f1c4c5`，前端 CI 通过，生产待部署。S1 `ui-ux-pro-max` 已更新至 `281e4537`，原四处部署逐文件核对一致。 | H1/H2 联合更新 61 项候选通过依赖检查与 ONNX 实测，正式服务切换需管理员。U1 FlClash 机器范围更新需管理员。AGH1 `v0.4.11` 启动被 Windows 拒绝，`v0.4.10` 在运行。T3-1、A1、A2 按本批选择跳过。 |
| 2026-11-25 | Grok Build、t3-pstack 与 staged Hindsight | 登记 Grok Build `1.0.92` 和 t3-pstack `v2.7.1`，新增 Grok Hindsight 接线，子代理过滤六组回归通过。当天模型表的会话 hook 关闭。 | 本次技能登记留在 My-Skills 维护源，Skills Manager 中央库和五个宿主仍读取已发布版本。 |
