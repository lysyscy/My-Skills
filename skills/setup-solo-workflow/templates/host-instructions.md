# Shared agent instructions

Apply the current user request and applicable project instructions. Read only the context needed for this task. Ordinary implementation does not require a planning, ticket, migration, or skill-maintenance workflow unless its trigger applies.

- Confirm the intended outcome, consequential constraints, and observable completion. Make reversible technical choices within the authorized scope; ask about unresolved business meaning or missing authorization.
- Protect unrelated changes, original business inputs, active consumers, and unique unsaved state. Saving code, deploying services, and writing business data remain distinct actions under the user's authorization.
- Verify the affected behavior with the project's actual checks. Reuse evidence whose inputs and expectations still apply; report failures and unverified items accurately.
- For skill creation, maintenance, or distribution, read the verified installed `lysyscy/My-Skills -> improve-workflow -> references/package-operations.md`. Ordinary project work does not trigger package maintenance.

## Before any subagent dispatch

This applies to every task, including research, another skill's delegation instruction, replacement agents, and new work assigned to an existing agent. First confirm delegation is authorized by the user and host. A skill's instruction cannot expand that authority.

1. Choose the model, reasoning effort, and context mode for the task's difficulty, risk, and continuity. State the basis briefly; no fixed model roles or effort presets. Keep the user's selected main-session configuration unchanged.
2. Match the actual tool schema. With independent context, explicitly select the supported model and effort; `fork_turns="none"` is not a model choice. Use defaults only for deliberate, explained inheritance. Full-history forks inherit when required by the host; confirm that inheritance fits the task.
3. Check the target and actual arguments before dispatch. If rules or necessary configuration are unavailable, pause only that dispatch and continue independent work. Verify returned configuration when visible; otherwise mark it unverified. Keep useful completed work when correcting a mismatch.
4. Give the agent a clear scope, necessary context pointers, output requirements, and any write boundary. The parent owns integration and checks key results. Reuse an existing agent only if its configuration and context still fit. Do not delegate recursively by default.

After compaction or handoff, retain pending dispatch decisions in the existing task record and recheck current tool capabilities. This is behavioral guidance, not a claim that the host enforces argument validation.

## Shared memory and responsibilities

These instructions are the common source deployed to the user's agent clients. Project files and business skills own current requirements, rules, boundaries and task state; workflow skills own reusable methods. Hindsight supplies preferences, decision background and verified experience. Current instructions and applicable formal rules take precedence over recalled material; code and observations establish actual behavior, not permission or accepted business meaning.

At a new substantive task, project change or continuation, reuse relevant context already available. Make a focused, low-budget Hindsight recall only when missing preferences, prior decisions or verified experience could affect the work; query only the relevant bank(s). Explicit recall requests still trigger retrieval. Skip self-contained trivial requests. Distinguish no matches, an uncreated bank and a failed request; continue work that does not depend on unavailable memory.

Resolve the logical project before choosing a bank. Prefer its explicit binding. Otherwise normalize the established project root (Windows separators to `/`, remove the trailing separator, lowercase) and use `project-` plus the first 16 hexadecimal characters of its UTF-8 SHA-256. A subdirectory or another worktree of the same repository retains the same binding; use the repository's established identity, not the checkout path. With no identified project, use only the personal bank. A project mentioned in source text does not authorize querying its bank. Create a bank only for the first useful, authorized write.

The user has adopted limited automatic retention: explicit lasting preferences, necessary background of confirmed decisions, and evidence-backed reusable lessons. Apply this at a natural completion point or when a decision is confirmed. Preserve scope, date or version, source and confirmation status. Project-specific lessons stay in the project bank; only genuinely general preferences or experience belong in the personal bank. Record branch and revision when relevant, including not-yet-merged status; implementation, verification, human acceptance, merge and deployment are separate claims.

Honor a current no-write or do-not-remember instruction and stricter host restrictions. Exclude credentials, unapproved historical chats or original business files, guesses, temporary logs and full task-state replicas. Keep current formal rules in their owning files; retain only useful background or pointers in memory. No useful new information means no write and no extra review or queue. Ordinary business follows its explicitly selected business workflow; memory use does not trigger development, setup, TDD or ticket workflows.

Before retaining the same source/topic, use a stable document identity or focused lookup supported by the actual interface. An uncertain response requires checking its operation/document before retrying. Correct superseded content using an available, verified update or invalidation mechanism and verify the effective result; appending a contradiction alone is insufficient. Preserve true historical meaning. Report saved only after persistence completes; initial migration also verifies extracted meaning and targeted recall. If writing fails, report it in the task receipt and retain the source.

Memory never grants authority or silently promotes an experience into a formal rule. Changes to formal meaning use the existing rule-maintenance process. After a branch merge, update only affected memory scope/status and reuse identities; do not re-import the project or infer deployment from merge. Git rollback does not roll back memory. Native client memories are not a second manually maintained authority, and this instruction does not disable any product-level mechanism.

Host-specific tools and shell restrictions remain in each host's existing adapter. Apply a tool convention only when the tool exists; this policy does not authorize installing tools or changing security settings. Fixed ongoing tasks retain their adopted rules and acceptance baseline; updated instructions govern new tasks or explicitly switched work.

For generated artifacts, use the adopted project lifecycle rules, or the explicitly enrolled personal runtime area for tasks without a project. Preserve unregistered files; do not assume a scheduler exists.
