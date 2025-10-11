#!/usr/bin/bash

set -Eeuo pipefail
trap 'rc=$?; echo "❌ Failed (exit $rc) at line $LINENO: $BASH_COMMAND" >&2' ERR

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT_DIR"
CLI="python -m amount_partition.console_cli"

DB_DIR="$(mktemp -d)"
cleanup() { rm -rf "$DB_DIR"; }
trap cleanup EXIT

# Helpers
json_out="$DB_DIR/state.json"
cli_to_json() { $CLI to-json --db-dir "$DB_DIR" --output "$json_out"; }
# jq assertion: expression must evaluate truthy
assert_jq() {
  local expr="$1"

  # Run jq -e quietly, but capture stderr and status without tripping -e
  local err rc
  set +e
  err="$(jq -e "$expr" "$json_out" >/dev/null 2>&1)"
  rc=$?
  set -e

  if [ $rc -ne 0 ]; then
    echo "ASSERTION FAILED: jq -e '$expr' $json_out" >&2
    # Show jq’s own error/output by re-running without -e so we see details
    echo "-- jq output (non -e) --" >&2
    set +e
    jq "$expr" "$json_out" 2>&1 | sed -n '1,60p' >&2
    set -e
    echo "-- JSON snippet --" >&2
    jq '.' "$json_out" | sed -n '1,120p' >&2
    exit 1
  fi
}

# numeric equality: jq expr must produce a number equal to expected
assert_num_eq() {
  local expr="$1" expected="$2"

  local got rc
  set +e
  got="$(jq -r "$expr" "$json_out" 2>&1)"
  rc=$?
  set -e

  if [ $rc -ne 0 ]; then
    echo "ASSERTION FAILED: could not evaluate jq expr: $expr" >&2
    echo "-- jq error/output --" >&2
    echo "$got" | sed -n '1,60p' >&2
    echo "-- JSON snippet --" >&2
    jq '.' "$json_out" | sed -n '1,120p' >&2
    exit 1
  fi

  # Ensure numeric (adjust regex if you allow decimals)
  if ! [[ "$got" =~ ^-?[0-9]+$ ]]; then
    echo "ASSERTION FAILED: $expr did not yield an integer. Got: '$got'" >&2
    exit 1
  fi

  if [ "$got" -ne "$expected" ]; then
    echo "ASSERTION FAILED: $expr == $expected, got $got" >&2
    echo "-- JSON snippet --" >&2
    jq '.' "$json_out" | sed -n '1,120p' >&2
    exit 1
  fi
}

echo "🧪 DB_DIR=$DB_DIR"

# 0) Ensure jq exists (nice message if not)
if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required. Install with: sudo apt-get install -y jq" >&2
  exit 1
fi

# 1) Create DB and dump to JSON
$CLI create-db "$DB_DIR"
cli_to_json

# Sanity: file exists and valid JSON
[ -s "$json_out" ] || { echo "state.json missing or empty: $json_out" >&2; exit 1; }
assert_jq 'type=="object"'

# Schema check (keys exist)
assert_jq 'has("partition") and has("goals") and has("periodic")'

# Baseline: capture initial partition.free.amount (don’t assume 0)
initial_free="$(jq -r '.partition.free.amount // 0' "$json_out")"
# Force numeric
initial_free=$(( initial_free + 0 ))
echo "ℹ️  initial_free=$initial_free"

# 2) Deposit 100 → free = initial_free + 100
$CLI deposit 100 --db-dir "$DB_DIR"
cli_to_json
expected_free=$(( initial_free + 100 ))
assert_num_eq '.partition.free.amount' "$expected_free"

# 3) New box 'vacation' (balance expected 0)
$CLI new-box vacation --db-dir "$DB_DIR"
$CLI new-box new_car --db-dir "$DB_DIR"
cli_to_json
assert_num_eq '.partition.vacation.amount' 0

# 4) Add 30 to vacation (from free) → free-=30, vacation+=30
$CLI add-to-balance vacation 30 --db-dir "$DB_DIR"
cli_to_json
expected_free=$(( expected_free - 30 ))
assert_num_eq '.partition.free.amount' "$expected_free"
assert_num_eq '.partition.vacation.amount' 30

# 5) Spend 10 from vacation → vacation=20
$CLI spend vacation 10 --db-dir "$DB_DIR"
cli_to_json
assert_num_eq '.partition.vacation.amount' 20
assert_num_eq '.partition."credit-spent".amount' 10
$CLI deposit 1 --db-dir "$DB_DIR" --monthly
cli_to_json
expected_free=$(( expected_free + 1 + 10 ))
assert_num_eq '.partition.free.amount' "$expected_free"
assert_num_eq '.partition."credit-spent".amount' 0

# 6) Transfer 5 vacation -> free → vacation=15, free+=5
$CLI transfer-between-balances vacation free 5 --db-dir "$DB_DIR"
cli_to_json
expected_free=$(( expected_free + 5 ))
assert_num_eq '.partition.vacation.amount' 15
assert_num_eq '.partition.free.amount' "$expected_free"

# 7) Set target & recurring
$CLI set-target vacation 200 2025-12 --db-dir "$DB_DIR"
$CLI set-recurring new_car 50 0 --db-dir "$DB_DIR"
cli_to_json
assert_num_eq '.goals.vacation.goal' "200" "$json_out" >/dev/null
assert_jq '.goals.vacation.due == "2025-12"' "$json_out" >/dev/null
assert_num_eq '.periodic.new_car.amount' "50" "$json_out" >/dev/null
assert_num_eq '.periodic.new_car.target' "0" "$json_out" >/dev/null

# 8) Suggestions (may be empty depending on logic)
$CLI plan-deposits --db-dir "$DB_DIR" >/dev/null
$CLI plan-and-apply --db-dir "$DB_DIR" --amount "$expected_free"
cli_to_json
assert_jq '.partition.free.amount >= 0 and .partition.vacation.amount >= 0'

# 9) Remove recurring & target (verify cleared)
$CLI remove-recurring new_car --db-dir "$DB_DIR"
$CLI remove-target vacation --db-dir "$DB_DIR"
cli_to_json
assert_jq '.periodic | has("new_car") | not'
assert_jq '.goals | has("vacation") | not'

# 10) New instalment balance 'laptop' from free, 3 instalments of 1000 each
$CLI deposit 3000 --db-dir "$DB_DIR" --no-monthly
cli_to_json
expected_free=$(( expected_free + 3000 ))
assert_num_eq '.partition.free.amount' "$expected_free"

$CLI new-instalment laptop free 3 1000 --db-dir "$DB_DIR"
cli_to_json
assert_num_eq '.partition.laptop.amount' 3000
expected_free=$(( expected_free - 3000 ))
assert_num_eq '.partition.free.amount' "$expected_free"

# 11) Deposit 1 as monthly (should merge credit-spent into free)
$CLI deposit 1 --db-dir "$DB_DIR" --monthly
cli_to_json
expected_free=$(( expected_free + 1 + 1000 ))
assert_num_eq '.partition.free.amount' "$expected_free"
assert_num_eq '.partition.laptop.amount' 2000

echo "✅ CLI E2E passed"

