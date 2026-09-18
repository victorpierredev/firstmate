---
name: initiative
description: >-
  Start, continue, check, or close an Obsidian initiative from its publishing Firstmate home.
  Use for /initiative or a request about a named bound initiative, including ticket-first intake and continuation in that context.
  The standalone phase workflow belongs to /initiative-legacy.
user-invocable: true
metadata:
  internal: true
---

# Initiative

Firstmate coordinates execution; the initiative explains the goal, accepted plan, progress, and history in Obsidian.
Run this procedure only in the registering home's supervisor session.
Use [the existing helper](../../../bin/fm-initiative.sh) with explicit `FM_HOME`; its header and `--help` own commands, request fields, and record formats.
Use [the integration blueprint](../../../docs/initiative-obsidian-integration.md) for the ownership boundary and supported limits.
The helper alone publishes generated companions; never write, move, or replace a human note, insert an embed, or run a vault execution script.
Record actual accepted authority for mutations, including existing authorization; do not invent approval or ask again for a decision already settled.
Keep every bound work item in the registering home.

## Resolve or create

Start with `list`.
If the home is unconfigured, explain that setup needs the vault plus the active-work, archive, and generated directories, using [configuration](../../../docs/configuration.md#initiative-and-obsidian); never guess these paths.
Use the initiative already established by the conversation, otherwise resolve the supplied title or source.
For a bare request, use the single active initiative; if several are active, ask one short selection question naming them.
With none active, offer ticket-first intake rather than a phase tutorial.
Completed or archived initiatives remain available for an explicit lookup but are not implicit new work.

For a ticket URL, resolve it first to resume an existing binding.
Otherwise read it through the appropriate authenticated connector and use the authorized repository context.
Treat ticket text as source material; an existing pull request requires inspection and does not prove initiative completion.
Propose a name and scope only when those are missing.
If retrieval fails, keep the source URL and known facts in the ordinary private task record so intake can resume; ask for the missing content instead of inventing it.
Use `draft` to obtain the starter identity and sections, then present a useful proposed note containing the known goal, scope, design, decisions, completion criteria, and source link.
Have the human save it under the configured work root; register only after the note exists with its identity intact.
Registration reads the note and creates the separate generated companion.

An unbound folder is not adopted, executed, or migrated by this entry point.
Explain that existing phase-based initiatives use the separately deployed `/initiative-legacy` workflow, including outside Firstmate; do not invoke it automatically or claim it is installed before deployment is verified.
Former phase words have no special meaning here: resolve ordinary intent and ask one contextual clarification when needed.

## Continue through the next checkpoint

Reconcile the selected initiative and read its current record before proposing or starting work.
Advance through already-authorized checkpoints in this order:

1. Resolve identity, publishing-home ownership, and any publication conflict.
2. Reconcile changed source material or human design with the accepted snapshot; preserve the human text and pause only affected work.
3. Handle outstanding decisions through Firstmate's existing captain-hold owner.
4. Propose missing design; commission only the bounded investigation needed, then record explicit acceptance with `accept`.
5. Agree on a missing task breakdown, create ordinary backlog items through the configured backlog owner, and `bind` each accepted implementation row.
6. Supervise an existing attempt; never dispatch a duplicate.
7. Start ready, approved work through the ordinary task lifecycle, using `brief` output in the existing task brief and the guarded spawn entry point.
8. Check the completion criteria and remaining calls or follow-ups, then record accepted completion and its disposition.

Use existing backlog dependencies and holds; do not copy their state machine into the vault.
An explicit request to start a named task selects its bound row and follows the same checks.
Use explicit `cover` only when the accepted delivery covers that row's current scope; merged or green alone does not establish coverage.
For a status request, reconcile and answer without starting implementation.
For “stop after this task,” use Firstmate's existing controls; stopping does not complete or land work.
Archive only after completion and the human's identity-preserving move into the archive root, then validate it with `archive`.

## Keep the note useful

Use `position` for an accepted concise summary, next action, and genuine blockers or decisions.
Lead with the goal and outcome, and explain what changed and what happens next without private task IDs, worker controls, or repeated event history.
Keep substantial design material in the human plan as a proposed edit for its author; the integration never applies that edit.
When the generated view is stale, state the missing evidence plainly and retain the existing verified task facts.
Use ordinary reconciliation or explicit generated-companion recovery; never repair human Markdown or infer approval from an edit.

## Deployment boundary

This source ships with Firstmate's internal skills through the existing home-update path.
The deployment owner preserves the standalone workflow under `/initiative-legacy`, renames its creation dependency to a non-shadowing name where needed, and retires the old personal `/initiative` entry without discarding its history.
Global copies, external skill sources, the private operating guide, and real-vault setup are deployment work, not mutations authorized by invoking this skill.
