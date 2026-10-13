# 个人技能包操作

读者：维护个人包的 Agent。运行状态保存在维护仓 Git common dir 的 `workflow-state/`，位于技能发现目录之外；不是第二份产品待办。工具为完整维护源根目录的 `tools/skill_package.py`，Python 标准库与 Git 即可。

## 维护源与安装入口

My Skills 负责编辑、检查和发布；Skills Manager 负责中央库、更新和 Agent 部署。安装目录只有独立技能及其内部资源，不能从它向上两层寻找包策略或管理工具。

先读本机 `manage-skills`，解析其受版本戳保护的 CLI；`repo status`、`skills show improve-workflow` 和 `agents list` 提供中央库、来源及部署位置。复用项目入口提供的 My Skills 维护源，或本机同一来源远端的完整 Git 仓；核其 `skill-package.json`、`tools/skill_package.py`、Git origin 与技能来源一致。缺少维护仓时按当前授权取得完整源；缺少授权则只保留分析，不把中央库当维护仓。维护仓与已部署内容有差异时先定位来源，保护双方独有改动。

工具调用带实际 `--source`；上游指纹检查与 prepare 的 `--install-root` 指向 `repo status` 返回的中央库。Python、CLI 和路径均查本机，项目只登记本机绑定，跨项目技能不保存某台电脑的绝对路径。

## 固定执行版本与状态

工具动作输出 JSON：0 成功，2 保存成果但需要 Agent 接续，1 操作失败或阻塞；读取实际状态和详细日志指针，不能只信退出码 0。共享 Git 和安装操作使用本机互斥，忙时等待当前事务结束再试，工作区编辑仍可独立进行。prepare返回的entry保存完整规则和相对引用，runtime保存实际执行工具，后续沿用二者。

inspect的upstream字段比较实际原版及资源指纹；unverified或changed时按入口“Matt更新适配”核当前消费契约。prepare保存本轮上游原件和指纹。verify的`--checked-upstream`只列Agent已核验保存版本的依赖名，兼容结论与依据留在本轮已有记录；完成时仅这些依赖且版本仍匹配才登记基线，其余变化继续待核。checked表示该指纹曾按流程核验，不表示任意将来版本兼容，不替代依赖可达性或个人包自身改动的行为核验。本轮使用保存的上游输入，外部引用按实际需要读取并留下版本依据。源修改后再次列仍有效的已核验依赖，按影响复用证据。

| 动作 | 输入与结果 | Agent 下一步 |
|---|---|---|
| inspect | 实际源 `--source`、中央库 `--install-root`；发现技能、上游路径、dirty、未完运行及 installation | 核中央库内容与维护源；实际 Agent 部署经 Skills Manager 核验，只有分析时止于只读 |
| read | `--file`，相对引用加 `--relative-to`；默认限量文本或 JSON 概览，细读用 `--pointer` / `--offset` | 按下一节读取所需证据，不把概览或截断部分当成完整内容 |
| structure | 实际源、`--validator` 和 `--validation-python`；先核 yaml，再执行发现的全部技能的现有验证器 | 环境阻塞时先选可用解释器，技能失败时修候选；此结果不替代 verify |
| prepare | 唯一 `--run`；保存稳定源原件、二进制差异、原HEAD与内容摘要，从最新主线建 worktree | 在返回的worktree迁入确认的增量；之后调用返回的runtime，始终带实际source和run |
| verify | 运行标识；固定策略下执行候选检查及保存的旧回归，记录内容摘要和退出码 | 核原问题反馈、语义和审查；失败修复后再验 |
| publish | 有效验证、已提交的隔离worktree | published 后同步；needs_verification 或 conflict 时整合、核证据再验；pending 保留并按本轮三次上限处理 |
| resume | 下一次调用接续已有运行，核不确定推送是否已被远端接收 | 未发布时开启新一轮最多三次尝试；已发布时直接处理同步 |
| sync | 实际维护源；可带已发布运行；CLI 只推进稳定源，返回 source_synced | 继续 Skills Manager 更新及部署；source_synced 不是安装完成 |
| sync-manager | 已发布运行、实际 `--skills-manager-cli`；串行推进维护源、预检中央库、更新技能、修复既有部署并确认 | 全部通过才返回 synced；失败保留 source_synced，修正原因后接续同一运行 |
| confirm-install | 完整稳定维护源、实际 `--skills-manager-cli`；可带已发布运行 | 只读核中央库来源、所有资源内容与已声明的实际 Agent 部署；通过才登记 synced，失败保留待安装运行 |

首次为已经创建的隔离 `codex/` 工作区建立运行，可用 prepare 的 `--existing-worktree`，须属同一仓并包含最新主线；只接管本任务拥有的现场。普通调用由 prepare 创建工作区。工具不替 Agent 暂存或提交文件；验证后按本轮明确文件列表保存。源码提交不改变内容摘要，新增或修改输入会使证据失效。

publish 遇到主线前进会合并到本轮隔离分支并使验证失效，Agent处理语义、冲突及对应核验。网络失败、钩子拒绝和竞争保留分支与状态；不强推，不跳过钩子。对需要PR或其他权限的远端按实际限制报告，包策略不绕过环境限制。发布后远端可能再次前进，核本轮提交仍被包含及实际同步版本。

带运行的同步须已发布且远端包含其提交；sync只登记source_synced，sync-manager在中央库与真实部署都确认后才结束运行。未发布时可以独立同步宿主，不改变原运行的待办状态。本地主线有独有提交时保留提交和恢复分支，先把有效增量整合到本轮隔离分支；Agent核已保存历史和迁移结论后接好干净稳定源，工具不把本地领先版本冒称远端安装版本。

## 落后版本与安装副本

prepare 先保存稳定源中的 tracked 和未忽略的新文件；忽略的凭据及缓存不进入发布范围。原基线明确时做三方比较；基线未知时以完整原件逐项定位来源。源改动继续留在原现场，隔离工作区默认从最新主线开始，不自动套旧文件。

已发布并确认原增量逐项处置后，sync 可带 `--reconcile-source`：只有源HEAD、内容及快照仍匹配时，才释放已保存的旧dirty并正常推进主线。源已被其他任务改动时重新保护新成果，不能沿用旧快照释放它。

中央库或 Agent 安装副本有独有改动时先比较、保存并迁入维护源的有效增量；已有技能通过 Skills Manager 原位更新，保留 ID、来源、预设和部署选择。新增技能用维护远端的准确技能子目录入库，再按当前授权选择 Agent 部署。安装冲突、held_back_removals 或未获准的覆盖保留现场，按 manage-skills 处理；不删除重装，不使用 force，不由个人工具重建链接。Matt 原版与归属不明副本保持原渠道和边界。

正常发布后使用sync-manager，既有技能只保持各自原有部署选择。新增技能默认只入中央库；本轮已明确选择Agent时用可重复的`--deploy-new-to`指定。预检须确认中央库是源仓历史中完整提交过的版本，未知本地编辑在任何update前拒绝；先迁入源仓再重新发布。工具只规范化已识别UTF-8文本的CRLF/LF来比对部署，二进制仍逐字节判断。Git源快照与Matt上游兼容指纹保持原始字节。

新增技能的部署意图在install前保存；入库成功而部署失败时，同一运行重试即使不再传Agent参数也须补齐原选择，核真实部署后才清除。有运行时存入原state，无运行时保存在Git common dir的pending-manager-deployments.json；不在中央库放维护状态。

## 材料读取与结构校验

inspect 的 installation 给出中央库实际形态与 matches_source，不要求它链接回维护源。安装完成用 confirm-install：Skills Manager 记录的来源与中央库路径须正确，完整资源指纹与维护源一致，声明部署的每个 Agent 路径须存在且内容匹配；链接部署还须指向中央库。缺项、陈旧内容、错误来源或错误目标都拒绝关闭。仅 metadata 显示 deployed 不算完成；没有部署的技能明确保持 library-only。

读取证据先调用 `read --file '<实际文件>'`；JSON 默认只显示一级字段类型与数量，需具体内容时用 `--pointer '/sources/local-source/files'` 等实际键，空指针选根。文本及选中 JSON 每次默认 2000 字符，上限 6000；complete 只表示当前 view 输出完整，json_overview 不是原文。next_offset 非空时按需续读；同一内容的续读须保持 sha256 一致。read 的项数用于定位，文件摘要用于核续读来源；清单完整性另用已有快照、摘要机制或定向程序实际比对原件与清单，只返回统计、差异及证据位置，明细留在原文件。

相对引用用 `read --file 'SKILL-MECHANICS.md' --relative-to '<引用它的实际 SKILL.md>'`，以引用文件所在目录解析。缺项会返回实际解析路径；按原引用补查，不自行插入目录层级。工具尚无这些动作的固定旧运行继续原版本：采用同样的字段筛选、限量读取和实际实现检查，不借新版管理进行中的旧运行。

完整结构校验用 `structure --source '<候选包>' --validator '<本机 quick_validate.py>' --validation-python '<已有解释器>'`。两个路径按当前宿主核实；工具使用 Python UTF-8 模式，先检查该解释器能 import yaml，失败返回 environment_blocked 且不执行验证器，选择已有可用环境后继续。依赖就绪后逐技能返回退出码；validation_failed 与环境故障分开，输出截断按标记补取必要原始失败证据，不以包目录发现代替 YAML 校验。

## 新会话同步

新会话首次使用个人方法时，定位完整维护源，执行inspect并接续本机未完同步；稳定源无待保护修改时sync-manager一次，再读取本轮要用的实际安装正文。新技能按当前授权选择部署。已核一致时复用结果，不重复更新。发现相关上游变化时按入口核消费契约，不自动全面复盘产品会话；dirty先保护，运行中任务保持固定基线，版本检查不重复到每票。

## 核验与收尾

工具按最终差异选择机械验证：仅技能文档、技能UI元数据或README变化时检查目录与必要元信息；管理工具、检查、包策略和其他输入变化时执行包策略的回归及保存的旧回归。新增技能自动发现，完整YAML结构按本机 skill-creator 的 quick_validate.py核验。候选行为仍由Agent按实际改动判断，机械回归通过不代表所有决策正确。运行可恢复不等于任务完成。

同步完成后，确认源快照、必要日志及本轮未决均有去向；用Git工作区工具释放本轮无须保留的worktree，保留执行快照供进行中任务和自修改失败恢复。未发布、冲突或未完成安装确认的现场保持可访问。旧固定工具尚无 source-only 同步时，保留旧验证和发布反馈；本次授权已改为 Skills Manager 管理的迁移，正常快进稳定源后由 Skills Manager 更新部署，再用新维护工具 confirm-install 关闭，旧链接安装器不用于迁移。状态与证据保留在原运行，不为清理另建台账。

旧固定工具有source-only但没有sync-manager时，沿用旧runtime的sync推进维护源；通过manage-skills更新及部署，再用新稳定源的confirm-install带原run关闭。也可在新稳定源无run调用sync-manager，再confirm-install原run；验证与发布继续使用旧runtime，不改写执行快照。
