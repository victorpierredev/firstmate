# Firstmate, Initiative, and Obsidian

## Review boundary

This is a proposed design checkpoint, not a description of installed integration behavior or approval to implement it.
It specifies how one human-readable initiative note can remain useful while Firstmate owns execution continuity.
Review this design before producing the implementation plan, then deliver the approved stages through Firstmate's existing guarded delivery path.
The checkpoint changes no runtime, global skill, vault content, or prototype code.

The proposal's principal review points are the single-writer boundary, the conservative landed-commit rule, and the conditional-writer requirement in [Safe Markdown publication](#safe-markdown-publication).
Approval of the design authorizes planning within these boundaries; it does not authorize deployment, a merge, or any change to existing initiatives.

## Outcome and scope

An initiative is a complete body of work, such as integrating Salesforce, composed of implementation tasks that together satisfy its completion criteria.
The initiative note explains the objective, scope, approved implementation design, important decisions, completion criteria, and current position.
Its task table has exactly four columns: `Task`, `Brief explanation`, `Status`, and `Commit`.
Firstmate maintains those task statuses automatically and publishes only the final verified landed commit for a completed task.
Detailed task specifications, dependencies, worker attempts, branches, validation, reviews, blockers, and recovery evidence belong in Firstmate's private execution records.
Individual tasks receive no Obsidian note by default.
A separate human note is appropriate only for substantial explanatory material, such as an investigation that changes the design, and the initiative links its conclusion.

The integration adds a narrow initiative binding and publication capability to Firstmate and makes Initiative the intent-oriented entry point.
It does not introduce another queue, scheduler, worker launcher, review pipeline, database, or background daemon.
It does not continue development of the `initiativeAI-cli` prototype as a user-facing CLI.
Unlinked Firstmate work retains its current behavior.
The integration leaves the contents and scripts of an existing legacy initiative folder untouched: it never writes, moves, or runs them.
It does change how such a folder is reached: once the integrated launcher replaces the installed phase-driven skill, `/initiative <phase>` no longer runs the legacy workflow, and this design installs no replacement entry point for it.

The following are future non-goals.
This design specifies none of them, and each needs its own reviewed checkpoint before any work begins.

- Migrating or adopting existing legacy initiative folders into the integrated model.
- Executing initiative tasks through secondmates or other homes, including binding handoff and remote evidence routing.
- Accepting or emulating the legacy phase-command syntax, keeping a separate creation command, or installing a second compatibility skill for legacy folders.

## Current behavior and sources

The inspected sources establish the following baseline.
Sources outside this repository are the author's local installation inputs and are described by role.
They are not runtime dependencies, and the design relies on none of their names or locations.

| Source | Current behavior | Consequence for this design |
| --- | --- | --- |
| Installed phase-driven Initiative skill | Resolves explicit phases and project/feature prefixes, reads a project prompt section, and shows the phase table when no phase is supplied | Replace phase selection with intent resolution |
| Installed initiative-creation skill | Reads a ticket, confirms a name, invokes the skeleton creator, and runs kickoff | Preserve ticket-first intake and meaningful confirmation while unifying entry under `/initiative` |
| Vault workflow notes | Describe a target integration with four task statuses, warn that automatic linkage may not exist, and describe a phase-driven workflow with per-feature supervisors, workers, reviews, commit logs, and boards | Treat them as desired behavior, not proof of an implementation, and hand execution ownership to Firstmate |
| Vault initiative skeleton template | Creates a dashboard, several narrative notes, feature notes, agent plans, task files, state boards, and prompt templates | New integrated initiatives need a smaller human template |
| Skeleton agent prompts, task templates, and feature templates | Keep execution state in the vault, count local committed work separately from merged work, and write verification logs | Do not import this execution loop into the new launcher |
| Vault creation, status, archive, and worktree-link scripts | Copy the old skeleton, read feature boards and forge state, archive after board checks, and link notes into worktrees | Do not run them for integrated initiatives |
| `initiativeAI-cli` prototype | A Go wrapper creates folders, prints phase prompts, delegates status/archive, and launches no agent | Mine resolver and validation logic and tests, not its CLI lifecycle |
| [Firstmate lifecycle](../AGENTS.md#7-task-lifecycle) and [backlog configuration](configuration.md#backlog-backend-taskstoml--configbacklog-backend) | Own task intake, guarded dispatch, delivery, merge authority, and backend-specific backlog addressing | Extend their existing seams rather than adding a competing executor |

The prototype's entry-point, creation, and prompt sources were inspected alongside its README, plan/review material, and relevant tests.
Its notes and tests are evidence of ideas to reuse, not proof that the intended integration already works.
No Initiative-specific linkage or Obsidian publisher was found in the inspected Firstmate runtime and skills.

### Existing lifecycle owners

| Concern | Current owner | Integration seam |
| --- | --- | --- |
| Durable work item and backend addressing | [fm-tasks-axi.sh](../bin/fm-tasks-axi.sh) and [fm-backlog-transition-lib.sh](../bin/fm-backlog-transition-lib.sh) | Bind an initiative row to an existing work-item identity without parsing or rewriting backend storage |
| Task start | [fm-spawn.sh](../bin/fm-spawn.sh) | Observe committed dispatch and its paired backlog transition |
| Current execution state | [fm-crew-state.sh](../bin/fm-crew-state.sh) and [fm-fleet-snapshot.sh](../bin/fm-fleet-snapshot.sh) | Reuse authoritative observations, including unknown results and generation checks |
| Held work and answers | [Captain hold lifecycle](captain-hold-lifecycle.md) | Observe durable holds and resolutions without creating another decision register |
| PR identity and merge observation | [fm-pr-check.sh](../bin/fm-pr-check.sh), [fm-pr-lib.sh](../bin/fm-pr-lib.sh), and [fm-merge-outcome-lib.sh](../bin/fm-merge-outcome-lib.sh) | Preserve their canonical identity and acquire an additional verified landing result |
| Local-only landing | [fm-merge-local.sh](../bin/fm-merge-local.sh) | Capture the exact approved fast-forward result |
| Cleanup and durable close | [fm-teardown.sh](../bin/fm-teardown.sh) | Retain initiative evidence before removing volatile task metadata |

Current status logs are wake-event history, not current-state truth.
Current PR registration records a PR head when available; that head is not the final landed commit after a squash or rebase.
The merge poll reports a merged observation, not a final commit hash.
Teardown's work-preservation test can accept remote-reachable work and must not be repurposed as proof that an initiative task reached its intended integration branch.
The default backlog retains only a bounded recent Done list, so initiative history cannot depend on a live metadata file or that recent list remaining present.

## Approach and ownership

Three approaches were considered.

| Approach | Benefit | Cost | Decision |
| --- | --- | --- | --- |
| Keep vault execution boards and synchronize both systems | Small initial change to the old workflow | Competing status and decision owners, ambiguous recovery, operational noise in the vault | Reject |
| Use Firstmate records with one initiative note and a narrow publisher | Reuses guarded execution and keeps the human story self-contained | Requires explicit bindings, landing evidence, and a proven conditional writer | Recommend |
| Build on the prototype as the orchestration service | Reuses a CLI surface | Adds a second execution authority and contradicts the requested retirement direction | Reject |

Ownership is divided by meaning, not by which agent last touched a file.

| Surface | Authority |
| --- | --- |
| Initiative objective, scope, design, and completion criteria | Human intent and its explicitly accepted revisions in the initiative note |
| Durable decision and approval evidence | Existing Firstmate work-item/hold mechanisms; the note carries the concise human conclusion |
| Execution specifications and continuity | Firstmate's existing backlog, briefs, reports, validation records, and lifecycle owners |
| Task status and final landed commit | Verified Firstmate lifecycle facts, rendered into the note |
| Task names and explanations | Human-facing wording in the note, initially supplied from the accepted task breakdown |
| Initiative identity, row bindings, publication recovery | One new Firstmate initiative record owner |
| Entry-point routing | Initiative skill, delegating execution to Firstmate |

The home that registers an initiative is its single publisher and the owner of every bound work item.
A bound work item stays in that home; handing it to another home is unsupported.
A worker receives an ordinary Firstmate brief containing the accepted task specification and design revision, not permission to update the vault.
The integration confers no new project-write, push, merge, discard, or external-message authority.
Firstmate's [delivery and merge contract](../AGENTS.md#selected-delivery-path-and-merge-authority) remains the authority for those actions.

## Initiative note schema

For a new integrated initiative, the human entry point is `<work-root>/<initiative-name>/<initiative-name>.md`.
The work root is configured and validated; it is not inferred from the agent's current checkout or hardcoded to one workspace.
The note is ordinary Markdown and readable without Dataview, an execution-board plugin, or access to private Firstmate files.
Preserve the vault's existing frontmatter properties without adding execution identifiers to visible properties.
An initiative-level status property follows the vault's own lifecycle vocabulary and is independent of task status.

| Section | Required human content |
| --- | --- |
| Objective | The outcome, who benefits, and why it matters |
| Scope | Included work, non-goals, affected systems, and constraints |
| Current behavior | The starting behavior and limitations that the design changes |
| Implementation design | The approved end-to-end flow, major components, interfaces/data changes, rollout, and failure handling |
| Important decisions | Concise choice, reason, authority/date, and source where useful; proposals are explicitly pending |
| Completion criteria | Observable outcomes and any rollout or verification requirement beyond merging code |
| Current position | A short account of what is available, what remains, and the next meaningful action |
| Tasks | The four-column implementation table |
| Sources | Ticket and selected human-relevant references |

Before design approval, the design section says `Proposed` and names the decision needed to proceed.
After approval, it identifies the accepted revision in plain words and date; private execution records bind that revision to exact content.
There is no requirement to create a supporting narrative, feature, or task note solely to fill a template.
Large designs may link a substantial supporting human document while retaining enough explanation in the initiative note to understand the solution.

The following rendered example is illustrative; its commit value is not a real delivery claim.

| Task | Brief explanation | Status | Commit |
| --- | --- | --- | --- |
| OAuth connection | Connect a Salesforce account securely | Done | `a13fd72b904e` |
| Account synchronization | Import accounts and apply later changes | In progress | - |
| Retry handling | Recover from temporary API failures | Planned | - |

The status vocabulary is exactly `Planned`, `In progress`, `Blocked`, and `Done`.
Task names are meaningful action names, and explanations are normally one short sentence or phrase.
There are no visible ID, PR, worker, branch, timestamp, dependency, or retry columns.
A commit cell is `-` until the completion rule in [Landed commits](#landed-commits) is satisfied.
For a verified result, show an unambiguous abbreviated hash of at least twelve hexadecimal characters and link it to the canonical repository commit when available.
Retain the full object ID privately and lengthen the displayed abbreviation if it is ambiguous.
For local-only work, show the verified abbreviation without inventing a remote link.

## Identity and Firstmate linkage

Use one immutable random initiative UUID and one immutable random UUID per task row.
IDs do not encode titles, order, feature names, branch names, or worktree locations.
An HTML comment binds the document, and a comment inside the Task cell binds each row without adding visible columns.

```markdown
<!-- firstmate:initiative v=1 id=4d18e357-a8f6-4f24-a655-355361a16c75 -->

## Tasks

<!-- firstmate:tasks v=1 -->
| Task | Brief explanation | Status | Commit |
| --- | --- | --- | --- |
| <!-- firstmate:task id=f4c3eb6d-bdd5-4d10-8c7f-9cc68fb5e2a6 --> OAuth connection | Connect an account securely | Planned | - |
<!-- /firstmate:tasks -->
```

The parser recognizes these exact standalone region markers and row-comment forms outside fenced examples only.
Exactly three marker conditions are conflicts that block publication: a malformed, nested, or unknown-version marker or region; a duplicated ID; and a registered initiative or row ID that no longer appears in the note, whether its row was deleted or only its marker was removed.
None is resolved by guessing from the task title or row position.
An unmarked row is never a conflict.
It is a proposed task for intake, publication of the bound rows proceeds around it, and it receives an ID only through an accepted task addition.
Renaming or reordering a marked row preserves its identity and does not respawn work.
A copied note containing an existing initiative ID is a duplicate, not another registered initiative.
Deleting a row is not cancellation authority; retain its binding and ask for scope reconciliation before removing it from the projection.

Keep durable linkage under the configured Firstmate data root, provisionally `data/initiatives/<initiative-id>/record.json`.
The future initiative helper's header and help will own its exact versioned wire format.
Required semantic fields are:

- Schema version, initiative ID, title, selected vault/work roots, and registered relative note path.
- Source ticket identity and approved design revision, content digest, approval provenance, and immutable accepted text snapshot.
- For each row ID: durable backlog task ID, repository identity, intended integration branch, and task scope revision.
- For an active attempt: task metadata generation and its execution binding, so an old worker or reused task name cannot update a replacement.
- For each accepted landing: full commit ID, exact repository and target branch, canonical PR/MR identity or local merge receipt, covered task scope revision, and evidence provenance.
- Last acknowledged publication revision and baseline of managed content, plus outstanding reconciliation or publication work.

Each implementation row normally binds one work item in the publishing home's backlog through all its worker attempts.
A replacement attempt changes the attempt binding, not the human row identity.
One task that requires separate deliverables in different repositories or separate incomplete landings is split into independently meaningful rows before execution.
Several rows may intentionally share a PR only when an explicit coverage mapping identifies the accepted work of every row; a merged PR alone cannot complete an arbitrary associated row.
Planning and investigation work items remain private unless they produce substantial human context worth linking from the initiative.

The binding record does not copy the backlog's dependency graph, hold state, task body, or current run state as independent truth.
Its observed status is a disposable projection of those sources; its durable landing receipt and row identity survive ordinary task teardown and backlog retention.
Accepted design snapshots are immutable briefing evidence, not a second editable design document.
Raw user intent remains separately attributable when Firstmate constructs a no-mistakes brief.

## Entry point and user flows

`/initiative <ticket-link>` is the preferred creation path.
Resolve the source with the appropriate authenticated connector, reuse the user's authorized repository context, and present a concise proposed name and scope if either remains unspecified.
An explicit name or already accepted scope need not be confirmed again.
Ticket content is source material; a ticket that is a PR requires inspection of existing work and is not evidence that the initiative is complete.
Lookup failure leaves a resumable draft or asks for the missing source content, never an invented specification.
An existing binding for the same source offers continuation instead of creating a duplicate.

| Request | Intended action |
| --- | --- |
| Bare `/initiative` | Resolve the active initiative from the conversation; otherwise use one unambiguous registered initiative or ask a short selection question |
| `/initiative <ticket-link>` | Create or resume intake, then move to the next missing design checkpoint |
| “Start an initiative for Salesforce” | Use the same intake, resolving scope and repository before task dispatch |
| “Continue Salesforce” or `continue` in that context | Reconcile current facts, then carry out the next authorized useful step |
| “Start the OAuth connection task” | Resolve the marked row and check its accepted specification, blockers, and existing worker before dispatch |
| “Where are we with Salesforce?” | Reconcile and answer from current facts, publishing changes without starting new implementation |
| “Stop after this task” | Use Firstmate's existing worker controls and preserve continuity; stopping is not completion or landing |
| “Close the initiative” | Check completion criteria and outstanding calls, publish the outcome, and obtain any still-required archive authority |

Continuation uses a deterministic order of checkpoints: identity and ownership, pending source/design changes, unresolved decisions, missing approved design, missing accepted task breakdown, active work, ready tasks, then initiative completion.
It advances through already-authorized checkpoints without asking the user to remember the phase order.
It attaches to or supervises an existing attempt rather than launching a duplicate.
If all remaining work is blocked, explain the material blocker and next decision in plain words.
If the design is inadequate, arrange the bounded investigation or clarification needed before briefing implementation.

The launcher resolves intent, not a phase argument, and defines no phase vocabulary.
An initiative folder without a Firstmate binding is not managed by this launcher: leave its contents untouched and say plainly that the launcher neither runs nor migrates it.
That answer depends only on the target being an unbound legacy folder, never on the words of the request.
Former phase words carry no compatibility meaning: aimed at a bound initiative they are ordinary language for intent resolution, and otherwise they receive the same clarification as any other unresolved request.
Unknown arguments produce a short contextual clarification, not a mandatory phase tutorial.

The tracked Initiative entry-point source must have one owner when implemented, with installation into global skill directories treated as deployment.
Before changing that source, identify its actual installation owner so a later synchronization cannot restore the old launcher over the new one.
Firstmate-specific operating detail belongs in a conditional internal skill and helper headers, with only the necessary trigger pointer added to the supervisor contract in a later implementation change.

### Private operating guide

Maintain an installation-specific human operating guide in the private vault as a deployment artifact, separate from individual initiative notes.
It names the exact canonical Firstmate home directory from which to start a session and explains the installed workflow for creating, specifying, running, resuming, and checking an initiative.
The guide directs users to work through Firstmate from that home; project repositories and isolated worker worktrees are resolved by Firstmate rather than becoming the user's supervisor working directory.
Its directory and startup instructions must agree with the installation's actual home configuration and supported harness setup, whose shared contract remains in [configuration](configuration.md).
Distinguish currently installed behavior from the proposed integration so a target workflow is never presented as available before deployment.
The deployment owner maintains this guide whenever the working-directory setup or installed entry-point behavior changes and verifies it with a fresh-session walkthrough.
Keep actual local paths and installation-specific commands in that private guide, never in the upstream specification or an initiative's task table.

## Lifecycle projection

Derive the table from the bound work item, current attempt, unresolved blockers/holds, and accepted landing evidence.
Do not parse free-form outcome prose or treat the latest status-log line as the state machine.

| Verified condition | Visible status | Commit |
| --- | --- | --- |
| Accepted task exists and has not started; no active blocker | Planned | - |
| Dispatch has committed, or implementation, validation, review, fixes, or ordinary merge waiting remain active | In progress | - |
| A dependency, required decision, explicit pause, or verified failure prevents forward progress | Blocked | - |
| The task's accepted scope has passed its selected delivery path and has verified final landing evidence | Done | Final landed hash |

A green PR awaiting ordinary merge approval remains `In progress`; an explicit hold or unresolved decision that prevents its merge is `Blocked`.
A cleared blocker returns an unstarted task to `Planned` and a started task to `In progress`.
A known worker failure becomes `Blocked` with a concise human reason only when it prevents progress; normal automated retries remain `In progress`.
Unknown or temporarily unavailable evidence retains the last verified status and records publication freshness separately, without inventing a fifth status or implying that work itself is blocked.

An approved scope removal retires the row from the current table and retains a private tombstone and a concise scope decision.
It is never mislabeled `Done` to avoid adding a fifth status.
A follow-up requirement normally receives a new row instead of rewriting a completed row's historical purpose.
Reopening an actually incomplete or reverted task retains its identity, explicitly changes the accepted scope/state, and removes the obsolete displayed commit until its final replacement lands.
Prior landing evidence stays in private history.
An unrelated initiative decision does not reopen a correctly completed task, and a task completing does not close an unrelated held decision.

### Automatic update points

Record projection work after accepted planning, committed spawn, authoritative blocked/resumed observations, hold/answer changes, PR registration, verified landing, scope changes, and teardown recovery.
Use the existing supervision/reconciliation loop to publish pending changes, including an automatic backstop for missed observations.
Successful publication should occur by the next successful supervision reconciliation cycle, with no manual command required.
Publication is idempotent, coalesces intermediate operational transitions, and writes nothing when rendered content is unchanged.
A plain repair request for one initiative runs the same reconciler.

Current bounded fleet snapshots are navigation aids, not proof that omitted rows are absent.
Reconcile every linked item by exact identity, using authoritative owner reads where the snapshot is incomplete.
Manual-backend or otherwise unstructured homes cannot promise automatic tracking: refuse automatic binding with an actionable explanation until supported authoritative reads exist, without altering their unlinked work.

## Landed commits

The displayed commit identifies the change as integrated into the task's declared target branch, not the worker's first implementation commit, validation-fix commit, PR head, current default-branch tip, or teardown date.
`done:`, no-mistakes success, green CI, a push, merge queue entry, and a merged stacked PR targeting an intermediate branch are insufficient on their own.

For a forge-backed task, verify the exact canonical PR/MR identity and repository, its merged state, its accepted task coverage, its integration target, and the resulting commit object on that target's history.
For a squash, use the resulting squash commit.
For a merge commit, use the resulting merge commit.
For a rebase or fast-forward merge, use the final integrated commit attributable to that delivery, proving the mapping rather than assuming the old head survived.
Provider-specific field interpretation must be verified by focused fixtures and a live supported-provider check before enabling that merge strategy.
Where the provider cannot prove the final object, retain a reconciliation obligation and withhold the hash and `Done` claim.
Do not relax Firstmate's existing forge identity validation or merge authorization to acquire this evidence.

For an approved local-only merge, extend its existing owner to persist the full post-fast-forward commit ID while the target update is still serialized.
Its receipt binds the task, repository, target, before/after object IDs, and accepted scope revision.
Reading the branch tip in a later agent turn is insufficient because unrelated work may have advanced it.
The receipt stays valid after a later ordinary target advance; a detected history rewrite that invalidates the evidence requires reconciliation.

The verified merge outcome path and external-merge poll feed the same landing recorder.
Keep forge enrichment out of the watcher's cheap polling path and out of the blocking session-start digest.
If a merge is already durable but evidence publication fails, report both facts distinctly and retry evidence capture without attempting the merge again.
Capture either the verified landing receipt or an identity-complete unresolved landing obligation before teardown removes its only source metadata.
Teardown may proceed after that durable obligation exists and its own guards pass; vault unavailability must not strand safely landed worktrees.
Failure to persist even the obligation refuses cleanup before destructive removal.

## Safe Markdown publication

Use one narrow deterministic publisher for binding, reconciliation, and note patches.
The agent may propose prose, but it does not rewrite the entire Markdown document on every event.
The publisher owns only the task table's Status and Commit cells during routine lifecycle publication.
It preserves Task and Brief explanation wording, row order, unrelated tables, headings, comments, frontmatter, links, line endings, and every byte outside the selected edit spans.
Accepted additions, removals, and narrative changes are separate explicit patch operations using the same safeguards.
Support the template's controlled Markdown table grammar, including escaped pipes and inline code, and refuse ambiguous input rather than running a broad regular-expression replacement.

### Transaction and conflict contract

1. Resolve the registered initiative identity and path, validate ownership, and acquire the existing home/actor authority plus a per-initiative publication lock.
2. Read the latest content and file identity, validate all markers and bindings, and compare managed fields with the last acknowledged baseline.
3. Compute a patch from current authoritative facts against this latest content, retaining all non-conflicting manual edits.
4. If the note has one of the marker conflicts defined in [Identity and Firstmate linkage](#identity-and-firstmate-linkage), or a human changed a machine-owned cell to a different value or altered a proposed narrative span, preserve the current document and record a conflict.
5. Persist a private pending transaction containing the expected content revision, intended patch, candidate digest, and source observation revision before attempting publication.
6. Apply a conditional content update through a writer that can enforce the expected revision at its serialization point.
7. Read back and validate the result, acknowledge the publication revision, then retire the pending transaction.

Concurrent Firstmate writers serialize through the same lock, and stale observations cannot overwrite a newer acknowledged source revision.
Independent human changes outside edited spans are rebased onto the latest content rather than rejected solely because the whole file hash changed.
A human edit already equal to the intended value can be accepted as converged, but it never establishes execution or landing evidence.
Keep original/candidate/conflicting snapshots in private recovery storage, not beside the human note as agent reports.
After a crash, matching candidate bytes finish acknowledgement; matching baseline bytes retry; any other content is re-read and reconciled instead of overwritten.
Bound routine recovery retention while retaining every unresolved conflict until it is handled.

### The conditional writer is a required boundary

An advisory lock plus a hash check followed by an unconditional rename is not an atomic compare-and-swap against Obsidian or a sync client.
It also cannot protect a human's unsaved editor buffer.
Do not claim that pattern guarantees preservation of concurrent manual edits.

Automatic status publication is required behavior, so the conditional writer in step 6 is a precondition of the implementation, not an optional enhancement.
This checkpoint has not verified a writer with that guarantee.
The first implementation stage must prove the smallest writer that serializes an update with the note's current content, including the active editor's buffer, and rejects a stale expected revision.
The proof runs against the actual editor and covers simultaneous edit and save, an unsaved buffer, and competing filesystem and sync writers, which the writer must coordinate or exclude.
It does not infer exclusivity from a quiet mtime or an absent open-file handle alone.
Prefer an already available supported editor integration that proves this contract.
Add a new local component only if none does, and then limit its authority to applying a validated patch to the registered note and returning the resulting content revision, with no queue, task, shell-command, or merge authority.
Concurrent editing from another device is unsupported unless that writer participates in the same conflict-safe update contract.

Stage 1 selects exactly one proven writer.
If no writer can be proven, implementation stops and the design returns to review.
There is no accepted outcome in which the integration ships with automatic publication disabled, and no fallback to filesystem last-writer-wins behavior.

A temporary failure of the proven writer, such as an offline vault, is different from that outcome.
Retain the pending publication, report the stale human view through Firstmate, and publish on the next successful cycle; never perform a blind overwrite.

## Human narrative policy

Update the human narrative when scope or direction changes, a durable decision is accepted, an investigation changes the solution, a material blocker appears or clears, meaningful work lands, or completion/archival changes the initiative's position.
Task starts and ordinary lifecycle changes update table cells without adding progress-log entries.
Rewrite Current position as a compact present-tense summary, normally one paragraph and at most three next/blocker bullets.
Do not append a dated line for every task event.
Important decisions state the choice and reason, with approval provenance or an explicit pending label.
Do not paste task briefs, agent messages, terminal output, commands, CI retries, review rounds, endpoint IDs, or transient failures into the note.

Detect manual changes to design, scope, criteria, and material task meaning by comparing the approved content snapshot, not only file modification time.
Read those edits as proposed input, summarize their effect, and record the user's actual approval before treating a changed design as accepted.
An explicit authenticated instruction accepting that change supplies the approval; do not ask for the same approval again.
Preserve the user's words and pause only affected dispatch or landing when their consistency with the approved design is uncertain.
Unrelated work may continue under its existing authorization.
Cosmetic renames or wording edits do not require repeating design approval, but they never silently broaden an execution brief.
Accepted narrative patches use the same revision and conflict protections as lifecycle publication.

The initiative is complete only when its in-scope implementation rows have landed, its human completion criteria are satisfied, and remaining calls or follow-ups have an explicit disposition.
All rows being `Done` is necessary for ordinary implementation completion but does not prove rollout, adoption, or other non-code criteria.
Archive only through an explicitly authorized, collision-safe operation that updates the registered note path without changing its initiative ID.

## Failure and reconciliation

| Failure or race | Required result |
| --- | --- |
| Vault offline, permission failure, or temporarily unavailable writer | Keep execution facts and pending publication durable, report the stale view without changing task truth, and publish on recovery |
| Editor conflict or damaged markers | Leave the note untouched and expose one deduplicated reconciliation issue through Firstmate |
| Out-of-order or duplicate lifecycle observation | Re-read authoritative state and converge; never regress a verified landing from an old worker event |
| Forge timeout or missing final hash | Preserve the verified facts and an unresolved landing obligation; never substitute the PR head |
| Restart between note update and acknowledgement | Recognize the candidate content and complete the receipt without a duplicate edit |
| Teardown or Done-history pruning | Reconstruct from retained initiative linkage/evidence rather than missing volatile metadata |
| Renamed note | Accept a single identity-preserving move inside allowed roots after validation; conflicting copies require reconciliation |
| Missing note | Retain binding and pending work; do not recreate over an intentional human deletion |
| Invalidated landing or revert | Preserve evidence, reconcile actual scope, and explicitly reopen the task or add follow-up work |

Use existing wake and held-work mechanisms for issues that require a decision, with actionable human wording and private technical detail.
Normal retryable publication failures do not create repeated decision rows or notification floods.
Do not wait synchronously on the vault or forge while holding spawn, merge, teardown, or backlog locks.
Lifecycle owners persist a bounded local publication obligation and release their locks; the reconciler performs slow work afterwards.
At startup, register pending work for the existing deferred/reconciliation path without adding network calls to the blocking digest.

## Prototype retirement

| Prototype element | Disposition |
| --- | --- |
| Exact-match-first, case-insensitive unique-prefix resolution | Reuse the behavior and ambiguity tests in the entry-point resolver |
| Name validation, source URL validation, argument arrays, and root containment | Reuse the validation concepts while strengthening write-time identity checks |
| Ticket hydration and distinction between source PR and finished delivery | Preserve in intake |
| Temporary-vault fixtures, traversal/symlink tests, collision and partial-creation tests | Port relevant scenarios to Firstmate's test conventions |
| Fence-aware prompt sections, missing-section fallback, inline task lookup | Do not port; they serve only legacy inputs |
| CLI parser, command surface, prompt-printing handoff, launcher milestone | Retire from the integrated path |
| Board status/archive wrappers and old execute/dispatch instructions | Not used by integrated initiatives, which read Firstmate lifecycle facts |
| Skeleton copier for new initiatives | Do not call; integrated creation uses the accepted compact schema |

Do not add a Go binary dependency solely to reuse these ideas.
Keep the prototype read-only during this checkpoint and leave any repository archival or deletion to a separate explicit request.
Later skill and vault changes must update their actual tracked source/install owner through normal delivery, rather than patching an installed global copy ad hoc.

## Security and path boundaries

Configure one publisher and explicit vault, active-work, and archive roots in private home configuration.
Opt-in authorization names the initiative note and permitted publication operations; it is not general write authority over the vault.
An initiative note stores no absolute home path, credentials, terminal endpoint, or private task-report link.
Bind identity to the registered path and allowed roots; content markers alone do not authorize a write.
Reject traversal, control characters, malformed identities, escaping symlinks, special files, unsafe hardlinks, and path/file identity changes during publication.
Resolve any symlinked alias of the note once as an input locator, then address the authorized canonical vault path directly.
Do not create worktree links or edit project memory as a side effect of status publication.
Read external tickets, Markdown, and comments as data rather than shell code or authority to widen the task.
Use structured connector calls and argument arrays, validate canonical forge identities with the existing owner, and never interpolate note text into shell programs.
Remote data cannot select a publisher path or execution home.
Writer requests require local authenticated access bound to the publisher, the initiative identity, an expected revision, and allowed patch types.
Failure of authority, path validation, or owner identity refuses mutation without falling back to another home or vault.

## Observable acceptance criteria

1. Starting with `/initiative <ticket-link>` reaches a reviewable initiative design and tasks without requiring the user to name a phase, while missing authority still produces a concrete decision.
2. Bare `/initiative` and contextual `continue` resume one unambiguous initiative and do not duplicate an existing work item or worker.
3. A new note contains every required human section and exactly four task columns, with hidden stable identities and no routine agent activity.
4. Planning, committed dispatch, a real blocker, blocker resolution, and verified landing automatically produce the specified table changes by the next successful reconciliation/publication cycle.
5. A worker commit, green PR, queued merge, or merge to a staging branch never produces `Done` or a premature commit cell.
6. Squash, merge, supported rebase/fast-forward, external forge merge, and local-only landing publish the correct final object ID; inability to prove one remains visible to Firstmate as unresolved work.
7. Renaming or reordering tasks preserves bindings; a malformed or duplicated marker, or a bound ID missing from the note, prevents publication instead of updating the wrong row; a new unmarked row does not delay publication for bound rows.
8. Manual narrative and wording edits survive status publication byte-for-byte; competing edits to managed cells produce a recoverable conflict.
9. The selected writer proves simultaneous edit/save and unsaved-buffer preservation with competing writers coordinated or excluded, and no later stage begins without that proof.
10. Crashes around registration, dispatch, merge evidence, file publication, and teardown reconcile without lost bindings, false completion, or duplicate rows.
11. Evidence and completed task rows survive metadata removal, recent-Done pruning, and note moves.
12. Unlinked Firstmate work behaves as before, and the contents and scripts of legacy initiative folders remain byte-for-byte untouched; a request aimed at an unbound legacy folder produces the unsupported-entry explanation, not legacy execution or migration, and former phase words change no outcome.
13. Path escape, forged row identity, wrong-home data, and untrusted source instructions cannot cause a write outside the registered note or authorize execution.
14. Initiative completion checks the stated human outcomes as well as landed tasks, and archive preserves stable identity and existing destination files.
15. The installation's private operating guide names the exact working directory and accurately explains the deployed workflow; a user following it can start a fresh Firstmate session and create or resume an initiative without guessing the directory or phase order.

## Test strategy and delivery stages

This checkpoint is documentation-only.
Classify this specification as maintainer architecture in the documentation inventory, run `bin/fm-doc-audience-check.sh`, review local link targets and the complete branch diff, and run `git diff --check` before committing.
Keep checkpoint command output and review history in task/PR evidence, not in the human initiative note or this design.

Implementation tests use temporary Firstmate homes, temporary vaults, real temporary Git repositories, and stubbed forge responses by default.
Port prototype behaviors rather than its test runner, and use the existing Firstmate behavior-test runner and focused lifecycle suites.
Exercise public helper behavior rather than asserting implementation source text.
Cover Markdown escapes, fences, Unicode, line endings, preserved frontmatter, task renames/reordering, unmarked proposal rows, manual cell edits, duplicate IDs, interrupted transactions, and symlink replacement races.
Use coordinated concurrent writers and injected failures at persistence boundaries rather than timing-only tests.
Test every lifecycle mapping, grouped PR coverage, deleted source branches, rewritten heads, stale observations, wrong targets, unavailable providers, and missing commit objects.
Extend existing spawn/backlog atomicity, PR merge/poll, captain-hold, and teardown tests where their contracts gain a publication obligation.
Verify supported backlog adapters separately and make unsupported manual tracking explicit.
No runtime harness/backend receives a new parser or launch path; verify the shared integration seam across affected adapters, with live checks where a verdict depends on vendor behavior.
Use a disposable Obsidian vault for the required live writer verification and a controlled forge fixture for provider semantics, never the real initiative vault as a test fixture.

The following stages are inputs to a later writing-plans pass, not implementation instructions authorized by this checkpoint.

| Stage | Scope and principal owners | Exit evidence |
| --- | --- | --- |
| 1. Prove publication and landing boundaries | Prove the smallest safe conditional writer against the live editor, and verify supported provider commit semantics, the actual skill installation owner, and existing backlog read interfaces | A reviewed capability result with concrete supported limits and exactly one proven writer; without that proof, implementation is blocked and the design returns to review |
| 2. Bind and publish a temporary initiative | Add the minimal private record/helper, note template, hidden IDs, the proven writer, conflict/recovery path, and documentation owners | Temporary-vault tests and the real-editor concurrent-save guard pass |
| 3. Connect authoritative lifecycle facts | Integrate planning, spawn/current-state/hold observations, merge evidence, and teardown retention with existing owners | End-to-end planned-to-landed projection, crash recovery, and premature-completion refusal across selected delivery modes |
| 4. Add conversational intake and resume | Update the tracked Initiative router and internal Firstmate skill, accepted-design briefing, and automatic next-step resolution | Ticket intake and fresh-session continuation work without phase knowledge or competing supervisors; a request aimed at an unbound legacy folder yields the unsupported-entry explanation with the folder unchanged, whatever words it uses |
| 5. Pilot | Run one approved new initiative, deploy the reviewed skill, template, and writer changes, and update the private operating guide with the exact working directory and installed workflow | A real initiative remains concise through a guarded task landing and a session restart, with its statuses and landed commit published automatically; a fresh-session walkthrough confirms the private guide matches the deployed installation |

Each stage has its own bounded task brief and validation evidence through the configured Firstmate delivery process.
A stage begins only after the stages it depends on have passed.
Only after the reviewed checkpoint and implementation plan are accepted should runtime, installed skill, or vault template work begin.
