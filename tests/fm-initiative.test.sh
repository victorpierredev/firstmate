#!/usr/bin/env bash
# Exercise initiative commands through their executable interface with isolated
# homes, vaults, real Git histories, and deterministic structured tool fixtures.
set -eu
# shellcheck source=tests/lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
TMP_ROOT=$(fm_test_tmproot fm-initiative)
python3 "$ROOT/tests/assets/fm-initiative-tests.py" "$ROOT" "$TMP_ROOT"
