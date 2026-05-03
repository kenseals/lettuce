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

REVIEWS_JSON=$(mktemp /tmp/lettuce-reviews-XXXXXX.json)
lettuce reviews "$DEST" | tee "$REVIEWS_JSON"

REVIEW_ID=$(python3 - "$REVIEWS_JSON" <<'PY'
import json
import sys
reviews = json.load(open(sys.argv[1], encoding="utf-8"))["reviews"]
if not reviews:
    raise SystemExit("no pending reviews created")
print(reviews[0]["id"])
PY
)

lettuce review-approve "$DEST" "$REVIEW_ID" --operator you --commit
lettuce status "$DEST"
lettuce logs "$DEST" --limit 5

echo
printf 'Demo repo: %s\n' "$DEST"
printf 'Approved review: %s\n' "$REVIEW_ID"
printf 'Git status should be clean after committed actions:\n'
STATUS=$(git -C "$DEST" status --short)
if [[ -n "$STATUS" ]]; then
  echo "$STATUS"
  exit 1
fi
