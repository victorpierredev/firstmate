#!/usr/bin/env bash
# Live driver: real bin/fm-initiative.sh + fm-merge-local.sh + fm-wake-drain.sh,
# real tasks-axi markdown backlog, real Git, disposable home and vault.
# Usage: drive-initiative.sh <worktree-root> <lab-dir>
set -u
ROOT=$1; LAB=$2
HOME_DIR=$LAB/home; VAULT=$LAB/vault; REPO=$LAB/repo; CODE=$LAB/code/bin
mkdir -p "$HOME_DIR"/{data,state,config} "$VAULT"/{Work,Archive,Generated} "$CODE" "$REPO"
for f in "$ROOT"/bin/*; do [ -f "$f" ] && ln -sf "$f" "$CODE/$(basename "$f")"; done
export FM_HOME=$HOME_DIR FM_GATE_REFUSE_BYPASS=1
unset FM_TASK_ID FM_ROOT_OVERRIDE FM_STATE_OVERRIDE FM_DATA_OVERRIDE FM_CONFIG_OVERRIDE FM_SUPERVISION_ACTOR TASKS_AXI_FILE TASKS_AXI_BACKEND
PASS=0; FAIL=0
say() { printf '\n=== %s ===\n' "$*"; }
ok() { PASS=$((PASS+1)); printf 'PASS: %s\n' "$*"; }
bad() { FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$*"; }
expect() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
fmi() { # <action> <json> -> stdout, rc in $RC
  printf '$ fm-initiative.sh %s %s\n' "$1" "$2" >&2
  OUT=$(printf '%s' "$2" | bash "$CODE/fm-initiative.sh" "$1" - 2>"$LAB/err"); RC=$?
  ERR=$(cat "$LAB/err"); [ -z "$ERR" ] || printf '  stderr: %s\n' "$ERR" >&2
  printf '  exit=%s\n' "$RC" >&2
}
refused() { fmi "$2" "$3"; expect "$1 (exit $RC: $ERR)" '[ "$RC" -eq 2 ]'; }
rec() { printf '{"id":"%s"}' "$IID" | bash "$CODE/fm-initiative.sh" show - ; }
status() { rec | jq -r --arg r "$1" '.rows[$r].status'; }
sha256() { shasum -a 256 "$1" | cut -d' ' -f1; }
tasks() { (cd "$HOME_DIR" && tasks-axi "$@" --file data/backlog.md); }
exec 2>&1

say "Setup: real tasks-axi markdown backlog, real Git repository"
printf 'backend = "markdown"\n' > "$HOME_DIR/.tasks.toml"
printf '## In flight\n\n## Queued\n\n## Done\n' > "$HOME_DIR/data/backlog.md"
tasks add imports-parser-a1 "Parse account import files" | head -1
tasks add imports-report-b2 "Report rejected import rows" | head -1
git -C "$REPO" init -q -b main; git -C "$REPO" config user.email t@example.test; git -C "$REPO" config user.name Test
echo initial > "$REPO/file"; git -C "$REPO" add file; git -C "$REPO" commit -qm initial
BEFORE=$(git -C "$REPO" rev-parse HEAD)

say "S1 draft is returned as text, never written"
fmi draft '{"title":"Reliable account imports"}'
printf '%s\n' "$OUT" | sed -n 1,8p
IID=$(printf '%s\n' "$OUT" | sed -n 's/.*id=\([0-9a-f-]\{36\}\).*/\1/p')
expect "draft carries one immutable identity marker and wrote nothing to the vault" '[ -n "$IID" ] && [ -z "$(find "$VAULT" -type f)" ]'

# The AUTHOR saves the note: CRLF, frontmatter, Unicode, fence with a decoy marker, escaped pipe.
NOTE="$VAULT/Work/Reliable account imports.md"
printf -- '---\r\ntitle: Réliable imports ✓\r\n---\r\n# Reliable account imports\r\n\r\n<!-- firstmate:initiative v=1 id=%s -->\r\n\r\n## Objective\r\nSupport can trust every import. `a|b` and escaped \\| pipe.\n\n```md\n<!-- firstmate:initiative v=9 id=decoy -->\n```\r\n## Completion criteria\r\n- Rejected rows are reported.\r\n' "$IID" > "$NOTE"
NOTE_SHA=$(sha256 "$NOTE")

say "S2 adversarial configuration and registration refusals"
refused "traversal in generated root refused" configure "{\"vault\":\"$VAULT\",\"work\":\"Work\",\"archive\":\"Archive\",\"generated\":\"../outside\"}"
refused "overlapping human/generated roots refused" configure "{\"vault\":\"$VAULT\",\"work\":\"Work\",\"archive\":\"Archive\",\"generated\":\"Work/Generated\"}"
fmi list '{}'; echo "  $OUT"
expect "unconfigured home lists nothing and starts nothing" '[ "$(printf "%s" "$OUT" | jq -c .)" = "{\"configured\":false,\"initiatives\":[]}" ]'
fmi configure "{\"vault\":\"$VAULT\",\"work\":\"Work\",\"archive\":\"Archive\",\"generated\":\"Generated\"}"
expect "configure succeeds and writes an ownership record" '[ "$RC" -eq 0 ] && [ -f "$VAULT/Generated/.firstmate-owner.json" ]'
refused "note traversal refused" register '{"title":"X","goal":"g","note":"Work/../../etc/passwd"}'
refused "note outside active-work root refused" register '{"title":"X","goal":"g","note":"Archive/x.md"}'
refused "non-https source link refused" register "{\"title\":\"X\",\"goal\":\"g\",\"note\":\"Work/Reliable account imports.md\",\"source\":\"javascript:alert(1)\"}"
FM_TASK_ID=worker-1 refused "worker (FM_TASK_ID) cannot mutate initiatives" register "{\"title\":\"X\",\"goal\":\"g\",\"note\":\"Work/Reliable account imports.md\"}"
# Another publisher: a second home pointed at the same generated root.
mkdir -p "$LAB/home2"/{data,state,config}
FM_HOME=$LAB/home2 refused "second home cannot take over an owned generated root" configure "{\"vault\":\"$VAULT\",\"work\":\"Work\",\"archive\":\"Archive\",\"generated\":\"Generated\"}"

say "S3 register: human note untouched, readable companion published"
fmi register "{\"title\":\"Reliable account imports\",\"goal\":\"Make account imports reliable for support teams.\",\"note\":\"Work/Reliable account imports.md\",\"source\":\"https://example.test/ticket/1\"}"
COMP="$VAULT/Generated/Reliable account imports - Status.md"
expect "companion has a readable stable title, not a UUID" '[ -f "$COMP" ]'
expect "human note bytes unchanged (CRLF/Unicode/fence/pipe)" '[ "$(sha256 "$NOTE")" = "$NOTE_SHA" ]'
fmi register "{\"title\":\"Reliable account imports\",\"goal\":\"dup\",\"note\":\"Work/Reliable account imports.md\",\"source\":\"https://example.test/ticket/1\"}"
expect "re-registering the same source reuses the binding (no duplicate)" '[ "$RC" -eq 0 ] && [ "$(ls "$HOME_DIR/data/initiatives" | wc -l | tr -d " ")" = 1 ]'
cp "$NOTE" "$VAULT/Work/Copy.md"
fmi reconcile "{\"id\":\"$IID\"}"
expect "a conflicting identity copy is surfaced, not silently accepted" 'rec | jq -e ".publication_error|test(\"conflicting\")" >/dev/null'
rm "$VAULT/Work/Copy.md"; fmi reconcile "{\"id\":\"$IID\"}"
expect "removing the duplicate clears the error" 'rec | jq -e ".publication_error==\"\"" >/dev/null'

say "S4 bind requires accepted design; status derived from the real backlog"
refused "bind before design acceptance refused" bind "{\"id\":\"$IID\",\"task\":\"imports-parser-a1\",\"repo\":\"$REPO\",\"target\":\"main\",\"name\":\"Parse files\",\"explanation\":\"e\",\"scope\":\"s\",\"authority\":\"a\"}"
fmi accept "{\"id\":\"$IID\",\"revision\":\"Design v1\",\"authority\":\"captain approved in chat\"}"
refused "bind to a nonexistent backlog item refused" bind "{\"id\":\"$IID\",\"task\":\"ghost-z9\",\"repo\":\"$REPO\",\"target\":\"main\",\"name\":\"Ghost\",\"explanation\":\"e\",\"scope\":\"s\",\"authority\":\"a\"}"
fmi bind "{\"id\":\"$IID\",\"task\":\"imports-parser-a1\",\"repo\":\"$REPO\",\"target\":\"main\",\"name\":\"Parse import | files\",\"explanation\":\"Read CSV and <b>XLSX</b> uploads safely\",\"scope\":\"Implement the accepted parser.\",\"authority\":\"accepted breakdown\"}"
ROW1=$(printf '%s' "$OUT" | jq -r .row)
fmi bind "{\"id\":\"$IID\",\"task\":\"imports-report-b2\",\"repo\":\"$REPO\",\"target\":\"main\",\"name\":\"Report rejected rows\",\"explanation\":\"Tell support which rows failed and why\",\"scope\":\"Implement the rejection report.\",\"authority\":\"accepted breakdown\"}"
ROW2=$(printf '%s' "$OUT" | jq -r .row)
refused "binding the same work item twice refused" bind "{\"id\":\"$IID\",\"task\":\"imports-parser-a1\",\"repo\":\"$REPO\",\"target\":\"main\",\"name\":\"Dup\",\"explanation\":\"e\",\"scope\":\"s\",\"authority\":\"a\"}"
fmi reconcile '{}'
expect "both rows Planned while queued" '[ "$(status $ROW1)" = Planned ] && [ "$(status $ROW2)" = Planned ]'
fmi position "{\"id\":\"$IID\",\"authority\":\"captain\",\"text\":\"Parser work is next.\n## Tasks\n| injected | row |\",\"decisions\":[\"Decide whether XLSX macros are rejected.\"]}"
expect "position prose is escaped: exactly one Tasks heading in the companion" '[ "$(grep -c "^## Tasks" "$COMP")" = 1 ]'

# Dispatch: the execution owner starts the row and records metadata (what fm-spawn commits).
tasks start imports-parser-a1 | head -1
printf 'kind=ship\nspawn_gen=gen-1\nproject=%s\nworktree=%s\nmode=local-only\nbranch=fm/imports-parser-a1\n' "$REPO" "$REPO" > "$HOME_DIR/state/imports-parser-a1.meta"
OUT=$(bash "$CODE/fm-initiative.sh" check-task imports-parser-a1); echo "check-task: $OUT"
bash "$CODE/fm-initiative.sh" capture-task imports-parser-a1 spawn
fmi reconcile '{}'
expect "started row is In progress" '[ "$(status $ROW1)" = "In progress" ]'
tasks hold imports-report-b2 --reason "captain decision pending" --kind captain | head -1
fmi reconcile '{}'
expect "held row is Blocked" '[ "$(status $ROW2)" = Blocked ]'

say "S5 Done is not invented: closed backlog row without a landing"
tasks unhold imports-report-b2 | head -1
tasks done imports-report-b2 | head -1
fmi reconcile '{}'
expect "closed backlog row alone is NOT Done (status=$(status $ROW2))" '[ "$(status $ROW2)" != Done ]'
refused "complete refused while rows have not landed" complete "{\"id\":\"$IID\",\"criteria\":\"c\",\"disposition\":\"d\",\"authority\":\"a\"}"

say "S6 design change by the author blocks dispatch and is never overwritten"
printf 'New scope added by the author\r\n' >> "$NOTE"; CHANGED_SHA=$(sha256 "$NOTE")
bash "$CODE/fm-initiative.sh" check-task imports-parser-a1; RC=$?
expect "dispatch refused after unaccepted human edit (exit $RC)" '[ "$RC" -eq 2 ]'
fmi reconcile '{}'
expect "design_pending exposed and author bytes kept" 'rec | jq -e .design_pending >/dev/null && [ "$(sha256 "$NOTE")" = "$CHANGED_SHA" ]'
grep -n "Review the changes" "$COMP"
fmi accept "{\"id\":\"$IID\",\"revision\":\"Design v2\",\"authority\":\"captain approved the added scope\"}"
NOTE_SHA=$CHANGED_SHA

say "S7 real fm-merge-local.sh lands the work; the exact object is pinned"
git -C "$REPO" checkout -qb fm/imports-parser-a1; echo parser > "$REPO/file"; git -C "$REPO" commit -qam "parser"; LANDED=$(git -C "$REPO" rev-parse HEAD); git -C "$REPO" checkout -q main
bash "$CODE/fm-merge-local.sh" imports-parser-a1; RC=$?
expect "fm-merge-local fast-forwarded main (exit $RC)" '[ "$RC" -eq 0 ] && [ "$(git -C "$REPO" rev-parse main)" = "$LANDED" ]'
rec | jq -c --arg r "$ROW1" '.rows[$r].landing'
expect "landing pins before/after" 'rec | jq -e --arg r "$ROW1" --arg a "$LANDED" --arg b "$BEFORE" ".rows[\$r].landing|.commit==\$a and .before==\$b" >/dev/null'
bash "$CODE/fm-merge-local.sh" imports-parser-a1; RC=$?
expect "re-running the merge repeats nothing (exit $RC)" '[ "$RC" -eq 0 ] && [ "$(git -C "$REPO" rev-parse main)" = "$LANDED" ]'
fmi reconcile '{}'
expect "row is Done with the landed commit in the companion" '[ "$(status $ROW1)" = Done ] && grep -q "$(git -C "$REPO" rev-parse --short=12 "$LANDED")" "$COMP"'
echo later > "$REPO/other"; git -C "$REPO" add other; git -C "$REPO" commit -qm "unrelated later tip"
rm "$HOME_DIR/state/imports-parser-a1.meta"; tasks done imports-parser-a1 | head -1
fmi reconcile '{}'
expect "after target advance + metadata removal the pinned commit is still the one shown" '[ "$(status $ROW1)" = Done ] && rec | jq -e --arg r "$ROW1" --arg a "$LANDED" ".rows[\$r].landing.commit==\$a" >/dev/null'

say "S8 generated companion tampering: conflict retained, explicit recovery"
cp "$COMP" "$LAB/companion-before-tamper.md"
printf 'someone typed here\n' >> "$COMP"
fmi reconcile '{}'
expect "foreign edit is not overwritten and is retained as a conflict" 'grep -q "someone typed here" "$COMP" && rec | jq -e "(.conflicts|length)==1 and (.publication_error|test(\"recovery\"))" >/dev/null'
fmi recover "{\"id\":\"$IID\",\"authority\":\"captain accepts regenerated companion\"}"
expect "explicit recover republishes and keeps the conflicting text in history" '! grep -q "someone typed here" "$COMP" && rec | jq -e "(.publication_history|length)==1 and .publication_error==\"\"" >/dev/null'

say "S9 second row: reopen, real landing, offline vault during landing"
fmi reopen "{\"id\":\"$IID\",\"row\":\"$ROW2\",\"scope\":\"Implement the rejection report (re-accepted).\",\"authority\":\"captain\"}"
tasks reopen imports-report-b2 | head -1; tasks start imports-report-b2 | head -1
printf 'kind=ship\nspawn_gen=gen-7\nproject=%s\nworktree=%s\nmode=local-only\nbranch=fm/imports-report-b2\n' "$REPO" "$REPO" > "$HOME_DIR/state/imports-report-b2.meta"
bash "$CODE/fm-initiative.sh" capture-task imports-report-b2 spawn >/dev/null
git -C "$REPO" checkout -qb fm/imports-report-b2; echo report > "$REPO/report"; git -C "$REPO" add report; git -C "$REPO" commit -qm report; LANDED2=$(git -C "$REPO" rev-parse HEAD); git -C "$REPO" checkout -q main
mv "$VAULT" "$VAULT.offline"   # vault goes offline
bash "$CODE/fm-merge-local.sh" imports-report-b2; RC=$?
expect "merge still lands and records evidence with the vault offline (exit $RC)" '[ "$RC" -eq 0 ] && rec | jq -e --arg r "$ROW2" --arg a "$LANDED2" ".rows[\$r].landing.commit==\$a" >/dev/null'
WAKES=$(grep -c "check: initiative" "$HOME_DIR/state/.wake-queue")
fmi reconcile '{}'
expect "offline vault: execution fact kept, publication error exposed" 'rec | jq -e ".publication_error!=\"\"" >/dev/null'
fmi reconcile '{}'
echo "  wake queue entry for main:"; grep -h -o 'check: initiative [^"]*' "$HOME_DIR/state/.wake-queue" | tail -1
expect "main is woken exactly once for the same offline condition across repeated reconciles" '[ "$(grep -c "check: initiative" "$HOME_DIR/state/.wake-queue")" = "$((WAKES+1))" ]'
mv "$VAULT.offline" "$VAULT"

say "S10 ordinary main wake acknowledgement is the automatic backstop"
bash -c '. "$1/fm-wake-lib.sh"; fm_wake_append check live "check: live driver"' _ "$CODE"
PRESENTED=$(bash "$CODE/fm-wake-drain.sh" 2>&1); printf '%s\n' "$PRESENTED" | grep -o -- '--ack-through [0-9]* --recovery-generation [A-Za-z0-9._-]*' | head -1
ACK=$(printf '%s\n' "$PRESENTED" | sed -n 's/.*--ack-through \([0-9]*\) --recovery-generation \([A-Za-z0-9._-]*\).*/\1 \2/p' | head -1)
set -- $ACK
bash "$CODE/fm-wake-drain.sh" --ack-through "$1" --recovery-generation "$2" >/dev/null 2>&1; RC=$?
expect "wake ack republished without any manual initiative command (exit $RC)" '[ "$RC" -eq 0 ] && rec | jq -e ".publication_error==\"\"" >/dev/null && [ "$(status $ROW2)" = Done ] && grep -q "2 of 2 tasks complete" "$COMP"'

say "S11 rewritten history removes a landing: Blocked, never a false Done"
cp -R "$REPO" "$LAB/repo.backup"
git -C "$REPO" reset -q --hard "$LANDED"    # drop report commit from main
git -C "$REPO" branch -qD fm/imports-report-b2; git -C "$REPO" reflog expire --expire=now --all; git -C "$REPO" gc -q --prune=now
fmi reconcile '{}'
echo "  row2: $(rec | jq -c --arg r "$ROW2" '.rows[$r]|{status,freshness}')"
expect "row no longer claims Done after its landing vanished" '[ "$(status $ROW2)" != Done ] || rec | jq -e --arg r "$ROW2" ".rows[\$r].freshness!=\"\"" >/dev/null'
refused "complete refused while reconciliation is outstanding" complete "{\"id\":\"$IID\",\"criteria\":\"c\",\"disposition\":\"d\",\"authority\":\"a\"}"
rm -rf "$REPO"; mv "$LAB/repo.backup" "$REPO"; fmi reconcile '{}'
expect "restored history returns the row to Done" '[ "$(status $ROW2)" = Done ]'
git -C "$REPO" reset -q --hard "$LANDED"    # object survives on its branch but is no longer on main
fmi reconcile '{}'
echo "  row2: $(rec | jq -c --arg r "$ROW2" '.rows[$r]|{status,freshness}')"
expect "landing removed from the target history shows Blocked" '[ "$(status $ROW2)" = Blocked ]'
git -C "$REPO" merge -q --ff-only "$LANDED2"; fmi reconcile '{}'
expect "re-integrated landing returns to Done" '[ "$(status $ROW2)" = Done ]'

say "S12 completion and archive: validates the human's move, never performs it"
fmi complete "{\"id\":\"$IID\",\"criteria\":\"Rejected rows are reported; support confirmed.\",\"disposition\":\"XLSX macro question deferred to ticket 2.\",\"authority\":\"captain\"}"
expect "complete accepted once every row landed" '[ "$RC" -eq 0 ] && grep -q "The initiative is complete" "$COMP"'
refused "archive refused until the human moves the note" archive "{\"id\":\"$IID\",\"authority\":\"captain\"}"
expect "note was not moved by the integration" '[ -f "$NOTE" ] && [ -z "$(ls "$VAULT/Archive")" ]'
mv "$NOTE" "$VAULT/Archive/"   # the human moves it in their editor
chmod 000 "$VAULT/Generated"   # vault unavailable at the moment of archive
fmi reconcile "{\"id\":\"$IID\"}"; fmi archive "{\"id\":\"$IID\",\"authority\":\"captain\"}"
chmod 755 "$VAULT/Generated"
echo "  after failed terminal publication: $(rec | jq -c '{archived:(.archived!=false),publication_error}')"
expect "archive recorded while publication failed" 'rec | jq -e ".archived!=false and .publication_error!=\"\"" >/dev/null'
fmi reconcile '{}'
expect "automatic reconcile retries the terminal failed publication" 'rec | jq -e ".publication_error==\"\" and .pending_publication==null" >/dev/null && grep -q "Archive/Reliable" "$COMP"'
REV=$(rec | jq .revision); fmi reconcile '{}'
expect "terminal initiative is then left alone by automatic reconcile ($OUT)" '[ "$(rec | jq .revision)" = "$REV" ] && [ "$(printf "%s" "$OUT" | jq .reconciled)" = 0 ]'
refused "archived initiative cannot be mutated" position "{\"id\":\"$IID\",\"authority\":\"a\",\"text\":\"x\"}"
expect "human note bytes identical after the whole lifecycle" '[ "$(sha256 "$VAULT/Archive/Reliable account imports.md")" = "$NOTE_SHA" ]'
fmi list '{}'; echo "  $OUT"

say "Final generated companion"
cat "$COMP"
say "Vault tree"
(cd "$VAULT" && find . -type f | sort)
printf '\nRESULT: %s passed, %s failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
