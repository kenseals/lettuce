#!/usr/bin/env bash
set -euo pipefail

DEST="${1:-/tmp/lettuce-demo-public}"
SIGNAL_FILE="${DEST}-signal.md"

if command -v lettuce >/dev/null 2>&1; then
  lettuce_cmd=(lettuce)
else
  lettuce_cmd=(python3 -m lettuce.cli)
fi

rm -rf "$DEST"
mkdir -p "$(dirname "$DEST")"

cat > "$SIGNAL_FILE" <<'EOF'
Customer says their agent keeps acting on stale account context. They want the agent to maintain durable work context with source provenance.
EOF

"${lettuce_cmd[@]}" onboard "$DEST" \
  --org demo \
  --operator you \
  --title "Demo signal" \
  --body-file "$SIGNAL_FILE" \
  --source agent.direct \
  --surface cli \
  --consent operator-direct-request \
  --commit

"${lettuce_cmd[@]}" status "$DEST"
"${lettuce_cmd[@]}" logs "$DEST" --limit 5
find "$DEST/brain" -type f | sort

echo
printf 'Demo repo: %s\n' "$DEST"
printf 'Git status should be clean after committed actions:\n'
STATUS=$(git -C "$DEST" status --short)
if [[ -n "$STATUS" ]]; then
  echo "$STATUS"
  exit 1
fi
