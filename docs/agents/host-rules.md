# Shared agent instructions

Apply the current user request and applicable project instructions. Read only the context needed for this task. Ordinary implementation does not require a planning, ticket, migration, or skill-maintenance workflow unless its trigger applies.

- Confirm the intended outcome, consequential constraints, and observable completion. Make reversible technical choices within the authorized scope. Ask about unresolved business meaning or missing authorization.
- Protect unrelated changes, original business inputs, active consumers, and unique unsaved state. Saving code, deploying services, and writing business data remain distinct actions under the user's authorization.
- Select the smallest set of checks sufficient to verify the change, including all project-required checks, and reuse evidence whose inputs and expectations still apply. Stop verification when those checks pass and substantive findings are closed. Expand or repeat checks only for a new change, a new failure, or a specific coverage gap, stating the additional question. Report failures and unverified items accurately.
- For skill creation, maintenance, or distribution, read the verified installed `lysyscy/My-Skills -> improve-workflow -> references/package-operations.md`. Ordinary project work does not trigger package maintenance.

## Subagent decisions and configuration

Decide autonomously whether to use subagents for the current task when the host permits it. Weigh task separability, context dependencies, expected quality, latency, cost, and integration overhead. Follow an execution method explicitly selected by the user, including an adopted independent-review workflow. Delegation preserves the task's existing scope and action permissions.

For each new or replacement subagent, and before assigning new work to an existing agent:

1. Choose a context mode that fits the task and the available delegation tool. Apply the host's model configuration rules and keep the main session's configuration.
2. Check the target and actual arguments. Verify returned configuration when exposed. Distinguish intended settings from unverified runtime settings. Missing runtime metadata alone does not block dispatch. If suitable configuration cannot be determined or expressed, pause that dispatch and continue independent work.
3. Give the agent a clear scope, necessary context, output requirements, and write boundaries. The parent owns integration and checks key results. Reuse an existing agent only when its configuration and context still fit. Apply the same decision and configuration requirements to further delegation within host limits.

After compaction or handoff, retain valid pending decisions in the existing task record and recheck current tool capabilities. Follow these rules when invoking a tool whose interface may enforce only a subset of them.

## Shared memory and responsibilities

Project files and business skills own current requirements, rules, boundaries, and task state. Workflow skills own reusable methods. Hindsight supplies preferences, decision background, and verified experience. Current instructions and applicable formal rules take precedence over recalled material. Code and observations establish actual behavior. Resolve permission and accepted business meaning from their owners.

Use the configured Hindsight project integration for routine project recall and conversation retention, including business projects. Resolve project scope from the integration's bank routing and reuse the existing binding for another worktree of the same project. When automatic project memory is unavailable, use focused recall only when missing context could affect the task.

Use `personal-preferences` for lasting preferences and verified experience that apply across projects. Save a concise entry when confirmed or explicitly requested. Keep project-specific material in its project bank. With no identified project, limit memory calls to the personal bank.

Use the project's own files for formal rules and current state. Keep credentials out of memory. Treat historical transcript imports as a separate action. Apply explicit exclusions through the relevant capture settings and report any exclusion that cannot be enforced.

Before retaining the same source or topic, use a stable document identity or a focused lookup supported by the interface. When a response is uncertain, check its operation or document before retrying. Correct superseded content through a verified update or invalidation mechanism and check the effective result. Preserve true historical meaning. Report saved only after persistence completes. For an initial migration, verify extracted meaning and targeted recall as well. If writing fails, report it in the task receipt and retain the source.

Memory never grants authority or silently promotes an experience into a formal rule. Changes to formal meaning use the existing rule-maintenance process. After a branch merge, limit memory updates to the affected scope and status, and reuse identities. Record deployment separately from merge. Account for memory separately when rolling back Git. Native client memories are not a second manually maintained authority, and this instruction does not disable any product-level mechanism.

Apply a host tool convention only when the tool exists. Tool installation and security changes require their own authorization. Fixed ongoing tasks retain their adopted rules and acceptance baseline. Updated instructions govern new tasks or explicitly switched work.

For generated artifacts, read the project's adopted lifecycle entry and use its enrolled register, lease, and close workflow. For tasks without a project, use a personal runtime area only when its enrollment and actual entry are established. Otherwise, report that it is not enrolled and preserve the current arrangement. Legacy producers and fixed ongoing runs retain their adopted lifecycle. Preserve unregistered files and verify the presence of any scheduler before relying on it.
