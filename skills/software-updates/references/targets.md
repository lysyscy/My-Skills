# 本机项目与工具链

材料工作台、询价 Excel 归一化和 project-workflow 进入通用候选验证。正式启用、共享运行时和其他专项按各自规程处理。[状态与记录](status.md)保存版本快照。

| 目标 | 项目位置与版本来源 | 应用和验证边界 |
|---|---|---|
| 材料工作台后端 | `D:\dev\mtrl-workbench\backend` 的 `pyproject.toml`、`uv.lock`、`.python-version` | 读仓根 `docs/guides/development-and-verification.md` 和 `docs/guides/deployment.md`。主检出的 `backend/.venv` 供生产服务使用。候选用另建解释器环境、可核 Git 基准及该隔离副本的登记产物区。按变更选规定的后端测试，需数据库时走专用测试库；纯工具测试只证明所覆盖的工具行为。 |
| 材料工作台前端 | `D:\dev\mtrl-workbench\apps\frontend` 的 `pnpm-lock.yaml`、`pnpm-workspace.yaml` 和 `package.json` | 按项目当前配置核版本绑定补丁和实际选版限制。按 `.github/workflows/frontend-checks.yml` 用锁定的 Corepack/pnpm 冻结安装、类型检查和单测；影响构建时按项目规程验证构建。部署与本地候选分别处理。 |
| i8 爬虫开发 | `D:\dev\i8-data-crawler` 的 `pyproject.toml`、`uv.lock`；Playwright 在开发组 | Playwright 候选用独立浏览器目录，按锁定包所需修订验证无头 Chromium。可用合成 HTML 和 DOM 断言做离线冒烟；实际 i8 登录探针不属于依赖验证。现有一般自检不证明 Playwright 可用。 |
| i8 爬虫 Win7 打包 | 同仓 `打包.bat`、构建组和独立 `.buildenv`；Python 3.8 32 位与 PyInstaller 基线 | 与普通开发环境分开。锁变化波及构建组时停通用同步，按打包规程验证。 |
| 询价 Excel 归一化 | `D:\dev\业务流程\询价\agent-skills\inquiry-assistant\workflows\inquiry-list-normalization` 的 `pyproject.toml`、`uv.lock`、`.python-version` | 读仓根 `CONTRIBUTING.md` 和 `agent-skills/evals/evaluation.md`。与 Node 主应用、部署的技能副本和旧虚拟环境分开。 |
| 询价主应用 / 审批辅助 | `D:\dev\业务流程\询价\package.json`；`D:\dev\业务流程\审批辅助\pyproject.toml` 和 `uv.lock` | 首版登记运行时。询价主应用无 npm 依赖，审批辅助尚未声明第三方 Python 依赖；每次以项目现状为准。 |
| project-workflow | `D:\dev\project-workflow` 的 `package.json`、`pnpm-lock.yaml` 和 `pnpm-workspace.yaml` | 按 `CONTRIBUTING.md` 在隔离目录冻结安装并执行 `pnpm check`。TypeScript 和 `@types/node` 由锁管理。台账测试临时使用的 `openpyxl` 单独核查，影响该路径时用合成工作簿执行 `pnpm test:ledger-workbook`。 |
| My-Skills 开发环境 | `D:\dev\My-Skills` 的 `pyproject.toml`、`uv.lock` 和 `.python-version` | 核对仓库的实际 Python 和依赖；运行时迁移按仓库 `CONTRIBUTING.md` 验证。技能分发走已登记的发布规程。 |

持久开发应用目标需按项目明确登记路径和消费者。目前材料工作台后端及询价 Excel 归一化没有已核实的独立持久目标，默认停在候选验证。隔离候选和演练目录仅供验证；主检出的声明、锁文件及环境都应核实与生产或已部署技能的关系后再写入。

`whale-workbuddy` 已停止开发，留作未来将微信桥接入 My feiyu 的参考。接入时按当次范围核对所需依赖。

## 检查范围

| 目标 | 当前范围 | 恢复条件 |
|---|---|---|
| AstrBot（My feiyu） | 暂停本体、全部插件（含梗百科）及其共享环境依赖的更新检测。 | 用户重新纳入后走[服务规程](services.md#astrbot-与-my-feiyu)。 |
| i8 爬虫 | 暂停项目开发依赖（含 Playwright）和 Win7 打包依赖的更新检测与应用。 | 用户重新纳入后按上表对应的开发或打包规程验证。 |
| CodeBuddy CLI（`@tencent-ai/codebuddy-code`） | 用户确认已卸载，退出更新检测。 | 重新安装且重新登记后纳入。 |

先应用此表再查询版本、解析依赖或列候选。已排除项即使出现在旧批次、历史记录或包管理器缓存中，也按当前范围处理。

## 询价验证

- `openpyxl` 或影响它的变更：用候选解释器运行仓库布局的隔离副本中的 `agent-skills/evals/test_blank_template.py`，核对合成工作簿的表头、公式、格式及源文件防覆盖。
- `xlrd` 或影响它的变更：用合成 BIFF `.xls` 走流程的 `scripts/inspect_structure.py` 实际读取。空白模板测试不覆盖这一路；缺合适验证时停该项。

## 工具链

### 工具链与项目迁移

1. 在已选中的工具链更新里列出受影响的消费者，包括项目声明和 pin、虚拟环境、锁文件、CI、构建脚本、启动入口和服务。区分本机安装、项目开发、构建及生产目标，按实际渠道和兼容基线选版本。
2. 用目标版本隔离验证后，同步本批获授权的项目。需要时更新精确 pin、锁和脚本，重建或同步虚拟环境，核对项目命令实际解析到的版本，再跑相应测试或构建。版本范围已覆盖目标时，验证实际使用即可。生产、重启、共享运行时切换和已部署技能按各自授权处理。
3. 按目标应用并验收。开发环境按原锁同步并通过项目正常命令实测。生产服务先记健康、原环境和回退点，按项目入口停止、切换、启动，核新进程身份、实际解释器路径和健康。启动或核验失败，恢复原入口并复验。已发布技能从维护源构建，对比实际发布差异，按登记来源更新现有部署，回读中央库及每个客户端的文件，再从已发布版本入口验证。
4. 通用入口迁移、验收和清理按[更新收尾](completion.md)。Python 同一维护线的补丁版本（如 3.15.1 → 3.15.2）默认在迁移后淘汰旧版。先核精确 pin、虚拟环境的基底、共享入口、脚本、服务、计划任务、全局工具和回退用途。确认无消费者且无需回退后，用 uv 按精确补丁版本卸载。uv 可能重算其他维护线的共享入口，操作前后对照在用的各维护线入口和关键项目实际版本。只读扫描源码和已发布 pin、环境基底、实际进程、启动器、服务和任务。核对环境基底解析后的绝对路径，区分同名入口的独立安装根及已退役副本。发布或重启未验证、旧版仍承担兼容或回退用途时，保留并记解除条件。保留仍有明确用途的版本，记录消费者和释放条件。3.12、3.13、3.14、3.15 属于不同维护线，各自按实际兼容目标处理。
5. 回写每个目标的「声明 / 实际解释器 / 服务加载或客户端发布」、验证、适配和旧版去向。表格中的「已完成」以实际运行或发布证据为准。

- **Git for Windows、独立 PowerShell Preview、WinGet / App Installer**：核对实际安装位置、渠道和版本。WinGet 以 App Installer 的渠道为准。同一个实例若已有 [UniGetUI 候选](unigetui.md)，只列一次。

- **uv / Python**：以实际可执行文件、安装来源、项目 Python 声明和目标解释器为准。分别比较 [uv Releases](https://github.com/astral-sh/uv/releases) 和 [Python 发布](https://www.python.org/downloads/) 的同渠道稳定版本；默认 Python 不代表项目解释器。
- **Node / npm / pnpm / TypeScript**：TypeScript 以项目锁和实际 `tsc` 为准。分别记录本机命令、项目声明和实际构建工具链。分别核对 Node.js 随附的 npm、用户全局 npm 及当前命令实际解析到的入口。随附 npm 对照 [Node.js Releases](https://nodejs.org/en/about/previous-releases) ，独立 npm 对照 [npm 注册表](https://www.npmjs.com/package/npm)，pnpm 对照 [pnpm Releases](https://github.com/pnpm/pnpm/releases)。按实际安装渠道处理。
- **Playwright / Chromium**：材料工作台与爬虫共用 `C:\ProgramData\ms-playwright`。浏览器修订随 Playwright 包版本核对；完整和无头版及服务账户可达性分别取证。候选隔离设置 `PLAYWRIGHT_BROWSERS_PATH`；共享缓存、机器级变量和在用浏览器按消费者核对。见 [Playwright 浏览器说明](https://playwright.dev/python/docs/browsers)。
- **playwright-cli**：从实际命令定位包名、版本和上游。独立于项目 Python Playwright 和共用 Chromium 登记。
