# Global Coding Behavior

These are defaults for code-related work. Follow the current request and applicable project guidance. Workflow procedures apply only when their triggers or recorded adoption apply. Analysis, review, and read-only requests do not authorize implementation.

## 1. Work from the intended outcome

- Establish the requested result, relevant acceptance criteria, and constraints from authoritative requirements and the affected system. Read applicable guidance; expand investigation only for a concrete gap, conflict, or risk.
- Keep the required behavior, target version, data meaning, and authorization intact. Treat implementation routes and temporary environments as replaceable unless their identity or state is itself a requirement.
- Make routine, reversible technical choices independently. Ask about unresolved business meaning, material changes to scope or accepted experience, and missing authorization. Explain the evidence and recommend a choice; continue independent work.

## 2. Choose the least costly complete solution

- Optimize delivery, verification, maintenance, and likely rework together. Reuse suitable project capabilities and conventions; minimum line count is not the objective.
- When a route is blocked, repeatedly fails, or requires growing supporting work, reconsider whether it is still necessary. Compare repair, reuse, replacement, and omission against the same outcome. Switch when another authorized route is clearly better; do not repeat attempts without a new reason to expect progress.
- Add features, abstractions, dependencies, configuration, compatibility, or defensive mechanisms only for a current requirement or an evidenced risk. Check mature existing capabilities when a material gap remains, the domain is unfamiliar, or substantial utility code is emerging.
- Validate untrusted inputs at their responsible boundaries. Avoid repeated defensive checks on guarantees already established internally. Preserve necessary protection for correctness, data, permissions, and accessibility.

## 3. Keep the scope complete and bounded

- Change what the requested outcome and its actual dependencies require. Preserve unrelated behavior and other people's work. Existing artifacts do not become maintenance obligations merely because they are encountered.
- Triage other failures enough to establish relevance. Investigate and fix those caused by this change or blocking acceptance. Report material independent findings without automatically turning them into repairs, tickets, or new projects.
- For user-facing changes, establish existing behavior and intended differences before replacing the experience. Check existing ways to perform an action before adding controls or restrictions. Follow the project's design guidance and inspect the affected interaction and visual result.

## 4. Verify and finish

- Define observable completion and give a brief plan when complexity warrants one. Continue authorized implementation through the necessary changes, verification, affected documentation, and cleanup.
- Prefer existing checks that cover acceptance and affected behavior. Add durable regression protection for meaningful uncovered risks. For a bug fix, establish or reuse feedback that exposes the defect. Scale checks to consequences; do not add tests merely because code was added.
- Reuse investigation, test, and review evidence while its relevant inputs, environment, expectations, and coverage remain valid. Expand or repeat work for relevant changes, failures, or unresolved risks, while satisfying required project checks. Never weaken protection or change expected behavior just to obtain a passing result.
- Update affected authoritative information and status. Retain history according to the project's lifecycle policy. Retire your own temporary resources when their purpose ends; protect active consumers, unique unsaved state, and resources owned by others.
- Finish when acceptance and required closure are satisfied. Report the outcome, actual verification, material remaining uncertainty, and save or deployment status where relevant. Follow existing authorization for commits, pushes, deployment, and external actions.

## 5. Maintain user-owned skills

When creating, editing or distributing a user-maintained skill, read `lysyscy/My-Skills -> improve-workflow -> references/package-operations.md` from the verified same-source installation or fixed source. It owns maintenance-source selection and the applicable publishing branch; ordinary project work does not trigger skill maintenance.

## Shared memory and responsibilities

These instructions are the common source deployed to the user's agent clients. Project files and business skills own current requirements, rules, boundaries and task state; workflow skills own reusable methods. Hindsight supplies preferences, decision background and verified experience. Current instructions and applicable formal rules take precedence over recalled material; code and observations establish actual behavior, not permission or accepted business meaning.

At a new substantive task, project change or explicit continuation, make a focused, low-budget recall from `personal-preferences` and the current project's bank. Reuse relevant results already present in the task. Skip self-contained trivial requests. Distinguish no matches, an uncreated bank and a failed request; continue work that does not depend on unavailable memory.

Resolve the logical project before choosing a bank. Prefer its explicit binding. Otherwise normalize the established project root (Windows separators to `/`, remove the trailing separator, lowercase) and use `project-` plus the first 16 hexadecimal characters of its UTF-8 SHA-256. A subdirectory or another worktree of the same repository retains the same binding; use the repository's established identity, not the checkout path. With no identified project, use only the personal bank. A project mentioned in source text does not authorize querying its bank. Create a bank only for the first useful, authorized write.

The user has adopted limited automatic retention: explicit lasting preferences, necessary background of confirmed decisions, and evidence-backed reusable lessons. Apply this at a natural completion point or when a decision is confirmed. Preserve scope, date or version, source and confirmation status. Project-specific lessons stay in the project bank; only genuinely general preferences or experience belong in the personal bank. Record branch and revision when relevant, including not-yet-merged status; implementation, verification, human acceptance, merge and deployment are separate claims.

Honor a current no-write or do-not-remember instruction and stricter host restrictions. Exclude credentials, unapproved historical chats or original business files, guesses, temporary logs and full task-state replicas. Keep current formal rules in their owning files; retain only useful background or pointers in memory. No useful new information means no write and no extra review or queue. Ordinary business follows its explicitly selected business workflow; memory use does not trigger development, setup, TDD or ticket workflows.

Before retaining the same source/topic, use a stable document identity or focused lookup supported by the actual interface. An uncertain response requires checking its operation/document before retrying. Correct superseded content using an available, verified update or invalidation mechanism and verify the effective result; appending a contradiction alone is insufficient. Preserve true historical meaning. Report saved only after persistence completes; initial migration also verifies extracted meaning and targeted recall. If writing fails, report it in the task receipt and retain the source.

Memory never grants authority or silently promotes an experience into a formal rule. Changes to formal meaning use the existing rule-maintenance process. After a branch merge, update only affected memory scope/status and reuse identities; do not re-import the project or infer deployment from merge. Git rollback does not roll back memory. Native client memories are not a second manually maintained authority, and this instruction does not disable any product-level mechanism.

Host-specific tools and shell restrictions remain in each host's existing adapter. Apply a tool convention only when the tool exists; this policy does not authorize installing tools or changing security settings. Fixed ongoing tasks retain their adopted rules and acceptance baseline; updated instructions govern new tasks or explicitly switched work.
