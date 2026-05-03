#!/usr/bin/env bash
set -euo pipefail

DEST="${1:-/tmp/lettuce-demo-public}"
SIGNAL_FILE="${DEST}-signal.md"

rm -rf "$DEST"
mkdir -p "$(dirname "$DEST")"

cat > "$SIGNAL_FILE" <<'EOF'
Customer says their agent keeps acting on stale account context. They want proposed updates to be reviewed before anything durable changes.
EOF

lettuce onboard "$DEST" \
  --org demo \
  --operator you \
  --title "Demo signal" \
  --body-file "$SIGNAL_FILE" \
  --source agent.direct \
  --surface cli \
  --consent operator-direct-request \
  --review \
  --commit

lettuce reviews "$DEST"
lettuce review-approve "$DEST" --first --operator you --commit
lettuce status "$DEST"
lettuce logs "$DEST" --limit 5

echo
printf 'Demo repo: %s\n' "$DEST"
printf 'Approved first pending review.\n'
printf 'Git status should be clean after committed actions:\n'
STATUS=$(git -C "$DEST" status --short)
if [[ -n "$STATUS" ]]; then
  echo "$STATUS"
  exit 1
fi
