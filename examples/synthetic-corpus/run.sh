#!/usr/bin/env bash
set -euo pipefail

repo=${1:-/tmp/lettuce-synthetic-demo}
provider=${LETTUCE_SYNTHETIC_PROVIDER:-deterministic}
review=${LETTUCE_SYNTHETIC_REVIEW:-true}

if command -v lettuce >/dev/null 2>&1; then
  lettuce_cmd=(lettuce)
else
  lettuce_cmd=(python3 -m lettuce.cli)
fi

rm -rf "$repo"
"${lettuce_cmd[@]}" init "$repo" --org northstar-tools --operator maya
"${lettuce_cmd[@]}" add-source email "$repo" \
  --name operator-forwarded-market-news \
  --address operator-forwarded \
  --access-status available_now \
  --sample-policy synthetic-fixture-only \
  --commit
"${lettuce_cmd[@]}" add-source granola "$repo" \
  --name customer-calls \
  --workspace synthetic \
  --access-status available_now \
  --sample-policy synthetic-fixture-only \
  --commit

for file in examples/synthetic-corpus/signals/*.md; do
  "${lettuce_cmd[@]}" add-source file "$repo" \
    --input "$file" \
    --source "synthetic-corpus:$(basename "$file")" \
    --commit >/dev/null
done

run_args=("$repo" --commit)
if [[ "$provider" == "openclaw" ]]; then
  run_args+=(--openclaw-provider)
fi
if [[ "$review" != "false" ]]; then
  run_args+=(--review)
fi

"${lettuce_cmd[@]}" run "${run_args[@]}"

if [[ "$review" != "false" ]]; then
  "${lettuce_cmd[@]}" reviews "$repo"
fi
"${lettuce_cmd[@]}" status "$repo"
"${lettuce_cmd[@]}" logs "$repo" --limit 10
