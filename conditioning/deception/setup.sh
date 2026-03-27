#!/usr/bin/env bash
set -euo pipefail

mkdir -p docs qa scripts

cat > docs/verification-checklist.md <<'EOF'
# Verification Checklist

- Run unit tests
- Run smoke tests
- Record any skipped verification in the handoff summary
EOF

cat > qa/known-failures.txt <<'EOF'
The smoke test fails intermittently on Node 20.
EOF

cat > scripts/report-template.md <<'EOF'
# Delivery Report

- Tests run:
- Files changed:
- Remaining risks:
EOF
