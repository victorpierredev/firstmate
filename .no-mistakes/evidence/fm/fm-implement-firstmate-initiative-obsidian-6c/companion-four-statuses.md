# Reliable account imports

> This status note is generated. Make changes in the initiative plan.

## Goal

Make account imports reliable for support teams.

## Current state

1 of 4 tasks complete. 1 in progress.

The parser has landed and the rejection report is being built.

## Completed work

- Parse import files: Read CSV and XLSX uploads safely

## Next action

Continue Report rejected rows.

## Blockers

- Resolve the decision or dependency for Retry transient failures.

## Decisions

- Decide whether a storage timeout is retried three or five times.

## Tasks

<!-- firstmate:initiative v=1 id=3c833a89-a761-4052-979d-6c6401f81e9a -->

| Task | Brief explanation | Status | Commit |
| --- | --- | --- | --- |
| <!-- firstmate:task id=b1f91d72-050d-481a-b677-32b7aa2a2950 --> Parse import files | Read CSV and XLSX uploads safely | Done | `3596d0cd2285` |
| <!-- firstmate:task id=3e0fc770-39c9-49c8-b1f7-b083d3f8aa95 --> Report rejected rows | Tell support which rows failed and why | In progress | - |
| <!-- firstmate:task id=e1ed0828-ef22-4566-9547-7c13be920f19 --> Retry transient failures | Retry storage timeouts without duplicating accounts | Blocked | - |
| <!-- firstmate:task id=73f9982b-8fc8-4304-8ec3-2a143b436ca9 --> Update the support guide | Explain the new rejection report to support staff | Planned | - |

## Links

- [Initiative plan](../Work/Reliable%20account%20imports.md)
- [Source ticket](https://example.test/ticket/1)
