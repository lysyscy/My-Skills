# 项目目录、文档与产物职责

当前跨项目工作区接入方法；生命周期的新登记、30/60天与保护规则由[产物生命周期](artifact-lifecycle.md)持有。接入时把实际入口布置到项目正文；日常任务从该入口读取并使用已接入的 register/lease/close，新产物以 register 返回目录为准。未迁移旧生产者及固定旧运行才沿下文旧目录分支，不把旧路径查询作为新产物入口。物理落点与消费者按项目适配；文档内容职责与重构读[documentation](documentation.md)。老项目已有运行路径、工具默认值和在途任务保留为具名迁移例外，切换消费者并验证后退出。有内容才创建目录；创建或变更资料落点、受管理产物，或归属/生命周期不清时读取本接入参考，同源同版本已读且仍适用的内容可复用。

## 固定位置、按需创建

```text
project/
├── README.md                         # 人的入口、使用及目录导航
├── AGENTS.md                         # Agent边界及按条件读取的指针
├── CONTRIBUTING.md                   # 确有开发/维护协作时的入口；复用已有同职责指南
├── CODING_STANDARDS.md               # 确有项目编码约束时；可指向既有专题规范
├── GLOSSARY.md                       # 确有领域术语时；多上下文使用GLOSSARY-MAP.md
├── src/                              # 自有源码；多组件在apps/<组件>/下采用同一结构
├── tests/fixtures/                   # 自动测试与经脱敏的长期回归样本
├── resources/                        # 随产品部署的模板、静态资源及模型等运行本体
├── tools/                            # 可复用的开发、验证及维护脚本
├── ops/                              # 部署、服务起停、迁移及恢复入口
├── docs/
│   ├── agents/                       # workflow、issue-tracker、domain及必要triage-labels
│   ├── requirements.md              # 当前需求；过大时拆同名目录
│   ├── architecture.md              # 当前结构；过大时拆同名目录
│   ├── status.md                    # 确有跨任务状态/交接需要才建立
│   ├── adr/0001-<slug>.md            # 重要决定；既有编号不重写
│   ├── guides/<topic>.md             # 长期操作方法
│   ├── reference/<topic>.md          # 技术契约、接口、格式等精确查询
│   └── archive/<effort>/             # 有具名独立用途、确需保留当前文件的历史例外
├── .scratch/<effort>/                # 活动任务：spec、map、research、questions、evidence、handoff及issues
├── .artifacts/                      # 仅未迁移旧生产者与固定旧运行；新登记区由实际接入入口持有
│   ├── active/<effort>/<run>/        # 当前运行的开发验证产物
│   │   └── <kind>/                  # logs、reports、screenshots、traces、exports、downloads、work、recovery
│   └── archive/<effort>/             # 必要的本机原始证据；retention.json约束保留期限
├── data/source/                     # 用户原始输入，默认不提交、不覆盖
├── data/reference/                  # 经确认的长期参考数据；隐私数据不入Git
├── exports/<deliverable>/            # 交付给用户的成品及必要说明
├── var/                             # 程序运行数据；整体忽略Git
│   ├── data/                        # 数据库、上传文件等不可随意丢失的数据
│   ├── state/                       # 登录凭证、会话、进度与恢复游标
│   ├── cache/                       # 能按明确方法重建的缓存
│   ├── log/                         # 服务运行日志
│   ├── tmp/                         # 单次运行临时文件
│   └── backups/                     # 运行数据的必要恢复点
└── dist/                            # 可重建构建产物；正式在用版本按部署协议退出
```

`src/`等是自有工程默认；框架、包管理器、技能分发或宿主明确规定的布局（如技能的SKILL.md/scripts/references/assets、Python包、.venv、node_modules、构建工具的build/）服从其真实契约，在项目workflow中记录具体路径与理由。仅“以前这样放”“目录已存在”不构成永久例外。新项目不另造scratch、artifacts、temp、local等同义收容目录；已有例外不要求通过清空目录立即统一。

### 工程文件与各类产物

先按本表定类型，再创建实际输出；同一文件只保留一份权威。新类型先补本表及路径检查，再让生成入口使用；不临时发明落点。一次性脚本不因可执行而成为tools中的长期工具。

| 类型 | 固定落点 | 生命周期结束动作 |
|---|---|---|
| 源码、测试、可复用工具、运行资源 | src、tests、tools、resources；运维入口在ops | 随实现维护；功能退役同批修消费者并删除，必要来源由Git保存 |
| 依赖声明、锁、编译及宿主配置 | 对应工具要求的项目/组件根；依赖环境沿管理器目录 | 声明与锁同行；任务副本依赖用完释放，共享缓存按管理器清理 |
| 凭据与本机配置 | 根.env或宿主凭据存储；动态登录状态在var/state | 不入Git；轮换/失效即撤销或删除，不能复制进证据或归档 |
| 当前业务、架构、术语、指南、参考、重要决定 | 上述docs位置与GLOSSARY | 修改唯一正文与引用；有效独有知识先归现行主人，历史默认由可达Git提交及原路径追溯，原文件退出 |
| 任务规格、调查、澄清、地图、票、持久证据、交接 | .scratch/<effort>/{spec,research,questions,map,evidence,handoff}.md及issues/ | 按文件/段落用途退出，不等父任务全部完成；有效知识先归现行主人，Git可追溯且无活动用途的原件删除；仅保留具名活动验收所需材料 |
| 一次开发验证的日志、报告、截图、轨迹、测试导出与下载 | 项目实际接入入口的 register 返回目录 | 读写经 lease；用途结束时释放无价值内容，必要证据按组 close，未决用 hold；长期需要的下载归data/source |
| 一次性脚本、评审diff、临时源代码/构建/数据库副本 | 已登记组内按用途组织；原生临时API可使用系统临时目录 | 验证/诊断用途结束且无活动消费者或独有未保存状态时释放；对应临时进程、端口和 worktree 按各自用途退出 |
| 本次编辑或清理的恢复点 | 已登记且明确恢复用途的组 | 恢复窗口内保持保护；风险窗口关闭且保存验证完成后按其用途退出，仍需回滚则保留保护及具体解除条件，已有Git足够时不再复制 |
| 必要本机原始证据 | 原登记组，不另复制进旧archive | 仅保留无法用提交和结论替代的最小证据；用途结束后 close，普通30天、明确跨月60天，未决按hold保护；明确长期用途则迁为正式样本/数据，不无限续期整棵现场 |
| 用户原始输入、长期参考数据 | data/source、data/reference | 按业务或用户确认的保留规则处置；任务结束不自动删除原件。测试样本脱敏后归tests/fixtures |
| 用户成品 | exports/<deliverable>/ | 交付并确认可取得后按约定移交/清理；持续需要的成品由交付要求持有，不能当测试导出删掉 |
| 运行数据库/上传、状态、缓存、服务日志 | var/{data,state,cache,log}/ | 数据随业务生命周期；状态失效即退役；缓存可重建才清；日志按项目配置轮转及到期清理 |
| 程序临时文件、业务备份 | var/tmp、var/backups | 临时文件在成功/失败的finally中释放；备份在回滚/保留窗口关闭且恢复依据足够时删除 |
| 构建产物 | dist/或工具强制输出目录 | 无用构建用完即删；在用构建待部署切换与回滚窗口结束再清 |

`.git/`只放版本控制元数据；.scratch和.artifacts不是永久收容目录。数据、在用构建、活跃任务及他人未提交修改的退出条件由各自主人持有，不因本任务结束失去用途。未知归属或缺授权时说明具体缺口并保持未完成，不能假报已清理。

### Git 历史与具名例外

新项目和已获批准的迁移默认 Git-only：有效独有知识和理由先归现行主人；原文在可达提交中可按原路径恢复且无活动消费者时，删除当前原件。仅需追溯不构成永久 docs/archive、历史索引或兼容占位的理由。确有独立使用者、外部契约或长期引用必须保持当前文件时，说明具名用途并保留历史含义；ADR的持续决策用途按[documentation](documentation.md)处理。此默认不授权全仓清除旧历史；未批准迁移的既有项目、非Git原始证据、用户数据、运行资源及备份仍按各自生命周期处理。工具 paths.history 继续服务具名历史例外。

### 创建、运行和结束

1. **开始。** 确认根、项目实际接入入口、例外、dirty及活动消费者，核本次相关区域前序遗留的用途和归属；只读请求止于判断，实施时及时处理已确认无用途且在授权范围内的内容，未知项先核实并保护。新产物确认登记组与负责人，旧分支才沿已有 effort/run 身份；正常任务不扫描全部历史正文。无项目任务仅使用实际已登记且入口可用的个人运行区；未接入则说明并保留现状，不把本参考当作接入完成。
2. **生成与接入。** 新产物从实际接入入口 register，使用返回目录并经 lease 读写，先核绝对路径与链接目标。首次接入或修改生产者时，将输出、退出条件和成功/失败后的释放接到实际脚本、任务入口或资源管理器，同步示例、.gitignore及必要检查；短命资源用finally或等效机制退出。仅对归属、边界与删除条件可确定且已授权的资源自动清理；需用户验收、共享消费者或回滚判断的资源保留到条件满足。需要持久材料才建文件；用户原件、凭据和共享依赖不当临时输入复制。
3. **用途或运行结束。** 按资源各自用途及时释放临时进程、端口、工作树及副本，保留活动消费者和独有未保存状态。主预览仍供用户验收时保持有效，在已有任务记录中保留负责人、版本、用途和退出条件；停止服务不等于删除其数据库、源码或工作树。失败未归因时保留最小必要原始证据并 hold，不能据进程退出自行 close。新登记组在用途结束、必要依据归位后 close，不复制到旧archive，也不写retention.json。仍有有效消费者的运行保持活动，技术完成、用户验收与资源退出分别报告。
4. **改动、阶段或任务结束。** 核授权范围与实际验收，逐文件/段落按上表及Git历史规则处置，修引用、消费者和当前状态；父任务继续也释放已完成部分。仅保留当前验收、复测、范围或依赖所需最小材料，写明用途、主人与退出条件。effort 全部范围结束后实际退出其.scratch；旧分支同时按既有条件退出active。纯问答或没有产物时不造目录/归档件。
5. **检查与反馈。** 新登记组使用实际接入工具的 check；旧目录退出才执行下节 run-closed/closed。报告实际删除/归档/保留位置、理由、退出条件及检查结果；检查失败或用途未核清则对应收尾未完成。检查器只读核验，实际处置由当前负责人或已接入的生产者按授权完成；只有已配置并验证的自动化才可承诺相应后台动作，普通 Agent 工作不承诺会话外持续清理。

### 未迁移旧生产者与固定旧运行

只有此分支继续使用 `.artifacts/active/<effort>/<run>`、`.artifacts/archive/<effort>/<run>` 与同effort的 `retention.json`。用途结束后保留最小必要证据、退出无用途的active运行；`reason`及`expires_on`保持旧检查契约：日期格式 `YYYY-MM-DD`，检查时晚于当日且不超过其后30天。不得把新登记的60天或带时间截止值写入旧字段；旧材料不自动登记、搬迁或交给定时器。需要改变旧生产者时先切换其真实消费者并验证。

旧路径查询与检查从本技能实际安装目录运行（不从业务cwd猜位置）；`paths`只查询旧路径，不创建或登记产物：

```text
python <setup-solo-workflow>/scripts/workspace_check.py paths --root <project> --effort <slug> --run <run>
python <setup-solo-workflow>/scripts/workspace_check.py check --root <project> --effort <slug> --phase active
python <setup-solo-workflow>/scripts/workspace_check.py check --root <project> --effort <slug> --run <run> --phase run-closed
python <setup-solo-workflow>/scripts/workspace_check.py check --root <project> --effort <slug> --phase closed
```

旧check的JSON保留顶层ok/errors和总体退出码，并增加scope（本任务、其归档及共享路径问题）与other_archives（其他归档问题）两组；scope通过不代表全库通过，其他归档错误仍使总体非零。active检查本任务分类及本机证据归档到期；run-closed要求该run已退出active；closed要求本任务.scratch和active均不存在。三种检查都验证旧归档理由、日期期限及链接边界；它们不证明语义分类、隐私脱敏、业务验收或全盘清理，也不作为新登记组的检查入口。新登记可由实际接入工具的check核验；确需workspace_check适配时只用 `check --lifecycle-root <已登记专用区>`，不混用旧参数。按本次受影响分支执行相关检查，简单任务无相关产物或变化时不制造记录，也不重复无输入变化的检查。非零结果须解决原因或保留真实阻塞，不改预期、伪造归属或跳过失败。

### 项目适配

项目.gitignore须忽略.artifacts、var、.env、依赖环境和可重建产物；.scratch按tracker需求跟踪，data/source及exports默认忽略且不得强制提交。既有更严格的隐私、原件或服务要求继续有效。原生工具输出不可配置时在workflow逐项记默认路径、消费者、生命周期与迁移/保留理由，不用一条“沿项目惯例”放开所有目录。

未分类材料先判定其真实类型；确有新类别时维护本契约及检查。专项迁移按document-migration.md保护现有现场；按真实用途选留，不为清理再复制全部待删文件或建设第二套清单平台。

`requirements.md` 或 `architecture.md` 确实过大时，保留稳定入口，将不同主题的唯一正文拆入同名目录 `docs/requirements/` 或 `docs/architecture/`，入口只提供主题导航和必要跨主题约束。项目已有其他名称的有效权威或外部工具契约时，核真实消费者后复用并明确入口；不为名字一致增加迁移，也不并设同义正文。

### 5.5 普通软件项目示例（模拟，不是被审计项目）

假设一个“记录导入工具”已经有应用代码、导入规则、模块说明、操作指南和两张实施票，则可形成：

```text
record-importer/
├── README.md
├── AGENTS.md
├── GLOSSARY.md
├── package.json                      # 示例项目自己的可执行配置，不是全局指定
├── src/
├── tests/
├── docs/
│   ├── agents/{workflow,issue-tracker,domain}.md
│   ├── requirements.md               # 当前导入/重复处理等已确认规则
│   ├── architecture.md               # 输入、转换、持久化之间的实际关系
│   ├── adr/0001-source-preservation.md
│   ├── guides/import.md
│   └── reference/input-format.md
└── .scratch/import-validation/
    ├── spec.md
    └── issues/{01-feedback,02-integration}.md
```

本次增加导入校验时，实施者读取任务范围、requirements 的相关定义、输入格式及有关模块/测试；只有确实影响操作方式时才更新 guide。票只记录本次交付及验收引用，不再持有一份完整导入规则。测试命令来自该示例项目的配置，不从个人包下发。没有历史归档需要，因此示例也不预建 archive。

### 5.6 Excel/JSON 派生知识库示例（模拟裁剪）

此例**只假设** JSON 是经确认的规范数据、Excel 是供人阅读的派生产物，用来验证目录裁剪；不替用户决定真实知识库的数据主从关系或设计业务系统。

```text
quotation-notes/
├── README.md
├── AGENTS.md
├── data/                             # 示例资料，不由此目录契约规定其字段
├── exports/                          # 示例派生产物，是否入库由该项目决定
└── docs/
    ├── agents/workflow.md
    ├── requirements.md               # 已确认的资料含义、主从关系与更新边界
    ├── architecture.md               # 确有必要时用很短正文说明派生方向
    ├── guides/update.md
    └── reference/source-format.md
```

它沿用相同现行路径，但没有应用部署、前后端、浏览器回归、空 ADR、空 tickets 或空 triage 文件。日常任务验收是来源对应、唯一来源未被反向覆盖、派生一致性及文件可读性；不启动无关应用测试。只有多步改造或需要接续时才建立 effort 资料。

### 5.7 项目例外的边界

必要例外包括：真实多上下文布局、外部工具硬编码的资料位置、已有 tracker 的权威状态、合规/第三方契约不能移动的文件，以及已有同职责权威可有效消费、迁移收益不足的文档位置。例外在 `docs/agents/workflow.md` 用一小段写明**适用范围、原因、实际权威、读取方式及需重新评估的条件**，不建立独立例外登记平台。

“旧文件很多、暂时不想迁”是迁移状态，不是复用依据。完成条件是：现行权威位于约定位置或有明确消费依据的既有位置；入口和实际消费者可达且不依赖临时过渡；没有两份同义现行正文。保留的位置是当前唯一主人时，不把它误称待删除的兼容层。禁止凭全局默认静默覆盖更严格的安全、隔离、验收或模型限制。
