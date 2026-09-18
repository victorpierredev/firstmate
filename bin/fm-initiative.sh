#!/usr/bin/env bash
# fm-initiative.sh - initiative bindings and separate generated Obsidian state.
#
# Usage: fm-initiative.sh <command> [request.json|-]
# JSON is data, never a shell program. With -, read the request from stdin.
# Commands and required request fields:
#   configure: vault (absolute), work, archive, generated (relative directories)
#   draft: title [source]                       emit a human-note starter
#   register: title, goal, note [source]               read an opted-in human note
#   accept: id, revision, authority              snapshot the accepted design
#   bind: id, task, repo, target, name, explanation, scope, authority
#   position: id, text, authority [next, blockers[], decisions[]]                publish a narrative proposal
#   edit-row: id, row, authority [name, explanation, order]
#   retire/reopen: id, row, authority [scope]     retain history/tombstones
#   cover: id, row, pr, authority                explicit delivery coverage
#   complete: id, criteria, disposition, authority
#   archive: id, authority                       validate a HUMAN-performed move
#   list: {} -> configured, initiatives[{id,title,source,state}]
#     state is active, completed, or archived; unconfigured homes return []
#   show: id; resolve: [query]; brief: id, row; reconcile: [id]
#     reconcile without id observes active initiatives only; a completed or
#     archived initiative only has pending or failed publication retried, and
#     is reverified only when named by id
#   dispatch-check: task                        verify approved source/scope
#   capture: task, event (spawn|merge|local-intent|local|local-retry|delivery|teardown|discard)
#     merge takes pr; local-intent/local take before, after, target (full IDs)
#     local-intent durably pins the approved update before Git runs and replaces
#     an earlier intent only when the target proves it was never applied;
#     local-retry verifies it without merging, returns landed, and with [tip]
#     refuses branch commits beyond the recorded landing; delivery retains the
#     execution owner's no-mistakes proof before cleanup acquires its locks;
#     discard is teardown under explicit --force authority and records the
#     abandoned attempt when no landing or delivery evidence exists, or when
#     reopen already cleared that attempt from the row
#   recover: id, authority                      accept regenerated companion
#   verify-provider: pr, repo, target             read-only capability check
# Internal lifecycle callers may use:
#   fm-initiative.sh capture-task <task> <event> [pr|tip|before after target]
#   fm-initiative.sh check-task <task>
#
# config/initiative.json v1 pins home/data/state/config, vault and disjoint human
# work/archive and generated roots. The generated directory's ownership record
# binds one random publisher ID and canonical home; it is never adopted silently.
# data/initiatives/<UUID>/record.json v1 owns immutable initiative/row UUIDs,
# accepted text snapshots and provenance, exact work-item/repository/target/scope
# bindings, generation-bound attempts, landing history/obligations, publication
# baseline bytes/pending candidate/staging name/conflicts and revision.
# Explicitly resolved publication history retains at most 8 entries/256 KiB;
# unresolved evidence is never pruned. No dependency graph is copied.
# The human note is READ ONLY for ALL operations, including registration/archive.
# New records reserve a readable companion basename (<title> - Status.md), reject
# case-insensitive collisions, and retain that name independently of identity.
# Only the registered generated companion is published for reading/embedding.
# Only delivery capture reads the execution owner (outside cleanup/record locks);
# other captures use local evidence and never access the vault or forge.
# Teardown refuses missing delivery/local landing evidence unless forced.
# Cleanup captures (delivery|teardown) write private records only, so they stay
# open to the supervision branch's ordinary landed-work teardown.
# An unreadable unrelated note is skipped; the registered note must be readable.
# Reconcile collects owner observations outside the record
# lock, then refuses stale observations. Same-home writers serialize with flock.
# Hooks are inert without configuration. No new worker, daemon, or merge authority.
# Exit 2 refuses invalid/unsafe input; publication failures remain in the record
# and notify once through the existing wake queue, without changing task truth.
set -eu
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "${1:-}" in
  -h|--help|'') sed -n '2,/^set -eu$/p' "$0" | sed 's/^# \{0,1\}//; $d'; exit 0 ;;
esac
: "${FM_HOME:?fm-initiative requires explicit FM_HOME}"
export FM_HOME
STATE="${FM_STATE_OVERRIDE:-$FM_HOME/state}"
CONFIG="${FM_CONFIG_OVERRIDE:-$FM_HOME/config}"
case "$1" in
  reconcile|capture|capture-task|dispatch-check|check-task)
    if [ ! -e "$CONFIG/initiative.json" ] && [ ! -L "$CONFIG/initiative.json" ]; then
      printf '{}\n'
      exit 0
    fi
    ;;
esac
case "$1" in
  list|show|resolve|brief|draft|verify-provider) ;;
  *)
    # shellcheck source=bin/fm-gate-refuse-lib.sh
    . "$SCRIPT_DIR/fm-gate-refuse-lib.sh"
    fm_refuse_if_gate_agent
    [ -z "${FM_TASK_ID:-}" ] || { echo 'error: initiative mutation belongs to the publishing supervisor, not a worker' >&2; exit 2; }
    # shellcheck source=bin/fm-lease-lib.sh
    . "$SCRIPT_DIR/fm-lease-lib.sh"
    case "$1:${3:-}" in
      capture-task:delivery|capture-task:teardown) ;;
      *) fm_lease_forbid_branch initiative-publication ;;
    esac
    # shellcheck source=bin/fm-session-lock-lib.sh
    . "$SCRIPT_DIR/fm-session-lock-lib.sh"
    if fm_session_lock_foreign_owner_live "$STATE"; then
      # The detached startup worker already holds its existing acquisition
      # lease; its captured owner must still match the live home owner.
      if [ "$1" != reconcile ] || [ "${FM_BOOTSTRAP_NETWORK_LOCK_PID:-}" != "$FM_SESSION_LOCK_FOREIGN_OWNER_PID" ]; then
        echo 'error: another session owns this home; initiative mutation refused' >&2
        exit 2
      fi
    fi
    ;;
esac
exec python3 "$SCRIPT_DIR/fm-initiative.py" "$@"
