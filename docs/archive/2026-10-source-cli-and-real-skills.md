# 2026-10-18 源核验与真实 Skill 测试实施记录

历史验收记录，仅证明本次输入与环境。基线为 `7a23756cb1ad2e7916343ab84a12a30f4247bc80`；开始时 main、索引和工作区干净，origin 与清单一致。用户批准 C1/C2/C3、提交及正常推送，不含安装或部署；在独占 worktree 串行实施。

## 实际结果

- C1：只调整 `tools/skill_package.py:main` 的分派，源确认在定位 Manager 前执行。新增 `tests/test_source_cli.py`，复用原夹具、临时裸仓和固定 CI 返回，直接调用 CLI main，不提供 Manager 路径。
- C2：新增 `tests/test_real_skill_structure.py`，将真实 skills 复制进原夹具并调用既有 discover；保留 symlinks，不增加硬编码清单或解析器。
- C3：未改动。用户在看到下述旧版观察和环境限制后明确裁决“按计划停止 C3，保留旧版”，符合实施计划第 5.4 节。不是授权缺失，也不是声称已完成行为改进。

## 确定性验证

Windows x64、uv、CPython 3.15.0，保留 pyproject、Python 版本文件与 uv.lock。开始时 `uv sync --locked --check --offline --no-python-downloads` 退出 0；隔离 worktree 使用同一受管解释器创建独立零依赖环境。

以下 unittest 均经 `uv run --locked python -m unittest discover -s tests` 执行：

| 检查 | 实际结果 |
| --- | --- |
| C1 修复前，`-p test_source_cli.py -k test_source_cli_works_without_manager -v` | 1 项失败、退出 1；CLI 返回 `blocked / Skills Manager CLI is unavailable`，定位 Manager 1 次 |
| C1 修复后，`-p test_source_cli.py -v` | 4 项通过、退出 0；覆盖无 Manager 成功、脏源、精确 SHA/workflow/push/成功 CI、三个 Manager 动作仍依赖 Manager |
| `-p test_manager_sync.py -v` | 原 22 项通过、退出 0 |
| `-p test_distribution.py -v` | 原 7 项通过、退出 0 |
| `-p test_real_skill_structure.py -v` | 1 项通过、退出 0 |
| 独占一次性副本中把真实 setup 的 name 改为 definitely-wrong-name，运行相同 C2 入口 | 1 项 ERROR、退出 1，异常为 `Skill directory/frontmatter mismatch: setup-solo-workflow`；负例副本已释放 |
| 最终完整 `-v` | 79 项，75 通过、4 跳过、0 失败，退出 0；104.834 秒 |

4 项跳过均为原有 Windows 环境复用集成测试，要求显式 ENV_REUSE_ROOT；本次未改环境实现，按实施计划未启用。

原 structure 入口使用宿主系统 skill-creator/scripts/quick_validate.py 和既有 skill-validation-venv 解释器，实际 PyYAML 探测及三个 Skill 验证全部退出 0，状态 verified。没有新增依赖。

## C3 宿主观察与停止依据

冻结规则 R0、源 S0 和旧版 B0 均取上述基线；实际消费项目 `.agents/skills` 中完整的三个 Skill 副本。消费后逐项资源指纹与源一致。未生成 C3 候选，未改变全局安装内容，I0 仅为该合成项目副本。

使用本机 Codex CLI 0.163.0-alpha.10.2、gpt-6.1-sol / high，以新上下文、read-only sandbox 串行执行一次显式 `$improve-workflow` 只读任务。合成报告描述：40 次逐条收据查询任务一直正常完成，外部候选声称现有批量接口能减少往返；字段、顺序、失败及重试语义与净收益尚未实测；只授权分析。

旧版实际读取项目内 SKILL、选择及能力参考，把外部候选判为“待验证，值得获准后的项目小场景验证”，指出正常成本机会、等效语义尚缺证据、落点是项目调用；未直接采纳、改源或安装。这是一次局部观察，不能证明旧版普遍可靠或 C3 没有任何价值。

该次 shell 读取发生 `CreateProcessAsUserW failed: 5 (拒绝访问。)`，执行者改用 MCP 文件读取。无法证明该工具面受同等写隔离约束，因此不把本次运行视为合格 A/B，不尝试放宽沙箱或修改全局环境。进程自然退出 0，总时长 38.281 秒；原始 usage 为 input_tokens=154648、cached_input_tokens=129792、cache_write_input_tokens=0、output_tokens=1057、reasoning_output_tokens=248，保留原字段，不相加或推算费用。仅 1 次任务执行，无候选、无保留案例及比较收益结论。

Desktop 隐式触发、稳定行为收益、长期 Token/速度、实际 Manager 和第二设备均未验证。用户选择停止后不扩大实验。

## 差异审查与边界

主 Agent 完成差异自查，无新增未决发现；未把自查称为独立审查。源干净/固定提交/远端 SHA/精确 push CI 的实现和三项 Manager 契约保持；C2 删除仅限原夹具独占的临时目录。原测试、Skill 文档、共享能力选择、CI、清单、锁与版本要求均保留。`git diff --check` 通过。

C2 仅覆盖既有发现和基础元数据契约，不承诺完整 YAML、缺失入口清单或宿主质量。无新依赖、平台、扫描任务或协调机制；长期新增维护限两个沿用原夹具的测试文件。Git 保存与远端状态以实际提交及最终回执为准，不在此建立状态机。
