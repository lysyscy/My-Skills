# 目录治理

目录归属、保留条件或通用清理范围需要统一入口时接入。按[工具部署](../templates/README.md)选 `directory-governance`，根据[示例清单](../templates/directory-manifest.example.json)建立项目 JSON。将已采用的 `.agents` 作为 Git 跟踪的源码目录登记。

每行记录路径、主人、分类、Git 策略、管理入口、保留条件和退出条件。嵌套规则也登记父路径。只有需要审计子目录时才启用 `check_children`。已有运行组保留记录时可用 `retention_groups` 核到期情况，并把处置交给生产者。

- `hard_protected` 填任何通用清理都不得触碰的目录。受保护类别、有管理入口、有软阈值或留有登记记录的父级也保护后代。子级的 `apply_eligible` 无法解除这些保护。
- 管理发布目录时加 `releases` 对象，填写 `directory`、`registry` 和 `key`。前两项是仓库相对路径，`key` 指向登记 JSON 中以目录名为键的对象。审计报告未登记目录，发布目录始终交给发布负责人。
- 仅确认无主的空退役目录可设 `class: residue`、`owner: none`、`manager: none`、`apply_eligible: true`。需要扫描源码目录下失去源文件的 Python 字节码缓存时，可用同样的条件显式登记 `**/__pycache__`。

```text
python -B tools/audit/directory_audit.py --root . --manifest tools/audit/directory-manifest.json
python -B tools/audit/directory_audit.py --root . --manifest tools/audit/directory-manifest.json --staged
```

默认只读，与 `--dry-run` 相同。将 `--staged` 接到提交检查，暂存新顶层目录时同时暂存清单。工具读取同一 Git 索引中的路径及清单。它只校验新加或改动文件的顶层目录登记。

启用 `--apply` 前先核对 `RESIDUE` 和项目授权。工具仅处理可复核的空目录或无源码缓存，并在处理前重查 Git 索引、父级保护和文件状态。未知归属、链接、实际业务文件和已登记运行由对应主人处理。
