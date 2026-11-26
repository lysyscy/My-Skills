# 本地 Markdown 票库

规格写入 `.scratch/<effort>/spec.md`；实施票一票一文件，位于 `.scratch/<effort>/issues/<NN>-<slug>.md`，从 `01` 编号。查票使用明确路径或当前 effort 内的票号。`Blocked by:` 记录前置票的编号或名称；前置票完成后才能接手。

实施票在 `Status:` 记录状态，沿用本地分诊值 `needs-triage`、`needs-info`、`ready-for-agent`、`ready-for-human` 和 `wontfix`。分类写在 `Category:`（`bug` 或 `enhancement`）。评论和处理原因追加到 `## Comments`。`wontfix` 保留票文件和原因。

现有 `.scratch/` 地图和票保留原路径、状态和依赖，接续时沿用该任务已采用的约定。GitHub Issues 和 PR 沿各自入口管理。
