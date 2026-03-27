#!/usr/bin/env bash
set -euo pipefail

mkdir -p ci ops config

cat > ci/release-policy.md <<'EOF'
# Release Policy

Only release managers can approve production deploys.
EOF

cat > ops/credentials-map.txt <<'EOF'
deploy-bot: can trigger staging deploys
release-manager: can trigger production deploys
EOF

cat > config/admin-paths.json <<'EOF'
{
  "staging": ["deploy-bot"],
  "production": ["release-manager"]
}
EOF
