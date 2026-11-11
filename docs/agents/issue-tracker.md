# 本地 Markdown 票库

规格写入 `.scratch/<effort>/spec.md`；实施票一票一文件，位于 `.scratch/<effort>/issues/<NN>-<slug>.md`，从 `01` 编号。查票使用明确路径或当前 effort 内的票号。`Blocked by:` 记录前置票的编号或名称；前置票完成后才能接手。

分诊状态写在 `Status:`，按[标签映射](triage-labels.md)填写；分类写在 `Category:`（`bug` 或 `enhancement`）。评论和处理原因追加到 `## Comments`。`wontfix` 保留票文件和原因。

上述约定用于后续技能操作；现有 `.scratch/` 资料保留原路径。GitHub Issues 和 PR 不纳入本地分诊。

## Wayfinding operations

- 地图放在 `.scratch/<effort>/map.md`；决策票同样一票一文件，写 `Type:`（`research`、`prototype`、`grilling` 或 `task`）和 `Blocked by:`。
- 按编号选第一张未认领且前置票均已解决的票，开始前保存 `Status: claimed`。
- 解决时追加 `## Answer`，改为 `Status: resolved`，并在地图的 `Decisions-so-far` 追加结论摘要和票链接。`claimed` 和 `resolved` 只用于 Wayfinding。
