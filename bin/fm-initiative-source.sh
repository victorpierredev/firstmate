#!/usr/bin/env bash
# fm-initiative-source.sh - structured reads through existing lifecycle owners.
# Usage: fm-initiative-source.sh task <id> | pr <canonical-url> | wake <id> <digest>
# task returns exact backlog flags and the current execution owner's observation;
# missing/unreadable rows remain unknown. It never reads a bounded fleet snapshot.
# pr delegates forge identity validation. wake uses the existing durable queue.
set -eu
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${FM_HOME:?explicit FM_HOME required}"
DATA="${FM_DATA_OVERRIDE:-$FM_HOME/data}"
STATE="${FM_STATE_OVERRIDE:-$FM_HOME/state}"
CONFIG="${FM_CONFIG_OVERRIDE:-$FM_HOME/config}"
# shellcheck source=bin/fm-pr-lib.sh
. "$SCRIPT_DIR/fm-pr-lib.sh"
case "${1:-}" in
  pr)
    fm_pr_url_parse "${2:-}" || exit 2
    jq -n --arg provider "$FM_PR_PROVIDER" --arg url "$FM_PR_URL" --arg host "$FM_PR_HOST" --arg path "$FM_PR_PATH" --arg number "$FM_PR_NUMBER" \
      '{provider:$provider,url:$url,host:$host,path:$path,number:$number}'
    ;;
  task)
    fm_pr_task_id_valid "${2:-}" || exit 2
    # shellcheck source=bin/fm-tasks-axi-lib.sh
    . "$SCRIPT_DIR/fm-tasks-axi-lib.sh"
    # shellcheck source=bin/fm-backlog-transition-lib.sh
    . "$SCRIPT_DIR/fm-backlog-transition-lib.sh"
    if fm_backlog_backend_manual "$CONFIG"; then
      echo 'error: automatic initiative tracking requires structured tasks-axi reads; manual backend is unsupported' >&2
      exit 2
    fi
    fm_backlog_row_probe "$DATA" "$2" || true
    current=
    if [ -f "$STATE/$2.meta" ]; then
      current=$(FM_CREW_STATE_NO_FORGE=1 "$SCRIPT_DIR/fm-crew-state.sh" "$2" 2>/dev/null) || current=
    fi
    jq -n --arg result "$FM_BACKLOG_ROW_RESULT" --arg state "$FM_BACKLOG_ROW_STATE" --arg error "$FM_BACKLOG_ROW_ERROR" --arg current "$current" \
      '{result:$result,state:$state,error:$error,current:$current}'
    ;;
  wake)
    fm_pr_task_id_valid "${2:-}" || exit 2
    # shellcheck source=bin/fm-wake-lib.sh
    . "$SCRIPT_DIR/fm-wake-lib.sh"
    fm_wake_append check "initiative-$2-${3:?digest required}" "check: initiative $2 requires reconciliation; read bin/fm-initiative.sh show"
    ;;
  *) exit 2 ;;
esac
