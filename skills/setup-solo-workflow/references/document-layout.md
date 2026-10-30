# 项目目录、文档与产物职责

当前跨项目工作区契约。新项目直接采用；老项目的新任务沿本契约分类，已有运行路径、工具默认值和在途任务先保留为具名迁移例外，切换消费者并验证后退出。固定的是类型、路径与结束动作，有内容才创建目录。创建或变更资料落点、受管理产物，或归属/生命周期不清时读取；同源同版本已读且仍适用的内容可复用。

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
├── .artifacts/
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
| 一次开发验证的日志、报告、截图、轨迹、测试导出与下载 | .artifacts/active/<effort>/<run>/{logs,reports,screenshots,traces,exports,downloads}/ | 运行产物无活动用途后删无价值内容；必要原始证据归.artifacts/archive/<effort>/<run>，只选留logs/reports/screenshots/traces/exports/recovery；work按实际消费者退出、长期需要的下载归data/source，无活动用途的run实际退出 |
| 一次性脚本、评审diff、临时源代码/构建/数据库副本 | 同一run的work/；原生临时API可使用系统临时目录 | 验证/诊断用途结束且无活动消费者或独有未保存状态时释放；对应临时进程、端口和 worktree 按各自用途退出 |
| 本次编辑或清理的恢复点 | 同一run的recovery/ | 风险窗口关闭且保存验证完成即删除；仍需回滚则转本机证据归档并记录具体退出条件，已有Git足够时不再复制 |
| 必要本机原始证据 | .artifacts/archive/<effort>/<run>/，同effort的retention.json | 仅保留无法用提交和结论替代的最小证据，默认最多30天；到期同次检查处置，明确长期用途则迁为正式样本/数据，不无限续期整棵现场 |
| 用户原始输入、长期参考数据 | data/source、data/reference | 按业务或用户确认的保留规则处置；任务结束不自动删除原件。测试样本脱敏后归tests/fixtures |
| 用户成品 | exports/<deliverable>/ | 交付并确认可取得后按约定移交/清理；持续需要的成品由交付要求持有，不能当测试导出删掉 |
| 运行数据库/上传、状态、缓存、服务日志 | var/{data,state,cache,log}/ | 数据随业务生命周期；状态失效即退役；缓存可重建才清；日志按项目配置轮转及到期清理 |
| 程序临时文件、业务备份 | var/tmp、var/backups | 临时文件在成功/失败的finally中释放；备份在回滚/保留窗口关闭且恢复依据足够时删除 |
| 构建产物 | dist/或工具强制输出目录 | 无用构建用完即删；在用构建待部署切换与回滚窗口结束再清 |

`.git/`只放版本控制元数据；.scratch和.artifacts不是永久收容目录。数据、在用构建、活跃任务及他人未提交修改的退出条件由各自主人持有，不因本任务结束失去用途。未知归属或缺授权时说明具体缺口并保持未完成，不能假报已清理。

### Git 历史与具名例外

新项目和已获批准的迁移默认 Git-only：有效独有知识和理由先归现行主人；原文在可达提交中可按原路径恢复且无活动消费者时，删除当前原件。仅需追溯不构成永久 docs/archive、历史索引或兼容占位的理由。确有独立使用者、外部契约或长期引用必须保持当前文件时，说明具名用途并保留历史含义；ADR的持续决策用途按[documentation](documentation.md)处理。此默认不授权全仓清除旧历史；未批准迁移的既有项目、非Git原始证据、用户数据、运行资源及备份仍按各自生命周期处理。工具 paths.history 继续服务具名历史例外。

### 创建、运行和结束

1. **开始。** 确认根、项目例外、dirty及活动消费者；确有受管理任务/运行产物时确认 effort/run 身份。首次接入给实际生成入口、示例、.gitignore和检查接好固定路径；绑定本技能随包分发的scripts/workspace_check.py。正常任务不扫描全部历史正文。
2. **生成。** 使用检查脚本paths给出的路径；先核绝对路径与链接目标。需要持久材料才建文件。`.scratch`只放任务Markdown和逐票资料，运行输出进对应kind；用户原件、凭据和共享依赖不当临时输入复制。
3. **运行结束。** 成功与失败均核本次资源用途；用途结束且无活动消费者/独有未保存状态的临时资源在本次收尾释放。主预览仍供用户验收时保持有效，在已有任务记录中保留负责人、版本、用途和退出条件；技术完成、用户验收与资源退出分别报告。停止服务不等于删除其数据库、源码或工作树。失败未归因时仅留最小必要原始证据；先脱敏，再在.artifacts/archive/<effort>/retention.json写reason和expires_on（YYYY-MM-DD，最长30天）。随后归档选留证据、删除其余；无活动用途后实际移出 active 的 run。已触发检查的运行执行 run-closed；仍有有效消费者的运行保持活动，不冒报已关闭。
4. **改动、阶段或任务结束。** 核本次授权范围和真实验收；先将有效独有知识与必要理由归现行主人，再修引用、消费者和当前状态。已无活动用途、可从可达Git提交及原路径恢复的原文直接删除，不另留永久归档、索引或占位；父任务继续时也逐文件/段落执行。仅保留当前验收、复测、范围或依赖所需最小材料，写明用途与退出条件。effort 全部范围结束后实际退出.scratch和active；已触发检查的任务执行 closed。纯问答或没有产物时不造目录/归档件。
5. **完成反馈。** 报实际删除/归档/保留位置、保留理由、退出条件及检查结果。清理/归档是完成动作，不是“以后注意”或额外待办；检查失败则本轮收尾未完成。检查只读取文件，实际迁移删除由当前负责人按授权执行，没有后台定时删除承诺。

从本技能实际安装目录运行（不从业务cwd猜位置）：

```text
python <setup-solo-workflow>/scripts/workspace_check.py paths --root <project> --effort <slug> --run <run>
python <setup-solo-workflow>/scripts/workspace_check.py check --root <project> --effort <slug> --phase active
python <setup-solo-workflow>/scripts/workspace_check.py check --root <project> --effort <slug> --run <run> --phase run-closed
python <setup-solo-workflow>/scripts/workspace_check.py check --root <project> --effort <slug> --phase closed
```

check的JSON保留顶层ok/errors和总体退出码，并增加scope（本任务、其归档及共享路径问题）与other_archives（其他归档问题）两组；scope通过不代表全库通过，其他归档错误仍使总体非零。active检查本任务分类及本机证据归档到期；run-closed要求该run已退出active；closed要求本任务.scratch和active均不存在。三种检查都验证本机归档理由、期限及链接边界。它不证明语义分类、隐私脱敏、业务验收或全盘清理，项目已有检查与人工判断仍需完成。项目接入、专项迁移、复杂运行产物、共享资源退出或分类/保留有具体风险时，执行相关检查并处理到期结果。简单任务无相关产物或变化时，不制造 effort/run、空目录或归档，也不重复无输入变化的治理检查。已触发检查非零时解决原因或保留真实阻塞，不改预期、伪造归属或跳过失败。run-closed/closed 只判定其消费的资源范围，不要求交付页面后立刻停止所有服务。没有正在执行的 Agent 时不会在截止时刻自动运行。

项目.gitignore须忽略.artifacts、var、.env、依赖环境和可重建产物；.scratch按tracker需求跟踪，data/source及exports默认忽略且不得强制提交。既有更严格的隐私、原件或服务要求继续有效。原生工具输出不可配置时在workflow逐项记默认路径、消费者、生命周期与迁移/保留理由，不用一条“沿项目惯例”放开所有目录。

未分类材料先判定其真实类型；确有新类别时维护本契约及检查。专项迁移按document-migration.md保护现有现场；按真实用途选留，不为清理再复制全部待删文件或建设第二套清单平台。

`requirements.md` 或 `architecture.md` 确实过大时，保留稳定入口，将不同主题的唯一正文拆入同名目录 `docs/requirements/` 或 `docs/architecture/`，入口只提供主题导航和必要跨主题约束。项目已有其他名称的有效权威或外部工具契约时，核真实消费者后复用并明确入口；不为名字一致增加迁移，也不并设同义正文。

### 文档内容与实际消费者

建立或重构文档体系、判断内容职责时读 [documentation.md](documentation.md)：按读者任务区分教程、操作、技术参考与解释，借用必要架构视角，保护ADR替代关系；同时区分现行权威、任务、状态及证据。该参考拥有内容职责，本文件只持物理落点与生命周期。

生成或迁移时仍核工具读取、包内相对引用、在途任务与恢复依据；文档数量和目录检查不证明内容有效。已无活动用途的普通任务材料按本页退出，承担决策谱系的ADR继续保留。

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
