# Initiative publication verification

Verified 2026-09-18 on macOS 27.0 with Python 3.14.7, Obsidian 1.13.7 (installer 1.12.4), and gh-axi 0.1.35.
The [helper header](../../bin/fm-initiative.sh) owns the command and persistence contracts; [configuration](../configuration.md#initiative-and-obsidian) owns setup and current provider limits.

## Executable behavior

```sh
bin/fm-test-run.sh tests/fm-initiative.test.sh
bin/fm-test-run.sh tests/fm-backlog-atomicity.test.sh
bin/fm-test-run.sh tests/fm-captain-hold-lifecycle.test.sh
```

The initiative suite reports `Ran 68 tests` and `OK`.
The full backlog and captain-hold suites report `exit=0`.
The installed tasks-axi is markdown-only, so the captain-hold suite explicitly skips its live Beads migration cases; its structured adapter fixtures still run.
The macOS backlog run uses the existing portable timeout helper without installing GNU timeout.

The initiative cases execute the public helper with disposable homes, vaults, Git histories, and structured owner/provider fixtures.
They cover read-only human notes, path and ownership refusal, readable stable names and collisions, all four statuses, explicit coverage, generation and scope changes, publication interruption, conflict retention, bounded resolved history, pre-merge persistence, failed Git updates, post-merge crashes, cleanup ordering, supervision-branch cleanup capture, forced discard, local retry and unapplied-intent replacement, retained delivery proof, rewritten history, unsupported providers, unreadable unrelated notes, and bounded automatic reconciliation of completed or archived initiatives.
Publication crash tests terminate a separate process at filesystem publication boundaries and recover through the normal command.
These are process-crash tests, not power-loss qualification.

## Native reading and embedding

The native pilot used one disposable vault and a separate Obsidian user-data directory inside the laboratory.
Its registry contained only that vault, CLI access was enabled, updates were disabled, and community plugins were absent.
Opening the actual vault path was necessary to initialize its per-vault state; a registry entry alone did not load a usable vault.
The CLI vault selector must precede the command.

The following commands were exercised with `pilot_profile` and `pilot_vault` pointing at those disposable directories and `pilot_uri` containing the percent-encoded absolute vault path:

```sh
obsidian --user-data-dir="$pilot_profile" "obsidian://open?path=$pilot_uri"
obsidian vault=f17a7e0000000001 open "path=Generated/Example - Status.md" --user-data-dir="$pilot_profile"
obsidian vault=f17a7e0000000001 command id=markdown:toggle-preview --user-data-dir="$pilot_profile"
obsidian vault=f17a7e0000000001 open path=Work/Example.md --user-data-dir="$pilot_profile"
```

The fixture author, not the publisher, inserted `![[Generated/Example - Status]]` into the human note.
Native DOM reads and a screenshot verified the directly opened title `Example - Status`.
The embed reported the same readable title, the headers `Task`, `Brief explanation`, `Status`, `Commit`, and the statuses `Done`, `In progress`, `Blocked`, `Planned`.
The relative plan link resolved to `Work/Example.md`, and source view retained the hidden identity comments.
After a graceful application stop, a fresh helper reconciliation retained the final local object, human bytes, companion bytes, and companion modification time.
Reopening the isolated app retained the readable embedded title and four-column table.
The disposable app was stopped after verification.

Obsidian itself normalized CRLF to LF in an earlier fixture opened through its view API; the helper detected that as a changed human design instead of overwriting it.
The final native fixture used author-supplied LF and remained byte-identical through opening, embedding, reconciliation, and restart.
The executable helper tests independently preserve CRLF, Unicode, fences, frontmatter, and pipe characters byte-for-byte.
Native reading does not establish a real-vault deployment or a fresh supervisor-session installation walkthrough; those remain deployment-owner checks.

## Provider boundary

With a disposable repository whose origin was the canonical Firstmate GitHub repository, this read-only request succeeded:

```json
{"pr":"https://github.com/kunchenguid/firstmate/pull/4800","repo":"<disposable repository>","target":"main"}
```

```sh
FM_HOME="$pilot_home" bin/fm-initiative.sh verify-provider request.json
```

The result was `4055cbd6ec99e54210e01698c7c9b01f66e0a74c`, with `github-rest-merged-object` provenance and verified target ancestry.
It differed from the recorded worker head `ab7be8111cd63f8fdde6bf45305cb5d453c08b83`.
This verifies the live transport, final object, and ancestry path for [that merged delivery](https://github.com/kunchenguid/firstmate/pull/4800), without inferring its merge strategy from parent count.
The merge, squash, and multi-commit rebase response contracts have executable fixtures; separate known-strategy live examples are not yet recorded for all three strategies.
GitLab final-object publication remains disabled, with an explicit retained obligation and no Done/hash claim.
