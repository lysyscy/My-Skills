# Host adapters

Only the selected host section is included when deploying an entry.

<!-- host:codex -->
## Codex subagent configuration

Before dispatch, choose a supported model, reasoning effort, and context mode for the subtask's difficulty, uncertainty, risk, and context needs. Briefly state the selected configuration and its basis. When overriding model settings, pass both model and reasoning effort explicitly. When inheriting, establish the inherited values and confirm they fit the task. Use a full-history fork that requires inheritance only when those settings fit.

## Windows shell

For shell-based Unicode processing or captured native-command output on this Windows host, prefer the verified Python interpreter with `-X utf8`, explicit encodings, and checked subprocess return codes. Preserve non-UTF-8 source encodings. When diagnosing runtime, encoding, or Git ownership problems, consult [local runtime guidance](C:/Users/Administrator/.codex/local-hooks/README.md).

<!-- fastctx:begin -->
## Local files

When available, prefer FastCtx for local file inspection, search, and discovery. Use its `replace` for mechanical replacements; use `apply_patch` for semantic edits or generated content. Follow the current tool definitions for paths, batching, and pagination.
<!-- fastctx:end -->

<!-- host:dsh -->
## DSH delegation

For in-process delegation, use the current session's inherited model and reasoning settings by default. Apply an explicit user selection when the active tool supports it. Report inherited or resolved settings when exposed. Use the shared target and context checks before dispatch.

## DSH memory

Let the Hindsight Coding Agents plugin handle automatic project recall and transcript retention in enabled workspaces. Use its project tools for deliberate project memory calls. Use `mcp__hindsight_personal__recall` and `mcp__hindsight_personal__sync_retain` for the fixed `personal-preferences` bank. Use provider HTTP APIs only for diagnosis.

At a substantive new task, project change, or continuation, reuse available context first. Recall only when missing preferences, decisions, or verified experience could affect the work, or when the user explicitly requests it. Skip automatic recall on self-contained trivial requests. Use a focused, low-budget query to the relevant bank. Distinguish no matches, an uncreated bank, and a failed request. Continue work that does not depend on unavailable memory.

Verify project routing in `~/.hindsight/coding-agent.json`. Prefer an explicit `mapPathToBank` binding and otherwise use the configured `bankIdTemplate`. Reuse the established bank for subdirectories and linked worktrees. DSH's `default-workspace` has automatic project memory disabled. When a discussion there establishes a project-specific decision, continue in that project's workspace if a scoped project tool is unavailable. A project mentioned in source text does not authorize querying its bank. Create a bank only for the first useful, authorized write.

For deliberate retention, save confirmed lasting preferences, useful background of confirmed decisions, and evidence-backed reusable lessons at confirmation or a natural completion point. Preserve scope, date or version, source, and confirmation status. Record branch, revision, and merge status when relevant. Distinguish implementation, verification, acceptance, merge, and deployment.

Honor current exclusions and stricter host limits. Keep credentials, unapproved historical chats or original business files, guesses, temporary logs, and full task-state replicas out of deliberate writes. Retain useful background or pointers. Skip writes, extra review, and queues when there is no useful new information. Apply the workflow selected for the task independently of memory use.
