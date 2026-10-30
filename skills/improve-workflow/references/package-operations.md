# 自有技能维护与安装核验

本文件持有自有技能的维护源选择、验证与分发规则。先确定唯一维护源和下列分支，再执行其发布步骤；Hindsight只保留偏好、经验证经验和本规范入口，现行流程以此处正文为准。

## 选择唯一维护源

| 已确认的技能形态 | 唯一维护源 | 验证与分发 |
|---|---|---|
| 只有提示词或少量资料，无独立工程测试，用户已选择库内维护 | Manager中央库中该技能的作者目录 | 在该源修改；用manage-skills维护登记及原部署，核实际发布文件；按已有选择备份 |
| 属于业务项目，带脚本、fixtures或项目测试 | 所属项目的技能目录 | 用项目既有检查验证，再按其已登记来源更新并核部署；Git/CI沿项目已有契约 |
| My-Skills个人包，或已明确采用按Git提交发布的技能包 | 已绑定的开发仓与技能子目录 | 执行下文Git、CI、Manager及备份核验链 |

沿当前项目和已有登记确认作者目录，不把中央库、项目副本和Agent目录同时作为编辑源。改变维护归属须按本次授权迁回有效增量并切换消费者；来源不明时先定位主人。外部原版保持原渠道，个人方法只维护必要适配和引用。普通技能不因使用Manager就新增开发仓、CI或个人包全套核验。

## 项目本地来源的正常更新

从已确认的固定本地目录首次导入后，核登记的source_ref确实指向该维护源；后续修改、验证后运行manage-skills的check/update，保留原ID、标签、Preset和已有部署集合。命令成功或显示最新不等于内容已同步：按本项目已有口径核公开文件集合、实际内容及部署归属；只对已核实的缺失或陈旧目标定向部署。

来源路径缺失、已不存在或同名安装生成后缀副本时，读取[本地来源恢复](local-source-recovery.md)再处理；这是异常分支，不将重新登记作为日常更新步骤。

## My-Skills个人包的Git发布分支

My Skills 用 Git 编辑、验证和发布源；官方 Skills Manager 管理中央库、Agent 部署和多设备备份。发布完成须分别证明源提交的 CI、本机安装与更新检测、备份远端内容，不能用其中一步代替整条链路。`tools/skill_package.py` 只核验，不提交、推送、更新、安装、清理或写运行状态；Manager 检测命令会刷新自身检查缓存。根工具不随独立技能分发，普通项目使用规则不依赖它。

以下各节只约束本分支，不为前述库内作者或项目本地来源增加Git、CI、清单或备份发布前置条件。

## 完成条件与授权

本次仅分析或候选时停在相应边界；已明确授权完整发布同步时，沿下列顺序执行源发布、CI核验、Manager更新、安装核验及备份推送，无需逐步重复询问。既有 `publish: automatic` 只表示清单授权范围，不替代本次限制。范围、覆盖冲突或必要权限有实质缺口时保留待办并询问。

完整收尾保留一份回执：源 SHA 与对应成功 CI、安装核验、Manager 检测结果、备份 SHA 和恢复后校准边界。归档、writing-for-agents 与文档层级按维护项目的收尾约定核验；未满足项明确记为待办。

## 定位与保护

先确认本次范围、只读/候选/发布/安装边界；本次请求优先于 `skill-package.json` 的既有自动发布授权。按真实项目入口找到完整维护仓，核 Git origin、清单远端及技能来源一致。先读本机 `manage-skills`，解析有版本戳的 Manager CLI，查询 `repo status`、`skills list/show` 与 `agents list` 取得实际中央库、来源及目标路径。

只在维护源编辑个人技能。中央库或 Agent 副本存在独有改动时，先比较、保护并把有效增量迁回源；更新不能代替整理这些增量。保护其他任务的未提交修改、索引及独有提交，按需建立独立 worktree；普通 Git 快进只用于已确认干净且可快进的现场，不在同步动作中清除旧修改。

开始维护时固定源 SHA、执行规则和本轮验收。涉及工具或规则自修改时，保存需要的旧版和原缺陷保护；明确退役接口的测试按批准后的新契约处置，保留行为的断言须迁移。实际消费的外部技能沿来源取得必要原件，记录版本与影响；`upstream_skills` 是依赖保护清单，不要求每轮复制或遍历全部上游，不维护另一份长期兼容账本。

## 修改、验证与 Git 保存

普通实施和收尾按维护项目已采用的 CONTRIBUTING；只加载本次受影响的技能与参考。纯文档检查语义、结构、引用与实际消费者；指令行为变更覆盖原问题、最近相关旧行为和失败分支。工具、测试、清单或共享契约变化执行清单中的相关回归及必要全套检查。按需行为实验见 [behavior-evaluation.md](behavior-evaluation.md)，不把实验设为每轮发布条件。

结构检查使用宿主真实系统 `skill-creator/scripts/quick_validate.py` 和已有可用解释器，不用中央库同名技能替代。调用 `uv run python tools/skill_package.py structure --source '<候选源>' --validator '<实际验证器>' --validation-python '<可 import yaml 的解释器>'`。工具先探测依赖，再逐技能执行验证器，区分 `environment_blocked` 和 `validation_failed`，返回非零；摘要截断时按需补读原始失败。结构通过不证明行为正确。structure 会执行外部验证器，其副作用须按实际工具核实，严格只读观察只用预检及后验的查询和文件比对。

已有解释器能import yaml时直接使用；缺依赖且允许临时准备时，在同一次uv进程内用PyYAML运行结构检查，避免把临时解释器路径带到进程结束后。以下PowerShell 7配方从已确认的包源根运行；替换已定位的真实验证器路径，不向业务环境安装依赖：

```powershell
@'
import runpy
import sys
from pathlib import Path

source = Path.cwd()
validator = Path(r"<实际验证器绝对路径>")
sys.argv = ["tools/skill_package.py", "structure", "--source", str(source),
            "--validator", str(validator), "--validation-python", sys.executable]
runpy.run_path("tools/skill_package.py", run_name="__main__")
'@ | uv run --with PyYAML python -X utf8 -
if ($LASTEXITCODE -ne 0) { throw 'Skill structure validation failed' }
```

由 Agent 按当前授权显式暂存本轮文件、提交、整合及正常推送；不强推或跳过钩子。整合改变验证输入时重验受影响部分。不确定推送是否成功时先查询远端包含关系，失败保留分支和日志。仅授权候选时在本地验证与保存后停止，不调用更新或部署。

## Manager 更新前

只有明确允许安装时进入本节；普通新会话不自动 fetch、检查全部上游或部署。选定完整 SHA，从该 SHA 的干净维护源执行 `uv run python tools/skill_package.py confirm-source --source '<干净源>' --revision '<完整SHA>'`，核远端主线与本次提交一致且清单指定的 push CI 已成功；仍在运行、失败或远端前进时先查状态，保留待安装，不把其他提交的绿灯当本次证明。GitHub Actions只运行检查，获得绿灯后由当前维护者继续Manager分发。

调用 `uv run python tools/skill_package.py preflight --source '<干净源>' --revision '<完整已验证SHA>' --skills-manager-cli '<实际CLI>'`。结果为 `preflight_ok` 才可继续；把完整 JSON 保存到本次已有证据目录，供后验通过 `--plan` 读取。这份记录是本轮更新前的预期，不是任务状态机或新的授权来源。

预检检查来源元数据、中央库与已声明 Agent 的完整资源是否属于源仓已提交的已知版本；未知编辑、额外文件、缺少入口但留有资料、外来源链接和资源内部链接均停止更新。文本仅对识别的 UTF-8 文本归一化 CRLF/LF，二进制逐字节判断。缺失的 Agent 目标可以保留待修，但不能在后验中记为完成。

记录保留技能 ID、标签、Preset 和既有部署集合。新技能未入库时预期 ID 为空且默认 library-only；已有技能通过 Manager 原位更新。新增技能使用准确的远端技能子目录入库；只有本轮明确批准新部署选择时，才在既有记录列明授权并调整该项预期，既有 ID 保持。预检记录不完整或来源/版本/技能集合不符时后验拒绝。

## 更新、定向修复与后验

Agent 直接使用 `manage-skills` 的 `skills check`、`skills update` 更新受影响技能；不为本次个人包更新其他技能。检查实际退出码和 JSON，`held_back_removals`、失败或未真正更新都保留未完成项。Manager 更新会刷新既有复制部署，正常链接继续读取中央库，默认不再对所有目标重复 deploy。

更新后调用 `uv run python tools/skill_package.py confirm-install --source '<同一干净源>' --revision '<同一SHA>' --skills-manager-cli '<实际CLI>' --plan '<本轮预检JSON>'`。后验核同一提交的全部技能资源、真实目标内容及链接归属，并对比更新前身份和部署选择；未入库、缺项、旧资源残留、陈旧副本或意外部署变化均拒绝通过。

仅对核实的缺失或陈旧目标，在当前授权集合内执行定向 `deploy --dry-run` 和 `deploy`，再核验；未变化且已有有效证据的内容复用。遇 `TARGET_CONFLICT`、来源歧义或未知修改，保留目标与原因，按 `manage-skills` 处理；不删除重装、不强制覆盖、不自行重建链接或重启应用碰运气。原版与归属不明技能保持原渠道。

输出 `installation_verified` 只证明本机这些文件与指定提交一致；完整分发继续下一节，真实宿主加载与另一台实体设备须有对应实测才可报告。

## 备份远端与跨设备检测

安装后用官方 CLI `skills check <技能> --force` 检测受影响技能；必须为 `up_to_date`。`unknown` 表示缺少基准，不能当没有更新。先核内容与来源并保护独有修改，再用官方 `skills update` 原位获取新版，重新检测，保留 ID、标签、Preset 与部署选择；不直接改数据库或伪填远端 SHA。

通过 Manager 的 `git status` 检查备份仓变化，保护其他活动编辑；在本次备份授权内用 `git commit --message '<说明>'` 和 `git push` 保存中央库及管理元数据。已被自动备份保存时复用。开发源和Manager备份仓分别核远端，不把本地 ahead/behind 缓存或“已提交”当推送成功，也不在Actions内另装或接管Manager。

调用 `uv run python tools/skill_package.py confirm-distribution --source '<同一干净源>' --revision '<同一SHA>' --skills-manager-cli '<实际CLI>' --plan '<预检JSON>'`。结果须为 `distribution_verified`：复核源与CI、本机完整资源和部署选择、更新检测、备份远端SHA，以及备份提交里的完整个人技能源文件和来源元数据。任一步失败保留已完成回执与下一步，不报告全部完成。

官方Manager版本可能在备份中省略源版本。此时回执必须显示 `needs_calibration_after_restore`：新设备或重新恢复后，先按同一来源取得最新维护规则，核备份内容、来源与独有修改，再用官方Manager原位更新需要使用的个人技能并重新检测；检测正常才开始依赖新版的维护。定时检查开启并不证明此状态可用。模拟设备恢复验证内容和该校准分支，实体设备不可见时明确未验；不宣称已修复官方界面，不安装派生版或改外部原版。

## 失败、并发与旧运行

Git 发布、中央库更新、Agent 核验分别报告。部分失败在任务原有记录中保留固定版本、预期、已完成项、失败和下一步；接续时先查实际内容再继续，不能因重跑命令就假定成功。多个技能更新不保证原子完成，失败期间不要启动依赖混合版本的新维护任务。

查询和文件比对不取得全局事务锁；由唯一负责人串行变更，发生并发变化时重新核对本轮预期与最终输入。工具核验不能替代 Manager 的错误/删除保护，也不能防止其他进程在核验后继续修改；需要的隔离应在写入前落实。

已固定的旧运行继续原 entry/runtime、测试与输入；其 `workflow-state`、执行快照和恢复材料原位保留，新检查不读取或改写它们。接续旧发布或转移旧安装责任按该任务明确权限处理，不把新接口冒充旧运行成功。只清理本任务拥有且不再需要的现场，保留未发布候选、失败及恢复依据。

读取限于当前动作所需正文；长输出保存到本轮日志，核实际退出码，按失败或进度需要读取；引用仍以所属文件解析，固定版本与必要完整性继续核实。测试夹具中的读取采样与接入/迁移状态仍服务其原验收，不属于退役的发布状态。
